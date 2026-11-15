// UI_STRINGS_START
const STRINGS = {
  "ko": {
    "flow": "전체 흐름",
    "history": "지금까지",
    "chooseRun": "흐름 고르기",
    "skip": "목록으로 건너뛰기",
    "listView": "목록으로도 볼 수 있어요",
    "nodes": "하는 일",
    "handoffs": "주고받는 것",
    "yourTurn": "내가 할 일",
    "choiceEffects": "고르면 생기는 일",
    "nothing": "지금은 결정할 일이 없어요. 필요해지면 알려 드릴게요.",
    "needsYou": "읽고 결정해 주세요",
    "counts": "지금 흐름",
    "done": "끝남",
    "doing": "하는 중",
    "waiting": "앞 일을 기다림",
    "needs_you": "내 결정을 기다림",
    "returned": "고치러 돌아옴",
    "legend": "읽는 법",
    "ringLegend": "고리 한 칸은 한 번의 시도예요. 세 번까지 해 봐요.",
    "gateLegend": "문은 검사나 내 승인이에요. 노란 문은 나를 기다려요.",
    "socketLegend": "받는 쪽의 작은 동그라미는 채워지면 전달된 거예요.",
    "now": "지금",
    "whyReturned": "통과하지 못한 확인",
    "received": "받는 것",
    "outputs": "넘기는 것",
    "noHandoffs": "기록된 주고받기가 없어요.",
    "delivered": "받았어요",
    "notDelivered": "아직 기다려요",
    "from": "보낸 곳",
    "to": "받는 곳",
    "noReason": "돌아온 까닭이 따로 기록되지 않았어요.",
    "noReturns": "돌아온 적이 없어요.",
    "attempt": "{n}번째 시도 · 최대 {max}번",
    "notStarted": "아직 시작하지 않았어요",
    "passed": "끝났어요",
    "running": "만들고 있어요",
    "retrying": "고친 걸 다시 만들고 있어요",
    "submitted": "검사받고 있어요",
    "awaiting": "내 결정을 기다려요",
    "held": "다음 방향을 기다려요",
    "exhausted": "다음 계획이 필요해요",
    "noAction": "지금은 하실 일이 없어요. 세 번 안에 통과하지 못하면 알려 드릴게요.",
    "read": "읽고 결정하기",
    "why": "왜 내가 봐야 하나요",
    "verified": "이미 확인된 것",
    "unverified": "아직 확인 안 된 것",
    "workerNote": "쓴 쪽의 메모",
    "notRecorded": "따로 기록되지 않았어요.",
    "ifApproved": "이대로 하면",
    "ifRejected": "돌려보내면",
    "undo": "나중에 바꾸려면",
    "approve": "통과",
    "sendBack": "돌려보내기",
    "answer": "답 보내기",
    "answerLabel": "답을 적어 주세요",
    "backReason": "돌려보낼 때는 고칠 곳을 적어 주세요",
    "required": "고칠 곳을 먼저 적어 주세요.",
    "sending": "보내고 있어요…",
    "answerFailed": "답을 보내지 못했어요. 연결을 확인하고 다시 해 주세요.",
    "stale": "이미 답했거나 일이 바뀌었어요. 최신 흐름을 다시 읽어 주세요.",
    "answered": "답을 보냈어요. 다음 확인에서 반영돼요.",
    "details": "자세한 근거 보기",
    "loadEvidence": "근거 읽기",
    "noEvidence": "읽을 근거 기록이 없어요.",
    "evidenceFailed": "근거를 읽지 못했어요. 다시 해 주세요.",
    "noProjects": "등록된 프로젝트가 없어요. 프로젝트에서 새 흐름을 시작한 뒤 다시 연결해 주세요.",
    "noRun": "아직 흐름이 없어요. 프로젝트에서 새 흐름을 시작한 뒤 다시 연결해 주세요.",
    "noPlan": "아직 계획이 없어요. 이 흐름에 계획을 넣으면 여기에 나타나요.",
    "unreadable": "이 흐름을 읽지 못했어요. 기록을 확인하거나 다른 흐름을 골라 주세요.",
    "lost": "연결이 끊겼어요. 서버가 켜져 있는지 확인한 뒤 다시 연결해 주세요.",
    "unauthorized": "이 창의 열쇠가 없거나 바뀌었어요. 서버를 켤 때 받은 주소를 다시 열어 주세요.",
    "retry": "다시 연결",
    "loading": "흐름을 읽고 있어요…",
    "fallback": "그림을 그릴 수 없어 목록으로 보여 드려요. 모든 결정은 여기서 할 수 있어요.",
    "lessons": "배운 것",
    "noLessons": "아직 기록된 배움이 없어요.",
    "planOrder": "전체 시간 순서는 기록에서 알 수 없어 계획 순서로 보여 드려요. 각 일의 시도는 일어난 순서예요.",
    "returns": "통과하지 못한 확인",
    "complete": "모든 흐름이 끝났어요!",
    "waitingBubble": "읽어 주세요!",
    "attemptBubble": "{n}번째 시도예요",
    "make": "만들기",
    "check": "검사",
    "fix": "고치기",
    "pastOrbit": "앞서 돌아온 시도",
    "unnamed": "이 일",
    "handoff": "넘길 결과",
    "overview": "일 {total}곳 · 끝남 {done}곳 · 내 결정 {needs}개",
    "reviewed": "다른 눈으로 검토했어요",
    "runOption": "{project} · 흐름 {n}",
    "purposeReview": "사람이 직접 살펴봐야 하는 결과를 받아들일지 정해 주세요.",
    "purposeAuthorization": "되돌리기 어려운 일을 허락할지 정해 주세요.",
    "purposeTrajectory": "평소와 다르게 진행된 일을 받아들일지 정해 주세요.",
    "purposeHold": "멈춰 둔 일을 어떻게 이어 갈지 정해 주세요.",
    "purposeDirection": "다음에 어느 방향으로 갈지 알려 주세요.",
    "purposeInformation": "계속하는 데 필요한 정보를 알려 주세요.",
    "purposeNeutral": "내용을 읽고 어떻게 할지 정해 주세요.",
    "allow": "허락하기",
    "accept": "받아들이기",
    "continue": "계속하기",
    "confirmChoice": "결정 보내기",
    "evidenceReminder": "결정하기 전에 읽어야 할 근거가 기록되어 있어요.",
    "decisionClosed": "이 결정은 더 이상 열려 있지 않아요. 적던 답은 지웠어요.",
    "runChanged": "흐름이 바뀌어서 결정을 닫고 적던 답을 지웠어요.",
    "brand": "Graph flow",
    "failed": "통과하지 못한 것",
    "acceptAnyway": "그래도 받아들이기",
    "used_all_attempts": "세 번의 시도를 모두 썼어요.",
    "timed_out": "정해진 시간을 넘겼어요.",
    "left_its_files": "맡은 파일의 범위를 벗어났어요.",
    "untitledFailure": "설명이 없는 확인 하나가 통과하지 못했어요."
  },
  "en": {
    "flow": "Whole flow",
    "history": "So far",
    "chooseRun": "Choose a flow",
    "skip": "Skip to the list",
    "listView": "Read the flow as a list",
    "nodes": "The work",
    "handoffs": "What is handed over",
    "yourTurn": "Your turn",
    "choiceEffects": "What each choice does",
    "nothing": "Nothing needs you right now. We’ll let you know when it does.",
    "needsYou": "Ready for you to read",
    "counts": "At a glance",
    "done": "Done",
    "doing": "In progress",
    "waiting": "Waiting to begin",
    "needs_you": "Waiting for you",
    "returned": "Came back",
    "legend": "How to read it",
    "ringLegend": "Each ring segment is one attempt, up to three.",
    "gateLegend": "A gate is a check or approval. Amber waits for you.",
    "socketLegend": "A filled socket means the handoff has arrived.",
    "now": "Now",
    "whyReturned": "Checks that did not pass",
    "received": "Receives",
    "outputs": "Hands over",
    "noHandoffs": "No handoff is recorded.",
    "delivered": "Delivered",
    "notDelivered": "Not delivered yet",
    "from": "From",
    "to": "To",
    "noReason": "No readable reason was recorded.",
    "noReturns": "No returns so far.",
    "attempt": "Attempt {n} of {max}",
    "notStarted": "Not started",
    "passed": "Finished",
    "running": "Making it",
    "retrying": "Working on the next attempt",
    "submitted": "Being checked",
    "awaiting": "Waiting for you",
    "held": "Waiting for the next direction",
    "exhausted": "Needs a new plan",
    "noAction": "Nothing to do here now. You’ll be told if three attempts are not enough.",
    "read": "Read and decide",
    "why": "Why you are needed",
    "verified": "Already verified",
    "unverified": "Not yet verified",
    "workerNote": "The worker’s note",
    "notRecorded": "Not recorded.",
    "ifApproved": "If you proceed",
    "ifRejected": "If sent back",
    "undo": "How to undo",
    "approve": "Approve",
    "sendBack": "Send back",
    "answer": "Send answer",
    "answerLabel": "Write your answer",
    "backReason": "To send it back, describe what needs changing",
    "required": "Please describe what needs changing first.",
    "sending": "Sending…",
    "answerFailed": "Your answer could not be sent. Check the connection and try again.",
    "stale": "This question was answered or changed. Read the refreshed flow.",
    "answered": "Answer sent. The next check will apply it.",
    "details": "Details and raw evidence",
    "loadEvidence": "Read evidence",
    "noEvidence": "No evidence log is recorded.",
    "evidenceFailed": "The evidence could not be read. Please try again.",
    "noProjects": "No project is registered. Start a flow in your project, then reconnect.",
    "noRun": "There is no run yet. Start a flow in your project, then reconnect.",
    "noPlan": "This flow has no plan yet. Add a plan and it will appear here.",
    "unreadable": "This flow cannot be read. Check its records or choose another flow.",
    "lost": "Connection lost. Check that the server is running, then reconnect.",
    "unauthorized": "This window’s key is missing or changed. Reopen the address you received when starting the server.",
    "retry": "Reconnect",
    "loading": "Reading the flow…",
    "fallback": "The map is unavailable, so here is the list. All decisions still work.",
    "lessons": "What we learned",
    "noLessons": "No lessons recorded yet.",
    "planOrder": "The overall time order is unknown, so this follows plan order. Each task’s attempts are in their recorded order.",
    "returns": "Checks that did not pass",
    "complete": "The whole flow is complete!",
    "waitingBubble": "Please read this.",
    "attemptBubble": "On attempt {n}.",
    "make": "Make",
    "check": "Check",
    "fix": "Fix",
    "pastOrbit": "Earlier returned attempt",
    "unnamed": "This task",
    "handoff": "Handoff",
    "overview": "{total} tasks · {done} done · {needs} waiting for you",
    "reviewed": "Reviewed with another pair of eyes",
    "runOption": "{project} · flow {n}",
    "purposeReview": "Decide whether to accept a result that needs a human look.",
    "purposeAuthorization": "Decide whether to allow work that is hard to undo.",
    "purposeTrajectory": "Decide whether to accept work with an unclean path.",
    "purposeHold": "Decide how to continue work that was put on hold.",
    "purposeDirection": "Tell us which direction to take next.",
    "purposeInformation": "Provide the information needed to continue.",
    "purposeNeutral": "Read the details and decide what to do.",
    "allow": "Allow",
    "accept": "Accept",
    "continue": "Continue",
    "confirmChoice": "Send decision",
    "evidenceReminder": "There is recorded evidence to read before deciding.",
    "decisionClosed": "This decision is no longer open. Your draft was discarded.",
    "runChanged": "The flow changed, so the decision was closed and your draft discarded.",
    "brand": "Graph flow",
    "failed": "Did not pass",
    "acceptAnyway": "Accept anyway",
    "used_all_attempts": "All three attempts were used.",
    "timed_out": "A check exceeded its time limit.",
    "left_its_files": "Work went beyond its assigned files.",
    "untitledFailure": "A check without a description did not pass."
  }
};
// UI_STRINGS_END

