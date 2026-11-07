// mac-cu Chrome extension: runs the commands of the browser tool with "engine": "extension" in the
// user's own Chrome. mac-cu (ChromeExtension.swift) sends them through the native messaging host
// com.kakao.mac_cu, which is the mac-cu program itself. The open native port keeps this worker alive.
// Page commands go through chrome.debugger (the Chrome DevTools Protocol on the user's tab).

const HOST = 'com.kakao.mac_cu';
// After this long without a command, mac-cu detaches from the tabs, and Chrome removes its debugging bar.
const IDLE_MS = 5 * 60 * 1000;

let port = null;
let current = null;  // The id of the tab mac-cu works on.
let lastUsed = 0;
const attached = new Set();
const canceled = new Set();  // Tabs where the user chose Cancel on the debugging bar.
const logs = new Map();  // tabId → {order, requests, console}
// The protocol commands mac-cu sends (Browser.swift, CDPEngine). Nothing else runs on the user's tab, so a
// program that reaches the native host does not get the whole DevTools protocol.
const CDP_METHODS = new Set([
  'Runtime.evaluate', 'Page.captureScreenshot', 'Network.getResponseBody', 'Network.getCookies',
  'Input.dispatchMouseEvent', 'Input.dispatchKeyEvent', 'Input.insertText',
]);

function connect() {
  if (port) return;
  port = chrome.runtime.connectNative(HOST);
  port.onMessage.addListener(onMessage);
  // Reading lastError marks it handled: a host that exits (update, refusal) is normal, the alarm reconnects.
  port.onDisconnect.addListener(() => { void chrome.runtime.lastError; port = null; });
}

chrome.alarms.create('mac-cu', {periodInMinutes: 1});
chrome.alarms.onAlarm.addListener(() => {
  connect();
  if (attached.size && Date.now() - lastUsed > IDLE_MS) {
    for (const tabId of attached) chrome.debugger.detach({tabId}).catch(() => {});
    attached.clear();
  }
});
connect();

async function onMessage(message) {
  lastUsed = Date.now();
  let reply;
  try {
    reply = {id: message.id, result: (await run(message.method, message.params || {})) ?? null};
  } catch (error) {
    reply = {id: message.id, error: String(error?.message ?? error)};
  }
  port?.postMessage(reply);
}

async function currentTab() {
  if (current != null) {
    try { return await chrome.tabs.get(current); } catch {}
  }
  const [tab] = await chrome.tabs.query({active: true, lastFocusedWindow: true});
  if (!tab) throw new Error('Chrome has no open tab. Use the open action.');
  current = tab.id;
  return tab;
}

async function attach(tabId) {
  if (canceled.has(tabId)) {
    throw new Error('The user stopped mac-cu in this tab (Cancel on the debugging bar). Do not try again in this tab; tell the user.');
  }
  if (attached.has(tabId)) return;
  await chrome.debugger.attach({tabId}, '1.3');
  attached.add(tabId);
  logs.set(tabId, {order: [], requests: {}, console: []});
  for (const domain of ['Network', 'Runtime', 'Page']) await chrome.debugger.sendCommand({tabId}, domain + '.enable');
}

chrome.debugger.onDetach.addListener(({tabId}, reason) => {
  attached.delete(tabId);
  if (reason === 'canceled_by_user') canceled.add(tabId);
});

// The same records as the devtools engine (DevTools.swift handle).
chrome.debugger.onEvent.addListener(({tabId}, method, params) => {
  const log = logs.get(tabId);
  if (!log) return;
  const request = log.requests[params.requestId];
  switch (method) {
    case 'Network.requestWillBeSent':
      if (!request) log.order.push(params.requestId);
      log.requests[params.requestId] = {method: params.request.method, url: params.request.url, type: params.type || ''};
      if (log.order.length > 500) delete log.requests[log.order.shift()];
      break;
    case 'Network.responseReceived':
      if (request) Object.assign(request, {status: params.response.status, mime: params.response.mimeType});
      break;
    case 'Network.loadingFailed':
      if (request) request.failed = params.errorText;
      break;
    case 'Runtime.consoleAPICalled':
      log.console.push(params.type + ': ' + (params.args || []).map(a => String(a.value ?? a.description ?? a.type)).join(' '));
      break;
    case 'Runtime.exceptionThrown':
      log.console.push('exception: ' + (params.exceptionDetails.exception?.description ?? params.exceptionDetails.text));
      break;
  }
  if (log.console.length > 300) log.console.splice(0, log.console.length - 300);
});

async function run(method, p) {
  switch (method) {
    case 'tabs': {
      const shown = (await currentTab().catch(() => null))?.id;
      return (await chrome.tabs.query({})).map(t => ({id: t.id, window: t.windowId, active: t.active, current: t.id === shown, title: t.title, url: t.url}));
    }
    case 'open': {
      let tab;
      try {
        tab = await chrome.tabs.create({url: p.url});
      } catch {  // No window: a new window, which does not take the focus.
        tab = (await chrome.windows.create({url: p.url, focused: false})).tabs[0];
      }
      current = tab.id;
      return tab.id;
    }
    case 'navigate':
      await chrome.tabs.update((await currentTab()).id, {url: p.url});
      return null;
    case 'select':
      current = Number(p.tab);
      await chrome.tabs.update(current, {active: true});
      return null;
    case 'close':
      await chrome.tabs.remove(Number(p.tab));
      if (current === Number(p.tab)) current = null;
      return null;
    case 'back': return chrome.tabs.goBack((await currentTab()).id);
    case 'forward': return chrome.tabs.goForward((await currentTab()).id);
    case 'reload': return chrome.tabs.reload((await currentTab()).id);
    case 'cdp': {
      if (!CDP_METHODS.has(p.method)) throw new Error('mac-cu does not run the protocol command ' + p.method + ' in the user\'s Chrome.');
      const tabId = (await currentTab()).id;
      await attach(tabId);
      return chrome.debugger.sendCommand({tabId}, p.method, p.params || {});
    }
    case 'log': {
      const tabId = (await currentTab()).id;
      await attach(tabId);
      const log = logs.get(tabId);
      return {requests: log.order.map(id => ({id, ...log.requests[id]})), console: log.console};
    }
    default:
      throw new Error('Unknown command ' + method);
  }
}