export function sameRun(a, b) { return a?.project === b?.project && a?.run === b?.run; }
export function purposeWording(purpose, language = 'en') {
  const keys = {human_check:'purposeReview', review:'purposeReview', lane3:'purposeAuthorization', authorization:'purposeAuthorization', trajectory:'purposeTrajectory', hold:'purposeHold', direction:'purposeDirection', information:'purposeInformation'};
  const key = Object.hasOwn(keys, purpose) ? keys[purpose] : 'purposeNeutral';
  return STRINGS[language][key];
}
export function purposeAction(purpose, language = 'en', failed = []) {
  if (purpose === 'hold' || failed.length) return STRINGS[language].acceptAnyway;
  const keys = {lane3:'allow', authorization:'allow', human_check:'accept', review:'accept', trajectory:'accept', hold:'continue'};
  return STRINGS[language][Object.hasOwn(keys, purpose) ? keys[purpose] : 'confirmChoice'];
}
export function canApprove(session) {
  return !!session && (!(session.purpose === 'lane3' || session.purpose === 'authorization' ||
    session.kind === 'authorization' || session.purpose === 'hold' || session.failed?.length) || session.detailsOpened);
}
export function decisionQuestion(d) {
  const generated = `Approve ${d.record_purpose ?? d.purpose} for ${d.node}?`;
  return d.node && d.question === generated ? '' : d.question;
}
export function createDecisionController() {
  let session = null, view = null, chosen = null;
  const requests = new WeakMap();
  const current = () => !!session && view?.decisions.some(d => d.id === session.target.id);
  const update = d => { session.decision = d; session.purpose = d.purpose; session.kind = d.kind; session.failed = d.failed || []; };
  const controller = {
    get session() { return session; },
    get requiresDetails() { return !!session && !canApprove({...session, detailsOpened:false}); },
    open(id) {
      if (session?.busy) return null;
      const decision = view?.decisions.find(d => d.id === id);
      if (!decision || !chosen) return null;
      if (!session || !sameRun(session.target, chosen) || session.target.id !== id) {
        session = {target:Object.freeze({project:chosen.project, run:chosen.run, id}), draft:'', detailsOpened:false, busy:false};
      }
      update(decision); return session;
    },
    close() {
      if (session?.busy) return false;
      session = null; return true;
    },
    refresh(nextView, nextChosen) {
      // Keep the submitting view and its target until the response is reported.
      if (session?.busy) return '';
      view = nextView; chosen = nextChosen;
      if (!session) return '';
      const reason = !sameRun(session.target, chosen) ? 'runChanged' : !current() ? 'decisionClosed' : '';
      if (reason) session = null;
      else update(view.decisions.find(d => d.id === session.target.id));
      return reason;
    },
    setDraft(text) { if (session && !session.busy) session.draft = text; },
    openDetails() { if (current()) session.detailsOpened = true; },
    canSubmit(outcome, text = session?.draft || '') {
      if (!current() || session.busy) return false;
      const question = ['direction','information'].includes(session.kind);
      if (question ? outcome !== 'answered' : !['approved','revision_requested','rejected'].includes(outcome)) return false;
      return outcome === 'approved' ? canApprove(session) : !!text.trim();
    },
    buildRequest(outcome, text = session?.draft || '') {
      if (!controller.canSubmit(outcome, text)) return null;
      session.draft = text; session.busy = true;
      const request = {...session.target, outcome, answer:text.trim()};
      requests.set(request, session); return request;
    },
    onResult(request, error = null) {
      const matches = !!session && session === requests.get(request) && session.busy;
      requests.delete(request);
      const notice = !error ? 'answered' : error.status === 409 ? 'stale' : 'answerFailed';
      if (matches) {
        session.busy = false;
        if (!error || error.status === 409) session = null;
      }
      return {notice, close:matches && !session, refresh:sameRun(request, chosen)};
    }
  };
  return controller;
}

if (typeof document !== 'undefined') {
const language = navigator.language.toLowerCase().startsWith('ko') ? 'ko' : 'en';
const t = (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, String(value)), STRINGS[language][key]);
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; };
const button = (text, action, cls) => { const b = el('button', text, cls); b.type = 'button'; b.addEventListener('click', action); return b; };
const clear = e => e.replaceChildren();
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const startup = new URL(location.href);
const tokenKey = 'graph-flow-token:' + location.port;
let token = startup.searchParams.get('t') || '';
try {
  if (!startup.searchParams.has('t')) token = sessionStorage.getItem(tokenKey) || '';
  if (token) sessionStorage.setItem(tokenKey, token);
} catch { /* Storage may be unavailable; the printed address still works. */ }
startup.searchParams.delete('t');
history.replaceState(null, '', startup.pathname + startup.search + startup.hash);
document.documentElement.lang = language;
document.querySelectorAll('[data-i18n]').forEach(e => { e.textContent = t(e.dataset.i18n); });
document.querySelector('nav').setAttribute('aria-label', t('flow'));
$('map').setAttribute('aria-label', t('flow'));
let chosen = null, projects = [], view = null, fingerprint = '', mode = 'flow', selected = null;
let mapFailed = false, queuedRefresh = false;
let timer = 0, loading = false, generation = 0, renderer = null;
const decisionController = createDecisionController();
let decisionUI = null, decisionNotice = '';

async function api(path, body, text = false) {
  const response = await fetch(path, {method: body ? 'POST' : 'GET', headers: {'X-GF-Token': token, ...(body ? {'Content-Type':'application/json'} : {})}, ...(body ? {body:JSON.stringify(body)} : {})});
  if (!response.ok) { const err = new Error('request'); err.status = response.status; throw err; }
  return text ? response.text() : response.json();
}
function query(route, extra = {}, target = chosen) { return route + '?' + new URLSearchParams({project:target.project, run:target.run, ...extra}); }
function notice(key, retry = false) { const box = $('notice'); clear(box); box.hidden = !key; if (key) box.append(el('span', t(key))); if (retry) box.append(button(t('retry'), () => refresh(true))); }
function title(node) { return node && node.title && node.title !== node.id ? node.title : t('unnamed'); }
function otherTitle(value) { return view.nodes.some(n => n.id === value && n.title === value) ? t('unnamed') : value || t('unnamed'); }
// Legacy plans may have only an artifact path; keep that technical fallback out of normal views.
function label(value) { return !value || /[\/\\]|\.[a-z0-9]{1,8}$/.test(value) || view.nodes.some(n => n.id === value) ? t('handoff') : value; }
function question(d) { return decisionQuestion(d); }
function decisionTitle(d) { return title(view.nodes.find(n => n.id === d.node)); }
function decisionHeading(parent, d, tag) {
  parent.append(el(tag, decisionTitle(d)), el('p', purposeWording(d.purpose, language)));
  if (d.purpose === 'trajectory') textList(parent, (d.trajectory_reasons || []).map(key => t(key)));
  if (question(d)) parent.append(el('p', question(d)));
}
function needs(node) { return view.decisions.some(d => d.node === node.id); }
function status(node) {
  if (needs(node)) return t('awaiting');
  if (node.status === 'passed') return t('passed');
  if (node.status === 'running') return t(node.attempts > 1 ? 'retrying' : 'running');
  if (['submitted','unverified'].includes(node.status)) return t('submitted');
  if (['replan','exhausted'].includes(node.status)) return t('exhausted');
  if (node.status === 'rejected') return t('returned');
  if (['held','awaiting_approval'].includes(node.status)) return t('held');
  return t('notStarted');
}
function attempts(node) { return node.attempts ? t('attempt', {n:node.attempts, max:node.max_attempts}) : t('notStarted'); }
function card(heading, body, paper = false) { const c = el('div', undefined, 'card' + (paper ? ' paper' : '')); c.append(el('p', heading, 'eyebrow')); if (body) c.append(el('p', body)); return c; }
function textList(parent, items, empty = 'notRecorded') { const list = el('ul'); if (!items.length) list.append(el('li', t(empty))); else items.forEach(text => list.append(el('li', text))); parent.append(list); }
function countCard() {
  const c = card(t('counts')); const list = el('ul', undefined, 'count-list');
  for (const key of ['done','doing','needs_you','waiting','returned']) { const item = el('li'); item.append(el('span', undefined, 'dot ' + key), el('span', `${t(key)} ${view.counts[key]}`)); list.append(item); }
  c.append(list); return c;
}
function failedBlock(parent, d) {
  if (!d.failed?.length) return;
  const failed = card(t('failed')); failed.classList.add('failed');
  textList(failed, d.failed.map(text => text === STRINGS.en.untitledFailure ? t('untitledFailure') : text)); parent.append(failed);
}
function decisionCard(d) {
  const c = card(t('yourTurn'), null, true); decisionHeading(c, d, 'h3'); failedBlock(c, d); if (d.context.why) c.append(el('p', d.context.why));
  for (const key of ['if_approved','if_rejected','undo']) { if (d.context[key]) { c.append(el('small', t({if_approved:'ifApproved',if_rejected:'ifRejected',undo:'undo'}[key])), el('p', d.context[key])); } }
  c.append(button(t('read'), () => openDecision(d.id), 'amber')); return c;
}
function handoffsCard(key, rows, direction) {
  const c = card(t(key)); const list = el('ul');
  if (!rows.length) c.append(el('p', t('noHandoffs')));
  for (const row of rows) list.append(el('li', `${label(row.label)} · ${t(direction)} ${otherTitle(row.other_title)} · ${t(row.delivered ? 'delivered' : 'notDelivered')}`));
  c.append(list); return c;
}
function panel() {
  const p = $('panel'); clear(p);
  const node = view.nodes.find(n => n.id === selected);
  p.append(el('p', t(node ? 'now' : 'yourTurn'), 'eyebrow'), el('h2', node ? title(node) : t(view.decisions.length ? 'needsYou' : 'counts')));
  if (node) {
    p.append(card(t('now'), `${status(node)}. ${attempts(node)}. ${node.summary}`, true));
    const reasons = card(t('whyReturned'), null, true); textList(reasons, node.returned_reasons.flat(), node.returned_reasons.length ? 'noReason' : 'noReturns'); p.append(reasons);
    p.append(handoffsCard('received', node.inputs, 'from'), handoffsCard('outputs', node.outputs, 'to'));
    const ds = view.decisions.filter(d => d.node === node.id); ds.forEach(d => p.append(decisionCard(d)));
    if (!ds.length) p.append(card(t('yourTurn'), t('noAction')));
    p.append(button(t('flow'), wholeFlow, 'primary'));
  } else {
    view.decisions.forEach(d => p.append(decisionCard(d)));
    if (!view.decisions.length) p.append(el('p', t('nothing')));
    p.append(countCard()); const legend = el('div', undefined, 'legend'); legend.append(el('p', t('legend'), 'eyebrow')); for (const key of ['ringLegend','gateLegend','socketLegend']) legend.append(el('p', t(key))); p.append(legend);
  }
}
function accessible() {
  clear($('node-list')); clear($('edge-list')); clear($('decision-list'));
  view.nodes.forEach(n => { const item = el('li', undefined, 'card'); item.append(button(title(n), () => selectNode(n.id)), el('p', status(n)), el('p', attempts(n), 'muted'), el('p', n.summary)); if (n.returned_reasons.length) textList(item, n.returned_reasons.flat(), 'noReason'); $('node-list').append(item); });
  view.edges.forEach(e => { const a = view.nodes.find(n => n.id === e.from), b = view.nodes.find(n => n.id === e.to); $('edge-list').append(el('li', `${title(a)} → ${title(b)} · ${label(e.label)} · ${t(e.delivered ? 'delivered' : 'notDelivered')}`)); });
  view.decisions.forEach(d => { const item = el('li'); item.append(button(t('read'), () => openDecision(d.id))); decisionHeading(item, d, 'h3'); failedBlock(item, d); if (d.context.why) item.append(el('p', d.context.why)); $('decision-list').append(item); });
  if (!view.decisions.length) $('decision-list').append(el('li', t('nothing')));
}
function showMode(next) {
  if (next !== 'decision' && !discardDecision()) return false;
  mode = next; $('flow').hidden = next !== 'flow'; $('decision').hidden = next !== 'decision'; $('history').hidden = next !== 'history';
  $('flow-tab').setAttribute('aria-pressed', String(next === 'flow')); $('history-tab').setAttribute('aria-pressed', String(next === 'history'));
  if (renderer) renderer.wake(); return true;
}
function discardDecision() {
  if (!decisionController.close()) return false;
  decisionUI = null; clear($('decision')); return true;
}
function closeInvalidDecision(run, decisions) {
  const reason = decisionController.refresh({decisions}, run);
  if (!reason) return false;
  wholeFlow(); decisionNotice = reason; notice(decisionNotice); return true;
}
function wholeFlow() { if (!showMode('flow')) return; selected = null; if (view) panel(); if (renderer) renderer.select(null); }
function selectNode(id) { if (!showMode('flow')) return; selected = id; panel(); if (renderer) renderer.select(id); }
function focusHeading(heading) { heading.tabIndex = -1; heading.focus(); }
function openDecision(id, focus = true) {
  const session = decisionController.open(id); if (!session) return;
  const current = () => decisionController.session === session;
  const d = session.decision;
  if (decisionUI?.session === session) { decisionUI.update(); return; }
  decisionNotice = ''; notice('');
  showMode('decision'); const box = $('decision'); clear(box);
  const reading = card(t('yourTurn'), null, true); reading.classList.add('reading');
  const introduction = el('div'); reading.append(introduction);
  const report = el('div', undefined, 'worker-report'), note = el('div', undefined, 'speech');
  const mascot = el('img'); mascot.src = '/static/assets/frog-report.png'; mascot.alt = ''; report.append(mascot, note); reading.append(report);
  const outcomes = card(t('choiceEffects'), null, true); reading.append(outcomes);
  const isQuestion = ['direction','information'].includes(d.kind);
  const answerLabel = el('label', t(isQuestion ? 'answerLabel' : 'backReason')); answerLabel.htmlFor = 'answer-text';
  const input = el('textarea'); input.id = 'answer-text'; input.required = true; input.value = session.draft;
  input.addEventListener('input', () => { if (current()) { decisionController.setDraft(input.value); updateActions(); } }); reading.append(answerLabel, input);
  const message = el('p'); message.id = 'answer-message'; message.setAttribute('role','status'); reading.append(message);
  const actions = el('div'); actions.id = 'answer-actions';
  const updateActions = () => {
    actions.querySelectorAll('button[data-outcome]').forEach(b => { b.disabled = !current() || !decisionController.canSubmit(b.dataset.outcome, input.value); });
    backButton.disabled = !!decisionController.session?.busy;
    input.disabled = !current() || session.busy; $('picker').disabled = !!decisionController.session?.busy;
  };
  const send = async outcome => {
    if (!current()) return;
    const request = decisionController.buildRequest(outcome, input.value);
    if (!request) { if (!input.value.trim() && outcome !== 'approved') { message.textContent = t('required'); input.focus(); } return; }
    updateActions(); message.textContent = t('sending');
    let error = null;
    try { await api('/api/answer', request); } catch (failure) { error = failure; }
    const result = decisionController.onResult(request, error);
    if (result.close && mode === 'decision') wholeFlow();
    decisionNotice = result.notice; notice(decisionNotice);
    if (current()) { message.textContent = t(result.notice); updateActions(); }
    $('picker').disabled = !!decisionController.session?.busy;
    if (result.refresh) refresh(true);
  };
  let approveButton;
  const actionButton = (outcome, text, cls) => { const b = button(text, () => send(outcome), cls); b.dataset.outcome = outcome; return b; };
  if (isQuestion) actions.append(actionButton('answered', t('answer'), 'primary'));
  else { approveButton = actionButton('approved', '', 'primary'); actions.append(approveButton, actionButton('revision_requested', t('sendBack'))); }
  const backButton = button(t('flow'), wholeFlow); actions.append(backButton); reading.append(actions);
  const right = el('div'), surrounding = el('div'); right.append(surrounding);
  const details = el('details', undefined, 'evidence'); details.append(el('summary', t('details'))); const raw = el('pre');
  details.open = session.detailsOpened;
  const markDetailsOpened = () => { if (current() && details.open) { decisionController.openDetails(); updateActions(); } };
  details.addEventListener('toggle', markDetailsOpened);
  const reminder = el('p', t('evidenceReminder'));
  reminder.append(button(t('details'), () => { if (current()) { details.open = true; markDetailsOpened(); details.querySelector('summary').focus(); } })); reading.append(reminder);
  details.append(button(t('loadEvidence'), async () => {
    if (!current()) return;
    raw.textContent = t('loading');
    try {
      const payload = await api(query('/api/run', {}, session.target));
      if (!current()) return;
      const decision = payload.state.decisions[session.target.id];
      // Raw records stay inside this deliberately opened disclosure.
      const evidence = decision ? decision.evidence : null; const paths = new Set();
      const collect = value => { if (Array.isArray(value)) value.forEach(collect); else if (value && typeof value === 'object') { if (typeof value.log === 'string') paths.add(value.log); Object.values(value).forEach(collect); } };
      collect(evidence);
      const logs = await Promise.all([...paths].map(path => api(query('/api/evidence', {path}, session.target), null, true)));
      if (!current()) return;
      raw.textContent = (evidence ? JSON.stringify(evidence, null, 2) : t('noEvidence')) + (logs.length ? '\n\n' + logs.join('\n\n') : '\n' + t('noEvidence'));
    } catch { if (current()) raw.textContent = t('evidenceFailed'); }
  }), raw); right.append(details); box.append(reading, right);
  const update = () => {
    const decision = session.decision;
    clear(introduction); decisionHeading(introduction, decision, 'h2'); const heading = introduction.querySelector('h2'); heading.id = 'decision-title';
    const node = view.nodes.find(n => n.id === decision.node); if (node) introduction.append(el('p', node.summary));
    note.textContent = decision.worker_note || t('notRecorded');
    clear(outcomes); outcomes.append(el('p', t('choiceEffects'), 'eyebrow'));
    for (const [key, name] of [['if_approved','ifApproved'],['if_rejected','ifRejected'],['undo','undo']]) outcomes.append(el('small', t(name)), el('p', decision.context[key] || t('notRecorded')));
    clear(surrounding); surrounding.append(card(t('why'), decision.context.why || t('notRecorded')));
    failedBlock(surrounding, decision);
    for (const key of ['verified','unverified']) { const c = card(t(key)); textList(c, decision[key]); surrounding.append(c); }
    reminder.hidden = !decision.has_evidence && !decisionController.requiresDetails;
    if (approveButton) approveButton.textContent = purposeAction(decision.purpose, language, decision.failed);
    updateActions();
  };
  decisionUI = {session, update}; update(); if (focus) focusHeading(introduction.querySelector('h2'));
}
function historyView() {
  if (!showMode('history')) return; const box = $('history'); clear(box); box.append(el('p', t('planOrder'), 'muted'));
  const strip = el('ol', undefined, 'timeline');
  view.nodes.forEach(n => {
    const laps = n.laps.length ? n.laps : [needs(n) ? 'waiting_for_you' : 'unused'];
    laps.forEach((lap, i) => { const item = el('li'); item.append(el('span', undefined, 'mini-planet ' + lap), button(title(n), () => selectNode(n.id)), el('p', lap === 'returned' ? t('returned') : lap === 'passed' ? t('passed') : status(n), 'muted')); if (n.laps.length) item.append(el('small', t('attempt', {n:i + 1, max:n.max_attempts}))); strip.append(item); });
  }); box.append(strip);
  const grid = el('div', undefined, 'history-grid'); const returns = el('div'); returns.append(el('h3', t('returns')));
  view.nodes.filter(n => n.returned_reasons.length).forEach(n => { const c = card(title(n), null, true); textList(c, n.returned_reasons.flat(), 'noReason'); returns.append(c); });
  if (!view.nodes.some(n => n.returned_reasons.length)) returns.append(el('p', t('noReturns')));
  const lessons = el('div'); lessons.append(el('h3', t('lessons'))); view.lessons.forEach(l => { lessons.append(card(l.node_title ? otherTitle(l.node_title) : t('lessons'), l.text)); }); if (!view.lessons.length) lessons.append(el('p', t('noLessons')));
  const counts = el('div'); counts.append(countCard(), button(t('flow'), wholeFlow, 'primary')); grid.append(returns, lessons, counts); box.append(grid);
}
function applyView(next) {
  if (decisionController.session?.busy) return;
  closeInvalidDecision(chosen, next.decisions);
  const nextFingerprint = JSON.stringify(next); if (nextFingerprint === fingerprint) return;
  view = next; fingerprint = nextFingerprint; showMode(mode); if (!view.nodes.some(n => n.id === selected)) selected = null;
  $('title').textContent = view.title || t('brand'); $('subtitle').textContent = view.complete ? t('complete') : t('overview', {total:view.nodes.length, done:view.counts.done, needs:view.counts.needs_you});
  accessible(); panel(); if (renderer) renderer.update(view, selected);
  if (mode === 'history') historyView();
  if (mode === 'decision' && decisionController.session) openDecision(decisionController.session.target.id, false);
}
function setChosen(next) {
  if (decisionController.session?.busy || sameRun(chosen, next)) return;
  closeInvalidDecision(next, []); chosen = next; generation++; resetView(); showMode('flow');
}
function chooseRuns(data) {
  projects = data.projects;
  const runs = projects.flatMap(p => (p.runs || []).map((r, i) => ({...r, project:p.root, projectName:p.name, number:i + 1})));
  runs.sort((a,b) => Number(b.status === 'open') - Number(a.status === 'open') || (b.last_event || '').localeCompare(a.last_event || ''));
  if (!chosen || !runs.some(r => r.project === chosen.project && r.id === chosen.run)) { const first = runs.find(r => !r.error) || runs[0]; setChosen(first ? {project:first.project,run:first.id} : null); }
  const picker = $('picker'); picker.disabled = !!decisionController.session?.busy; clear(picker);
  runs.forEach((r, i) => { const option = el('option', t('runOption', {project:r.projectName,n:r.number})); option.value = String(i); option.selected = !!chosen && r.project === chosen.project && r.id === chosen.run; picker.append(option); });
  $('picker-label').hidden = runs.length < 2;
  picker.onchange = () => { if (decisionController.session?.busy) return; const r = runs[Number(picker.value)]; setChosen({project:r.project,run:r.id}); refresh(true); };
  return runs.find(r => chosen && r.project === chosen.project && r.id === chosen.run);
}
async function refresh(force = false) {
  if (document.hidden) return;
  if (decisionController.session?.busy) { schedule(); return; }
  if (loading) { queuedRefresh = queuedRefresh || force; return; }
  loading = true; const currentGeneration = generation;
  try {
    const projectData = await api('/api/projects');
    if (currentGeneration !== generation || document.hidden || decisionController.session?.busy) return;
    const available = chooseRuns(projectData);
    if (currentGeneration !== generation) { queuedRefresh = true; return; }
    if (!projects.length) { resetView(); notice(decisionNotice || 'noProjects'); return; }
    if (!chosen) { resetView(); notice(decisionNotice || (projects.some(p => p.error) ? 'unreadable' : 'noRun')); return; }
    if (available && available.error) { resetView(); notice(decisionNotice || 'unreadable', true); return; }
    const data = await api(query('/api/run')); if (currentGeneration !== generation || document.hidden || decisionController.session?.busy) return;
    notice(decisionNotice || (!data.plan ? 'noPlan' : mapFailed ? 'fallback' : '')); applyView(data.view);
  } catch (error) { if (currentGeneration === generation) notice(error.status === 401 ? 'unauthorized' : error.status === 400 || error.status === 404 || error.status === 500 ? 'unreadable' : 'lost', true); }
  finally { loading = false; if (queuedRefresh) { queuedRefresh = false; refresh(true); } else schedule(); }
}
function resetView() { closeInvalidDecision(chosen, []); view = null; selected = null; fingerprint = ''; ['node-list','edge-list','decision-list','panel'].forEach(id => clear($(id))); if (renderer) renderer.update({nodes:[],edges:[],decisions:[],complete:false}, null); $('flow').hidden = true; $('history').hidden = true; $('decision').hidden = true; $('subtitle').textContent = ''; }
function schedule() { clearTimeout(timer); if (!document.hidden) timer = setTimeout(refresh, 2000); }
$('flow-tab').addEventListener('click', () => { if (view) wholeFlow(); });
$('history-tab').addEventListener('click', () => { if (view) historyView(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && view) wholeFlow(); });
document.addEventListener('visibilitychange', () => { clearTimeout(timer); if (renderer) renderer.wake(); if (!document.hidden) refresh(true); });
reduced.addEventListener('change', () => { if (renderer) renderer.wake(); });
notice('loading'); refresh();

async function createMap() {
  const THREE = await import('/static/vendor/three.module.min.js');
  const {CSS2DRenderer, CSS2DObject} = await import('/static/vendor/CSS2DRenderer.js');
  const host = $('map');
  const webgl = new THREE.WebGLRenderer({antialias:true, alpha:false});
  webgl.setPixelRatio(Math.min(devicePixelRatio || 1, 2)); webgl.setClearColor('#221a38');
  webgl.domElement.setAttribute('aria-hidden','true');
  const labels = new CSS2DRenderer(); labels.domElement.className = 'labels';
  host.append(webgl.domElement, labels.domElement);
  const scene = new THREE.Scene();
  scene.add(new THREE.AmbientLight(0xffffff, .9));
  const light = new THREE.DirectionalLight(0xfff6ea, .8); light.position.set(-180,200,500); scene.add(light);
  const camera = new THREE.OrthographicCamera(-500,500,350,-350,.1,4000);
  let group = new THREE.Group(); scene.add(group);
  const ray = new THREE.Raycaster(), pointer = new THREE.Vector2();
  const ink = '#1a1330', colours = {passed:'#8fe6c0',current:'#c3b1ff',waiting_for_you:'#ffd166',returned:'#ff9479',unused:'#6a5a8e',open:'#8fe6c0',closed:'#6a5a8e'};
  const textures = {}, loader = new THREE.TextureLoader();
  for (const pose of ['wave','walk-a','walk-b','report']) {
    textures[pose] = loader.load(`/static/assets/frog-${pose}.png`, () => wake()); textures[pose].colorSpace = THREE.SRGBColorSpace;
  }
  let data = {nodes:[],edges:[],decisions:[]}, chosenNode = null, items = [], routes = [], frogs = [], picks = [];
  let compactMap = false;
  let bounds = {cx:0,cy:0,width:1000,height:700}, frame = 0, dirty = true, tilt = 0, startTilt = 0, targetTilt = 0, transitionStart = null;
  const center = new THREE.Vector3(), anchorPoint = new THREE.Vector3();
  function cssObject(element, position, parent = group) { const object = new CSS2DObject(element); object.position.copy(position); parent.add(object); return object; }
  function mesh(geometry, colour, parent = group, outline = false) { const m = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({color:colour, side:outline ? THREE.BackSide : THREE.DoubleSide, transparent:true})); parent.add(m); return m; }
  function disk(radius, colour, x, y, z, parent = group) { const d = mesh(new THREE.CircleGeometry(radius,24),colour,parent); d.position.set(x,y,z); return d; }
  function tube(points, colour, radius = 2.4, parent = group) { return mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), Math.max(8,points.length * 6), radius, 6, false), colour,parent); }
  function arc(radius, from, length, colour, parent = group, thickness = 3.5) { const m = mesh(new THREE.TorusGeometry(radius,thickness,6,64,length),colour,parent); m.rotation.z = from; return m; }
  function frog(position, pose, sentence, walkingNode = null) {
    if (frogs.length >= 6) return;
    const material = new THREE.SpriteMaterial({map:textures[pose],transparent:true,depthTest:false});
    const sprite = new THREE.Sprite(material); sprite.scale.set(82,82,1); sprite.center.set(.5,0); sprite.position.copy(position); sprite.renderOrder = 10; group.add(sprite);
    const bubble = cssObject(el('div', sentence, 'speech'), position.clone().add(new THREE.Vector3(25,88,0)));
    frogs.push({sprite,bubble,walkingNode,pose,base:position.clone()});
  }
  function layout() {
    const parents = new Map(data.nodes.map(n => [n.id,[]])); data.edges.forEach(e => parents.get(e.to)?.push(e.from));
    const depths = new Map();
    function depth(id, visiting = new Set()) { if (depths.has(id)) return depths.get(id); if (visiting.has(id)) return 0; const seen = new Set(visiting); seen.add(id); const value = Math.max(0,...(parents.get(id) || []).map(p => depth(p,seen) + 1)); depths.set(id,value); return value; }
    const layers = new Map(); data.nodes.forEach(n => { const d = depth(n.id); if (!layers.has(d)) layers.set(d,[]); layers.get(d).push(n); });
    const positions = new Map();
    layers.forEach((nodes,d) => nodes.forEach((n,i) => positions.set(n.id,new THREE.Vector3(d * 300,((nodes.length-1)/2-i)*450,0))));
    const positionsArray = [...positions.values()]; const xs = positionsArray.map(p => p.x), ys = positionsArray.map(p => p.y);
    const minX = Math.min(0,...xs), maxX = Math.max(0,...xs), minY = Math.min(0,...ys), maxY = Math.max(0,...ys);
    bounds = {cx:(minX+maxX)/2,cy:(minY+maxY)/2,width:maxX-minX+350,height:maxY-minY+350}; return positions;
  }
  function dispose() {
    group.traverse(object => { if (object.isCSS2DObject) object.element.remove(); if (object.geometry) object.geometry.dispose(); if (object.material) object.material.dispose(); });
    scene.remove(group); group = new THREE.Group(); scene.add(group); items = []; routes = []; frogs = []; picks = [];
  }
  function update(next, id) {
    data = next; chosenNode = id; dispose(); const positions = layout();
    // Fixed stars are decoration, never event markers.
    for (let i=0;i<40;i++) { const x = bounds.cx + (Math.sin(i * 9.71) * .5) * bounds.width, y = bounds.cy + Math.cos(i * 7.31) * bounds.height * .47; disk(i%3 ? .8 : 1.6,'#cdbfe0',x,y,-40); }
    data.nodes.forEach(n => {
      const pos = positions.get(n.id), root = new THREE.Group(); root.position.copy(pos); group.add(root);
      const waiting = data.decisions.some(d => d.node === n.id), colour = waiting ? colours.waiting_for_you : n.status === 'passed' ? colours.passed : ['running','submitted','unverified'].includes(n.status) ? colours.current : n.returned_reasons.length ? colours.returned : '#3a2e5a';
      const outline = mesh(new THREE.SphereGeometry(43.7,32,20),colour === '#3a2e5a' ? '#6a5a8e' : ink,root,true);
      const planet = new THREE.Mesh(new THREE.SphereGeometry(41,32,20),new THREE.MeshToonMaterial({color:colour,emissive:colour,emissiveIntensity:.5,transparent:true})); root.add(planet); planet.userData.node = n.id; picks.push(planet);
      // A little face gives the map the same quiet cartoon character as the references.
      disk(11,'#fff6ea',-14,14,40,root).scale.y=.65;
      disk(4,ink,-9,-10,41,root); disk(7,ink,16,-7,40,root).scale.y=.75;
      if(n.status === 'passed') tube([new THREE.Vector3(-13,3,42),new THREE.Vector3(-5,-4,43),new THREE.Vector3(9,12,42)],ink,2.3,root);
      const ring = new THREE.Group(); root.add(ring);
      const total = Math.max(1,n.max_attempts || 3);
      for (let a=0;a<total;a++) arc(59,a*Math.PI*2/total + .14,Math.PI*2/total-.30,colours[n.laps[a] || 'unused'],ring);
      const labelButton = button('', () => selectNode(n.id), 'planet-label'); labelButton.append(el('strong',title(n)),el('small',status(n))); labelButton.setAttribute('aria-label',`${title(n)}. ${status(n)}. ${attempts(n)}`);
      const caption = cssObject(labelButton,new THREE.Vector3(0,-91,0),root);
      const orbit = new THREE.Group(); root.add(orbit); orbit.visible = false;
      const currentOrbit=arc(117,0,Math.PI*2,colours.current,orbit,.8); currentOrbit.scale.z=.35; currentOrbit.userData.currentOrbit=true;
      for(let a=0;a<n.returned_reasons.length;a++) { const o=arc(117,0,Math.PI*2,colours.returned,orbit,.8); o.position.y=-10-a*8; o.position.z=-8-a*6; o.scale.z=.35; o.material.opacity=.3; }
      const stations=[]; for(const [index,key] of ['make','check','fix'].entries()) { const angle=Math.PI/2-index*2*Math.PI/3; const p=new THREE.Vector3(Math.cos(angle)*117,Math.sin(angle)*117,8); disk(5.5,'#fff6ea',p.x,p.y,p.z,orbit); stations.push(cssObject(el('span',t(key),'station'),p.clone().multiplyScalar(1.50),orbit)); }
      items.push({n,root,ring,orbit,stations,caption,planet,outline});
    });
    data.edges.forEach(e => {
      const a=positions.get(e.from), b=positions.get(e.to); if(!a||!b)return;
      const direction=b.clone().sub(a).normalize(), start=a.clone().addScaledVector(direction,47), end=b.clone().addScaledVector(direction,-47); const middle=start.clone().lerp(end,.55); const lineGroup=new THREE.Group(); group.add(lineGroup);
      const distance=start.distanceTo(end), count=Math.max(2,Math.floor(distance/11));
      for(let i=0;i<=count;i++) { const p=start.clone().lerp(end,i/count); disk(1.8,colours[e.gate],p.x,p.y,-5,lineGroup); }
      const gate=new THREE.Group(); gate.position.copy(middle); lineGroup.add(gate); const gateColour=colours[e.gate];
      const door=mesh(new THREE.PlaneGeometry(17,20),ink,gate); door.position.set(0,3,1);
      const points=[new THREE.Vector3(-9,-7,3),new THREE.Vector3(-9,6,3),new THREE.Vector3(-7,13,3),new THREE.Vector3(0,16,3),new THREE.Vector3(7,13,3),new THREE.Vector3(9,6,3),new THREE.Vector3(9,-7,3)];
      tube(points,ink,4.6,gate); const arch = tube(points,gateColour,2.6,gate); arch.position.z=4;
      if(e.gate === 'waiting_for_you') { gate.scale.setScalar(1.35); const fill=mesh(new THREE.PlaneGeometry(13,19),'#62452f',gate); fill.position.set(0,2,2); disk(1.8,'#fff6ea',4,1,4,gate); const d=data.decisions.find(d=>d.node===e.from); if(d) { const hit=mesh(new THREE.PlaneGeometry(44,48),ink,gate); hit.position.set(0,4,12); hit.material.opacity=0; hit.material.depthWrite=false; hit.userData.decision=d.id; picks.push(hit); } }
      const socket=end.clone(); socket.z=18; if(e.delivered) { disk(8,ink,socket.x,socket.y,socket.z,lineGroup); disk(5.5,'#fff6ea',socket.x,socket.y,socket.z+1,lineGroup); }
      else for(let i=0;i<8;i++) { const angle=i*Math.PI/4; disk(1.5,'#6a5a8e',socket.x+Math.cos(angle)*6,socket.y+Math.sin(angle)*6,socket.z,lineGroup); }
      const caption=cssObject(el('span',label(e.label),'route-label'),start.clone().lerp(end,.5).add(new THREE.Vector3(-direction.y*95,direction.x*95,5))); caption.visible=false;
      routes.push({e,group:lineGroup,caption,middle});
    });
    // Questions take priority in the six-mascot budget.
    const shown=new Set();
    for(const route of routes) { if(route.e.gate==='waiting_for_you'&&!shown.has(route.e.from)) { frog(route.middle.clone().add(new THREE.Vector3(42,20,15)),'report',t('waitingBubble')); shown.add(route.e.from); } }
    for(const item of items) { if(needs(item.n)&&!shown.has(item.n.id)) { frog(item.root.position.clone().add(new THREE.Vector3(65,25,12)),'report',t('waitingBubble')); shown.add(item.n.id); } }
    for(const item of items) { if(['running','submitted','unverified'].includes(item.n.status)&&!needs(item.n)) frog(item.root.position.clone().add(new THREE.Vector3(60,20,12)),'walk-a',t('attemptBubble',{n:item.n.attempts}),item); }
    if(data.complete&&items.length) frog(items[items.length-1].root.position.clone().add(new THREE.Vector3(80,20,12)),'wave',t('complete'));
    resize(); selectionAppearance(); wake();
  }
  function selectionAppearance() {
    const related=new Set([chosenNode]); data.edges.forEach(e=>{if(e.from===chosenNode)related.add(e.to);if(e.to===chosenNode)related.add(e.from);});
    for(const item of items) { const active=item.n.id===chosenNode; item.orbit.visible=active; item.caption.element.classList.toggle('selected-label',active); item.caption.element.classList.toggle('dim',!!chosenNode&&!related.has(item.n.id)&&!needs(item.n));
      const opacity=chosenNode&&!related.has(item.n.id)&&!needs(item.n) ? .3 : 1;
      item.root.traverse(o=>{if(o.material)o.material.opacity=opacity*(o.parent === item.orbit && !o.userData.currentOrbit ? .3 : 1);});
      item.ring.visible=!active;
    }
    routes.forEach(route=>{route.caption.visible=!!chosenNode&&(route.e.from===chosenNode||route.e.to===chosenNode);});
  }
  function setCamera(progress) {
    const angle=progress*55*Math.PI/180, direction=new THREE.Vector3(Math.sin(angle)*.22,-Math.sin(angle)*.975,Math.cos(angle)).normalize();
    const aspect=(host.clientWidth||1)/(host.clientHeight||1);
    const fitHeight=Math.max(bounds.height,bounds.width/aspect);
    const height=fitHeight+(585/aspect-fitHeight)*progress;
    camera.left=-height*aspect/2;camera.right=height*aspect/2;camera.top=height/2;camera.bottom=-height/2;camera.updateProjectionMatrix();
    center.set(bounds.cx,bounds.cy,0);
    if(chosenNode) center.lerp(anchorPoint,progress);
    camera.position.copy(center).addScaledVector(direction,1000); camera.up.set(0,1,0); camera.lookAt(center);
    camera.updateMatrixWorld();
  }
  function select(id) {
    const item=items.find(i=>i.n.id===id);
    if(item) { anchorPoint.copy(item.root.position); }
    chosenNode=id; startTilt=tilt; targetTilt=id?1:0; transitionStart=performance.now(); selectionAppearance(); wake();
  }
  function resize() {
    const width=host.clientWidth||1,height=host.clientHeight||1, aspect=width/height;
    const fitHeight=Math.max(bounds.height,bounds.width/aspect);
    camera.left=-fitHeight*aspect/2;camera.right=fitHeight*aspect/2;camera.top=fitHeight/2;camera.bottom=-fitHeight/2;camera.updateProjectionMatrix();
    compactMap = width < 600;
    const worldPixel = width / (camera.right-camera.left);
    const captionWidth = Math.max(46,Math.min(180,300 * width / (camera.right-camera.left) * .9));
    for (const item of items) {
      item.caption.element.style.width = captionWidth + 'px';
      item.caption.element.classList.toggle('compact-label',captionWidth < 110);
      item.caption.position.y = -65 - (captionWidth < 110 ? 26 : 30) / worldPixel;
    }
    for (const f of frogs) {
      const compact = width < 600;
      f.bubble.element.classList.toggle('compact-speech',compact);
      if (!f.walkingNode) f.bubble.position.copy(f.sprite.position).add(new THREE.Vector3(compact ? 230 : 25,compact ? 230 : 88,0));
    }
    webgl.setSize(width,height);labels.setSize(width,height);setCamera(tilt);wake();
  }
  function draw(now) {
    frame=0; if(document.hidden||mode!=='flow'||mapFailed)return;
    let animating=false;
    if(tilt!==targetTilt) { const amount=reduced.matches?1:Math.min(1,(now-transitionStart)/450); const ease=amount*amount*(3-2*amount);tilt=startTilt+(targetTilt-startTilt)*ease; if(amount===1)tilt=targetTilt;setCamera(tilt);animating=amount<1;dirty=true; }
    for(const f of frogs) {
      const selectedFrog=f.walkingNode&&f.walkingNode.n.id===chosenNode;
      const worldPixel=(host.clientWidth||1)/(camera.right-camera.left);
      const size=Math.max(selectedFrog?82:70,32/worldPixel);
      f.sprite.scale.set(size,size,1);
      if(!f.walkingNode) { f.bubble.position.copy(f.sprite.position).addScaledVector(new THREE.Vector3(0,1,0).applyQuaternion(camera.quaternion),size+26/worldPixel); continue; }
      const item=f.walkingNode, active=item.n.id===chosenNode, checking=['submitted','unverified'].includes(item.n.status);
      let angle=checking ? -Math.PI/6 : item.n.attempts>1 ? Math.PI*7/6 : Math.PI/2;
      if(!reduced.matches) { angle += 0; animating=true; }
      if(!active) angle=Math.PI/2;
      const radius=active?117:64;
      f.sprite.position.copy(item.root.position).add(new THREE.Vector3(Math.cos(angle)*radius,Math.sin(angle)*radius,15));
      f.sprite.material.map=textures[checking||reduced.matches?'report':Math.floor(now/180)%2?'walk-a':'walk-b'];
      f.bubble.position.copy(f.sprite.position).addScaledVector(new THREE.Vector3(0,1,0).applyQuaternion(camera.quaternion),size+24/worldPixel);dirty=true;
    }
    if(dirty||animating) { webgl.render(scene,camera);labels.render(scene,camera);dirty=false; }
    if(animating)frame=requestAnimationFrame(draw);
  }
  function wake() { dirty=true; if(!frame&&!document.hidden&&mode==='flow'&&!mapFailed)frame=requestAnimationFrame(draw); }
  webgl.domElement.addEventListener('click',event=>{const rect=webgl.domElement.getBoundingClientRect();pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);ray.setFromCamera(pointer,camera);const hit=ray.intersectObjects(picks)[0];if(hit){if(hit.object.userData.decision)openDecision(hit.object.userData.decision);else selectNode(hit.object.userData.node);}});
  webgl.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();fallback();});
  new ResizeObserver(resize).observe(host);
  return {update,select,wake};
}
function fallback() { mapFailed = true; document.body.classList.add('list-fallback'); $('accessible').open=true; if(!view||!$('notice').hidden)return; notice('fallback'); }
try { renderer = await createMap(); if(view)renderer.update(view,selected); } catch { fallback(); }
}
