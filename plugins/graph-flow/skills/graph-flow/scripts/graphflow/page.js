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
    "ringLegend": "고리 = 시도. 실선은 썼고 점선은 아직이에요.",
    "gateLegend": "문 = 검사나 승인.",
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
    "lessons": "별자리 · 배운 것",
    "noLessons": "아직 기록된 배움이 없어요.",
    "planOrder": "전체 시간 순서는 기록에서 알 수 없어 계획 순서로 보여 드려요. 각 일의 시도는 일어난 순서예요.",
    "returns": "혜성 · 돌아온 일",
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
    "untitledFailure": "설명이 없는 확인 하나가 통과하지 못했어요.",
    "readThis": "이 파일을 읽어 주세요",
    "openFile": "파일 읽기",
    "fileFailed": "지금은 읽을 수 있는 글 파일이 아니에요. 흐름을 새로 읽고 다시 해 주세요.",
    "noFiles": "이 결정에 적힌 파일이 없어요.",
    "returnTimes": "돌아온 횟수 {n}번",
    "colourLegend": "색 = 끝남 · 진행 · 내 차례 · 대기.",
    "moonLegend": "달 = 검토.",
    "cometLegend": "혜성 = 고치러 돌아옴.",
    "goal": "목표"
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
    "ringLegend": "Ring = attempts: solid used, dashed unused.",
    "gateLegend": "Gate = check or approval.",
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
    "lessons": "Constellation · what we learned",
    "noLessons": "No lessons recorded yet.",
    "planOrder": "The overall time order is unknown, so this follows plan order. Each task’s attempts are in their recorded order.",
    "returns": "Comets · what came back",
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
    "untitledFailure": "A check without a description did not pass.",
    "readThis": "Read this",
    "openFile": "Open file",
    "fileFailed": "This file is no longer available as readable text. Refresh the flow and try again.",
    "noFiles": "No files are listed for this decision.",
    "returnTimes": "Came back {n} times",
    "colourLegend": "Colour = done · active · you · waiting.",
    "moonLegend": "Moon = review.",
    "cometLegend": "Comet = came back.",
    "goal": "Goal"
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
  const made = ['human_check', 'trajectory', 'lane3'].includes(d.record_purpose ?? d.purpose);
  return made && d.node && d.question === generated ? '' : d.question;
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

export function viewLanguage(view, browser = 'en') {
  return view ? view.language === 'ko' ? 'ko' : 'en' : browser.toLowerCase().startsWith('ko') ? 'ko' : 'en';
}
export function cometCount(node) { return (node.laps || []).filter(lap => lap === 'returned').length; }
export function failedBadgeCount(node, decisions) {
  return (decisions.find(d => d.node === node.id)?.failed || []).length;
}
export function attemptSegments(laps, maxAttempts = 3, status = '') {
  return Array.from({length:maxAttempts}, (_,i) => ({state:laps[i] || 'unused', used:!!laps[i],
    thickness:laps[i] ? 3.2 : .7, opacity:laps[i] ? 1 : status === 'passed' ? .12 : .6}));
}
export function transferPoint(route, t) {
  const u = 1 - t;
  return {x:u*u*route.start.x + 2*u*t*route.control.x + t*t*route.end.x,
          y:u*u*route.start.y + 2*u*t*route.control.y + t*t*route.end.y};
}
export function crossingCount(routes, positions) {
  const cross = (a,b,c) => (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);
  let count=0;
  routes.forEach((e,i) => routes.slice(i+1).forEach(f => {
    const a=positions[e.from],b=positions[e.to],c=positions[f.from],d=positions[f.to];
    if(a&&b&&c&&d&&new Set([e.from,e.to,f.from,f.to]).size===4&&cross(a,b,c)*cross(a,b,d)<0&&cross(c,d,a)*cross(c,d,b)<0)count++;
  }));
  return count;
}
export function layeredLayout(nodes, edges, decisions = [], sort = true) {
  const byId=new Map(nodes.map(n=>[n.id,n])), parents=new Map(nodes.map(n=>[n.id,[]]));
  edges.forEach(e=>{if(byId.has(e.from))parents.get(e.to)?.push(e.from);});
  const depths=new Map();
  function depth(id, seen = new Set()) {
    if(depths.has(id))return depths.get(id);
    if(seen.has(id))return 0;
    const next=new Set(seen);next.add(id);
    const d=Math.max(0,...parents.get(id).map(p=>depth(p,next)+1));depths.set(id,d);return d;
  }
  nodes.forEach(n=>depth(n.id));
  const layers=[];
  for(const n of nodes.filter(n=>n.kind!=='review'))(layers[depths.get(n.id)] ||= []).push(n.id);
  const workEdges=edges.filter(e=>byId.get(e.from)?.kind!=='review'&&byId.get(e.to)?.kind!=='review');
  const titleLines=n=>Math.max(1,Math.ceil(Array.from(n.title||'').length/12));
  const moonCounts=nodes.filter(n=>n.kind==='review').map(n=>nodes.filter(m=>m.kind==='review'&&m.target===n.target).length);
  const rowGap=Math.max(290,...nodes.map(n=>titleLines(n)*44+150),...moonCounts.map(n=>n*150+200));
  let positions={};
  function place() {
    positions={};layers.forEach((ids,d)=>ids.forEach((id,i)=>{positions[id]={x:d*300,y:((ids.length-1)/2-i)*rowGap,depth:d,layer:d};}));
  }
  function cost() {
    return crossingCount(workEdges,positions)*1e7+workEdges.reduce((sum,e)=>sum+Math.abs((positions[e.from]?.y||0)-(positions[e.to]?.y||0)),0);
  }
  place();
  if(sort)for(let sweep=0;sweep<6;sweep++) {
    const order=layers.map((_,d)=>d);if(sweep%2)order.reverse();
    for(const d of order) {
      const ids=layers[d];if(!ids)continue;
      const bary=id=>{const neighbours=workEdges.filter(e=>sweep%2?e.from===id:e.to===id).map(e=>positions[sweep%2?e.to:e.from]?.y).filter(y=>y!==undefined);return neighbours.length?neighbours.reduce((a,b)=>a+b,0)/neighbours.length:positions[id].y;};
      const before=cost(),old=[...ids];ids.sort((a,b)=>bary(b)-bary(a));place();
      if(cost()>before){layers[d]=old;place();}
    }
  }
  const moons=new Map();
  for(const n of nodes.filter(n=>n.kind==='review')) {
    const target=n.target||parents.get(n.id)[0];if(!moons.has(target))moons.set(target,[]);moons.get(target).push(n);
  }
  for(const [target,children]of moons) {
    const p=positions[target]||{x:0,y:0};
    children.forEach((n,i)=>{positions[n.id]={x:p.x+190,y:p.y+110+i*150,depth:depths.get(n.id),satelliteOf:target};});
  }
  const labels=Object.entries(positions).filter(([id])=>byId.get(id).kind!=='review').map(([id,p])=>{
    const lines=titleLines(byId.get(id));
    return {node:id,left:p.x-110,right:p.x+110,top:p.y-68,bottom:p.y-100-lines*44};
  });
  const gates=[],routes=[];
  const free=p=>gates.every(g=>Math.hypot(g.x-p.x,g.y-p.y)>=100)&&Object.values(positions).every(n=>Math.hypot(n.x-p.x,n.y-p.y)>=88)&&labels.every(l=>p.x<l.left-28||p.x>l.right+28||p.y>l.top+28||p.y<l.bottom-28);
  for(const e of workEdges) {
    const a=positions[e.from],b=positions[e.to];if(!a||!b)continue;
    const route={...e,gateState:decisions.some(d=>d.node===e.from)?'waiting_for_you':e.gate,start:{x:a.x+66,y:a.y},end:{x:b.x-66,y:b.y}};
    let found=false;
    for(let bend=0;!found;bend++) {
      const offset=bend===0?20:Math.ceil(bend/2)*44*(bend%2?1:-1);
      route.control={x:(a.x+b.x)/2,y:(a.y+b.y)/2+offset};
      for(const t of [.5,.35,.65,.23,.77]){const p=transferPoint(route,t);if(free(p)){route.gate={...p,t};gates.push(p);found=true;break;}}
    }
    routes.push(route);
  }
  const nodeGates=[];
  for(const n of nodes) {
    if(n.kind==='review'||n.kind==='decision'||routes.some(r=>r.from===n.id)||(!cometCount(n)&&!decisions.some(d=>d.node===n.id)))continue;
    const p=positions[n.id];let gate={x:p.x+120,y:p.y};
    while(!free(gate))gate.y+=75;
    const state=decisions.some(d=>d.node===n.id)?'waiting_for_you':n.status==='passed'?'open':'returned';
    nodeGates.push({...gate,node:n.id,state});gates.push(gate);
  }
  const goal={x:Math.max(0,...Object.values(positions).map(p=>p.x))+270,y:0};
  const terminals=nodes.filter(n=>n.kind!=='review'&&!workEdges.some(e=>e.from===n.id)).map(n=>n.id);
  const points=[goal,...Object.values(positions),...routes.flatMap(r=>[r.control,r.gate]),...nodeGates];
  const minX=Math.min(0,...points.map(p=>p.x))-125,maxX=Math.max(...points.map(p=>p.x))+125,minY=Math.min(0,...points.map(p=>p.y),...labels.map(l=>l.bottom))-70,maxY=Math.max(0,...points.map(p=>p.y))+200;
  const order=layers.flatMap(ids=>ids.flatMap(id=>[id,...(moons.get(id)||[]).map(n=>n.id)]));
  return {positions,layers,order,labels,routes,nodeGates,goal,terminals,bounds:{cx:(minX+maxX)/2,cy:(minY+maxY)/2,width:maxX-minX,height:maxY-minY}};
}

if (typeof document !== 'undefined') {
let language = viewLanguage(null, navigator.language);
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
function translate() {
  document.documentElement.lang = language;
  document.querySelectorAll('[data-i18n]').forEach(e => { e.textContent = t(e.dataset.i18n); });
  document.querySelector('nav').setAttribute('aria-label', t('flow'));
  $('map').setAttribute('aria-label', t('flow'));
}
translate();
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
  for (const key of ['done','doing','needs_you','waiting','returned']) { const item = el('li'); item.append(el('span', undefined, 'dot ' + key), el('span', key === 'returned' ? t('returnTimes', {n:view.counts.returns_total ?? 0}) : `${t(key)} ${view.counts[key]}`)); list.append(item); }
  c.append(list); return c;
}
function failedBlock(parent, d) {
  if (!d.failed?.length) return;
  const failed = card(t('failed')); failed.classList.add('failed');
  textList(failed, d.failed.map(text => text === STRINGS.en.untitledFailure ? t('untitledFailure') : text)); parent.append(failed);
}
function decisionCard(d) {
  const c = card(t('yourTurn'), null, true); decisionHeading(c, d, 'h3'); failedBlock(c, d); if (d.context.why) c.append(el('p', d.context.why));
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
  p.append(el('p', t('yourTurn'), 'eyebrow'), el('h2',t(view.decisions.length ? 'needsYou' : 'counts')));
  view.decisions.forEach(d => p.append(decisionCard(d)));
  if (!view.decisions.length) p.append(el('p',t('nothing')));
  p.append(countCard());
  const legend=el('div',undefined,'legend');
  for(const key of ['colourLegend','ringLegend','moonLegend','cometLegend','gateLegend']) {
    const line=el('p',t(key));
    if(key==='colourLegend')for(const state of ['done','doing','needs_you','waiting'])line.append(el('span',undefined,'dot '+state));
    legend.append(line);
  }
  p.append(legend);
  if(node) {
    p.append(el('h2',title(node)),card(t('now'),`${status(node)}. ${attempts(node)}. ${node.summary}`,true));
    const reasons=card(t('whyReturned'),null,true);textList(reasons,node.returned_reasons.flat(),node.returned_reasons.length?'noReason':'noReturns');p.append(reasons);
    p.append(handoffsCard('received',node.inputs,'from'),handoffsCard('outputs',node.outputs,'to'),button(t('flow'),wholeFlow,'primary'));
  }
}
function accessible() {
  clear($('node-list')); clear($('edge-list')); clear($('decision-list'));
  const order = layeredLayout(view.nodes,view.edges,view.decisions).order;
  [...view.nodes].sort((a,b)=>order.indexOf(a.id)-order.indexOf(b.id)).forEach(n => { const item = el('li', undefined, 'card'); item.append(button(title(n), () => selectNode(n.id)), el('p', status(n)), el('p', attempts(n), 'muted'), el('p', n.summary)); if (n.returned_reasons.length) textList(item, n.returned_reasons.flat(), 'noReason'); $('node-list').append(item); });
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
  const files = card(t('readThis'), null, true), fileChoices = el('div', undefined, 'file-choices'), reader = el('pre', undefined, 'file-reader');
  reader.hidden = true; reader.tabIndex = 0; reader.setAttribute('aria-label',t('readThis'));
  const fileStatus = el('p'); fileStatus.setAttribute('role','status');
  files.append(fileChoices, fileStatus, reader); right.append(files);
  let fileFingerprint = '', fileRequest = 0;
  const updateFiles = decision => {
    const signature = JSON.stringify(decision.files || []); if (signature === fileFingerprint) return;
    fileFingerprint = signature; fileRequest++; clear(fileChoices); reader.hidden = true;
    fileStatus.textContent = decision.files?.length ? '' : t('noFiles');
    for (const file of decision.files || []) {
      const entry = el('div'); entry.append(button(file.name, async () => {
        if (!current()) return;
        const request = ++fileRequest; fileStatus.textContent = t('loading'); reader.hidden = true;
        try {
          const text = await api(query('/api/file', {decision:session.target.id,path:file.path}, session.target), null, true);
          if (!current() || request !== fileRequest) return;
          reader.textContent = text; reader.hidden = false; fileStatus.textContent = ''; reader.setAttribute('aria-label',file.name);
          decisionController.openDetails(); updateActions();
        } catch { if (current() && request === fileRequest) fileStatus.textContent = t('fileFailed'); }
      }), el('small',file.path,'file-path')); fileChoices.append(entry);
    }
  };
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
    updateFiles(decision);
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
    laps.forEach((lap, i) => { const item = el('li'); item.append(el('span', lap === 'returned' ? '' : n.kind === 'review' ? '☾' : n.kind === 'decision' ? '▣' : '', 'mini-planet ' + lap), button(title(n), () => selectNode(n.id)), el('p', lap === 'returned' ? t('returned') : lap === 'passed' ? t('passed') : status(n), 'muted')); if (n.laps.length) item.append(el('small', t('attempt', {n:i + 1, max:n.max_attempts}))); strip.append(item); });
  }); box.append(strip);
  const grid = el('div', undefined, 'history-grid'); const returns = el('div'); returns.append(el('h3', t('returns')));
  view.nodes.filter(n => n.returned_reasons.length).forEach(n => { const c = card(title(n), null, true); textList(c, n.returned_reasons.flat(), 'noReason'); returns.append(c); });
  if (!view.nodes.some(n => n.returned_reasons.length)) returns.append(el('p', t('noReturns')));
  const lessons = el('div', undefined, 'constellation'); lessons.append(el('h3', t('lessons'))); view.lessons.forEach(l => { const lesson=card(l.node_title ? otherTitle(l.node_title) : t('lessons'), l.text); lesson.classList.add('lesson'); lessons.append(lesson); }); if (!view.lessons.length) lessons.append(el('p', t('noLessons')));
  const counts = el('div'); counts.append(countCard(), button(t('flow'), wholeFlow, 'primary')); grid.append(returns, lessons, counts); box.append(grid);
}
function applyView(next) {
  if (decisionController.session?.busy) return;
  closeInvalidDecision(chosen, next.decisions);
  const nextFingerprint = JSON.stringify(next); if (nextFingerprint === fingerprint) return;
  language = viewLanguage(next, navigator.language); translate();
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
function resetView() { language = viewLanguage(null, navigator.language); translate(); closeInvalidDecision(chosen, []); view = null; selected = null; fingerprint = ''; ['node-list','edge-list','decision-list','panel'].forEach(id => clear($(id))); if (renderer) renderer.update({nodes:[],edges:[],decisions:[],complete:false}, null); $('flow').hidden = true; $('history').hidden = true; $('decision').hidden = true; $('subtitle').textContent = ''; }
function schedule() { clearTimeout(timer); if (!document.hidden) timer = setTimeout(refresh, 2000); }
$('flow-tab').addEventListener('click', () => { if (view) wholeFlow(); });
$('history-tab').addEventListener('click', () => { if (view) historyView(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !e.isComposing && view) wholeFlow(); });
document.addEventListener('visibilitychange', () => { clearTimeout(timer); if (renderer) renderer.wake(); if (!document.hidden) refresh(true); });
reduced.addEventListener('change', () => { if (renderer) renderer.wake(); });
notice('loading'); refresh();

async function createMap() {
  const THREE = await import('/static/vendor/three.module.min.js');
  const {CSS2DRenderer, CSS2DObject} = await import('/static/vendor/CSS2DRenderer.js');
  const host = el('div', undefined, 'map-scene'); $('map').append(host);
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
    const entry={sprite,bubble,walkingNode,pose,base:position.clone()};frogs.push(entry);return entry;
  }
  function comet(parent,x,y,scale=1) {
    const object=new THREE.Group();object.position.set(x,y,20);object.scale.setScalar(scale);parent.add(object);
    const tail=new THREE.Shape();tail.moveTo(-5,3);tail.lineTo(-38,19);tail.lineTo(-21,-4);tail.lineTo(-5,-6);tail.closePath();mesh(new THREE.ShapeGeometry(tail),'#ff9479',object);
    tube([new THREE.Vector3(-29,11,1),new THREE.Vector3(-10,2,1)],'#ffc2a4',1.5,object);
    disk(6,ink,0,0,2,object);disk(3.8,'#fff0d6',0,0,3,object);return object;
  }
  function dashedRing(radius,from,length,colour,parent,thickness=.8) {
    for(let i=0;i<9;i++)arc(radius,from+length*i/9,length/16,colour,parent,thickness);
  }
  function dispose() {
    group.traverse(object => { if (object.isCSS2DObject) object.element.remove(); if (object.geometry) object.geometry.dispose(); if (object.material) { if (object.material.map?.isCanvasTexture) object.material.map.dispose(); object.material.dispose(); } });
    scene.remove(group); group = new THREE.Group(); scene.add(group); items = []; routes = []; frogs = []; picks = [];
  }
  function gateControl(gate,nodeId,state,x) {
    const n=data.nodes.find(n=>n.id===nodeId),decision=data.decisions.find(d=>d.node===nodeId);
    const hit=button('',()=>decision?openDecision(decision.id):selectNode(nodeId),'gate-hit');
    const description=`${title(n)}. ${t(state==='open'?'passed':state==='returned'?'returned':state==='waiting_for_you'?'awaiting':'waiting')}`;
    hit.title=description;hit.setAttribute('aria-label',description);hit.dataset.flowOrder=String(x);
    const count=state==='waiting_for_you'?failedBadgeCount(n,data.decisions):0;
    if(count)hit.append(el('span',String(count),'failed-badge'));
    cssObject(hit,new THREE.Vector3(0,5,25),gate);
  }
  function update(next, id) {
    data=next;chosenNode=id;dispose();const layout=layeredLayout(data.nodes,data.edges,data.decisions);bounds=layout.bounds;
    const positions=new Map(Object.entries(layout.positions).map(([key,p])=>[key,new THREE.Vector3(p.x,p.y,0)]));
    for(let i=0;i<65;i++) { const x=bounds.cx+Math.sin(i*9.71)*bounds.width*.5,y=bounds.cy+Math.cos(i*7.31)*bounds.height*.47;const star=disk(i%4?.7:1.3,'#756887',x,y,-40);star.material.opacity=.45; }
    const goal=new THREE.Group();goal.position.set(layout.goal.x,layout.goal.y,0);group.add(goal);
    const shape=new THREE.Shape();
    for(let i=0;i<10;i++){const a=Math.PI/2+i*Math.PI/5,r=i%2?16:36;const x=Math.cos(a)*r,y=Math.sin(a)*r;i?shape.lineTo(x,y):shape.moveTo(x,y);}shape.closePath();
    const shadow=mesh(new THREE.ShapeGeometry(shape),ink,goal);shadow.scale.setScalar(1.13);shadow.position.y=-4;
    mesh(new THREE.ShapeGeometry(shape),data.complete?'#ffd166':'#6a5a8e',goal).position.z=2;
    cssObject(el('strong',t('goal'),'goal-label'),new THREE.Vector3(0,-65,0),goal);
    for(const id of layout.terminals){const a=positions.get(id),b=layout.goal;for(let i=0;i<32;i++){const t=i/32,p=disk(1.1,'#6a5a8e',a.x+65+(b.x-a.x-95)*t,a.y*(1-t),-20);p.material.opacity=.35;}}
    for(const id of layout.order){
      const n=data.nodes.find(n=>n.id===id);
      const pos=positions.get(n.id),root=new THREE.Group();root.position.copy(pos);group.add(root);
      const waiting=data.decisions.some(d=>d.node===n.id),active=['running','submitted','unverified'].includes(n.status);
      const colour=waiting?colours.waiting_for_you:n.status==='passed'||n.answered?colours.passed:active?colours.current:'#3a2e5a';
      const radius=n.kind==='review'?17:n.kind==='decision'?20:38,ringRadius=radius+15;
      const outline=disk(radius+3,colour==='#3a2e5a'?'#6a5a8e':ink,0,-3,0,root);
      const body=disk(radius,colour,0,0,4,root);body.userData.node=n.id;picks.push(body);
      if(n.kind==='decision'){
        const station=mesh(new THREE.BoxGeometry(25,22,5),ink,root);station.position.z=6;
        disk(7,colour,0,0,11,root);
        for(const x of [-30,30]){const panel=mesh(new THREE.PlaneGeometry(18,27),'#88adb5',root);panel.position.set(x,0,5);tube([new THREE.Vector3(x,-12,7),new THREE.Vector3(x,12,7)],ink,1.4,root);}
        tube([new THREE.Vector3(0,12,7),new THREE.Vector3(0,35,7)],ink,2,root);disk(4,colour,0,35,8,root);
      }else{
        const shade=disk(radius*.86,ink,4,-5,5,root);shade.material.opacity=.12;
        disk(radius*.83,colour,-4,4,6,root);
        const shine=disk(radius*.23,'#fff6ea',-radius*.32,radius*.34,7,root);shine.scale.y=.65;
        if(n.status==='passed')tube([new THREE.Vector3(-11,0,9),new THREE.Vector3(-3,-8,9),new THREE.Vector3(13,11,9)],ink,2.8,root);
      }
      let halo=null;if(waiting){halo=disk(ringRadius+9,colours.waiting_for_you,0,0,-2,root);halo.material.opacity=.12;}
      if(n.kind==='review'){
        const target=positions.get(n.target);if(target){const line=tube([target.clone(),pos.clone()],'#6a5a8e',.7);line.position.z=-15;line.material.opacity=.4;}
      }
      const ring=new THREE.Group();root.add(ring);
      if(n.kind==='work')attemptSegments(n.laps,n.max_attempts,n.status).forEach((segment,a)=>{
        const from=a*Math.PI*2/n.max_attempts+.14,length=Math.PI*2/n.max_attempts-.28;
        if(segment.used){const part=arc(ringRadius,from,length,colours[segment.state]||colours.current,ring,segment.thickness);part.material.opacity=segment.opacity;}
        else{const unused=new THREE.Group();ring.add(unused);dashedRing(ringRadius,from,length,'#6a5a8e',unused,segment.thickness);unused.children.forEach(p=>p.material.opacity=segment.opacity);}
      });
      const count=cometCount(n);if(count){comet(root,-radius-5,radius+20,.65);if(count>1)cssObject(el('span',String(count),'comet-count'),new THREE.Vector3(-radius-25,radius+22,22),root);}
      const labelButton=button('',()=>selectNode(n.id),'planet-label');const captionText=el('span',undefined,'node-caption');captionText.append(el('strong',title(n)),el('small',status(n)));labelButton.append(captionText);
      const description=`${title(n)}. ${status(n)}. ${attempts(n)}. ${t('returnTimes',{n:count})}`;
      labelButton.setAttribute('aria-label',description);labelButton.title=description;
      if(n.kind==='review')labelButton.classList.add('moon-label');
      const caption=cssObject(labelButton,new THREE.Vector3(0,0,20),root);
      caption.renderOrder=30;labelButton.dataset.flowOrder=String(pos.x);
      const orbit=new THREE.Group();root.add(orbit);orbit.visible=false;
      const currentOrbit=arc(125,0,Math.PI*2,colours.current,orbit,.8);currentOrbit.userData.currentOrbit=true;
      for(let i=0;i<count;i++){const old=arc(125+i*8,0,Math.PI*2,colours.returned,orbit,.7);old.position.z=-12-i*5;old.material.opacity=.3;}
      const stations=[];for(const [i,key]of ['make','check','fix'].entries()){const a=Math.PI/2-i*2*Math.PI/3,p=new THREE.Vector3(Math.cos(a)*125,Math.sin(a)*125,8);disk(5.5,'#fff6ea',p.x,p.y,p.z,orbit);stations.push(cssObject(el('span',t(key),'station'),p.clone().multiplyScalar(1.4),orbit));}
      items.push({n,root,ring,ringRadius,orbit,stations,caption,planet:body,outline,halo,radius});
    }
    for(const route of layout.routes){
      const e={...route,gate:route.gateState},a=positions.get(e.from),b=positions.get(e.to),lineGroup=new THREE.Group();group.add(lineGroup);
      const point=t=>{const p=transferPoint(route,t);return new THREE.Vector3(p.x,p.y,-5);};
      const count=Math.max(12,Math.floor(a.distanceTo(b)/10));for(let i=0;i<=count;i++){const p=point(i/count);disk(1.6,colours[e.gate]||colours.closed,p.x,p.y,p.z,lineGroup);}
      const middle=new THREE.Vector3(route.gate.x,route.gate.y,10),gate=new THREE.Group();gate.position.copy(middle);lineGroup.add(gate);
      const points=[new THREE.Vector3(-9,-7,3),new THREE.Vector3(-9,6,3),new THREE.Vector3(-7,13,3),new THREE.Vector3(0,16,3),new THREE.Vector3(7,13,3),new THREE.Vector3(9,6,3),new THREE.Vector3(9,-7,3)];
      const door=mesh(new THREE.PlaneGeometry(17,20),ink,gate);door.position.set(0,3,1);tube(points,ink,4.6,gate);const arch=tube(points,colours[e.gate]||colours.closed,2.6,gate);arch.position.z=4;
      if(e.gate==='waiting_for_you')gate.scale.setScalar(1.2);
      gateControl(gate,e.from,e.gate,middle.x);
      const socket=point(1);socket.z=18;if(e.delivered){disk(8,ink,socket.x,socket.y,socket.z,lineGroup);disk(5.5,'#fff6ea',socket.x,socket.y,socket.z+1,lineGroup);}else for(let i=0;i<8;i++){const a=i*Math.PI/4;disk(1.4,'#6a5a8e',socket.x+Math.cos(a)*6,socket.y+Math.sin(a)*6,socket.z,lineGroup);}
      routes.push({e,group:lineGroup,middle});
    }
    for(const entry of layout.nodeGates){
      const middle=new THREE.Vector3(entry.x,entry.y,10),gate=new THREE.Group();gate.position.copy(middle);group.add(gate);
      const points=[new THREE.Vector3(-9,-7,3),new THREE.Vector3(-9,6,3),new THREE.Vector3(-7,13,3),new THREE.Vector3(0,16,3),new THREE.Vector3(7,13,3),new THREE.Vector3(9,6,3),new THREE.Vector3(9,-7,3)];
      const door=mesh(new THREE.PlaneGeometry(17,20),ink,gate);door.position.set(0,3,1);tube(points,ink,4.6,gate);const arch=tube(points,colours[entry.state],2.6,gate);arch.position.z=4;
      if(entry.state==='waiting_for_you')gate.scale.setScalar(1.2);
      gateControl(gate,entry.node,entry.state,middle.x);
      routes.push({e:{from:entry.node,to:entry.node,gate:entry.state},group:gate,middle,terminal:true});
    }
    const shown=new Set();for(const route of routes)if(route.e.gate==='waiting_for_you'&&!shown.has(route.e.from)){frog(route.middle.clone().add(new THREE.Vector3(36,15,15)),'report',t('waitingBubble'));shown.add(route.e.from);}
    for(const item of items)if(needs(item.n)&&!shown.has(item.n.id)){frog(item.root.position.clone().add(new THREE.Vector3(65,25,12)),'report',t('waitingBubble'));shown.add(item.n.id);}
    for(const item of items)if(item.n.kind==='work'&&['running','submitted','unverified'].includes(item.n.status)&&!needs(item.n))frog(item.root.position.clone().add(new THREE.Vector3(60,20,12)),'walk-a',t('attemptBubble',{n:item.n.attempts}),item);
    if(data.complete){const wave=frog(new THREE.Vector3(layout.goal.x+55,layout.goal.y+25,12),'wave',t('complete'));if(wave)wave.bubble.visible=false;}
    if(chosenNode){const item=items.find(i=>i.n.id===chosenNode);if(item)anchorPoint.copy(item.root.position);}
    resize();selectionAppearance();wake();
  }
  function selectionAppearance() {
    const selectedNode=data.nodes.find(n=>n.id===chosenNode);
    const related=new Set([chosenNode,selectedNode?.target]); data.nodes.filter(n=>n.target===chosenNode).forEach(n=>related.add(n.id)); data.edges.forEach(e=>{if(e.from===chosenNode)related.add(e.to);if(e.to===chosenNode)related.add(e.from);});
    for(const item of items) { const active=item.n.id===chosenNode; item.orbit.visible=active&&item.n.kind==='work'; item.caption.element.classList.toggle('selected-label',active); item.caption.element.classList.toggle('show-moon',related.has(item.n.id)&&!!chosenNode); item.caption.element.classList.toggle('dim',!!chosenNode&&!related.has(item.n.id)&&!needs(item.n));
      const opacity=chosenNode&&!related.has(item.n.id)&&!needs(item.n) ? .3 : 1;
      item.root.traverse(o=>{if(o.material){o.userData.baseOpacity ??= o.material.opacity;o.material.opacity=opacity*o.userData.baseOpacity;}});
      item.ring.visible=true;
    }
  }
  function setCamera(progress) {
    const angle=progress*55*Math.PI/180, direction=new THREE.Vector3(Math.sin(angle)*.22,-Math.sin(angle)*.975,Math.cos(angle)).normalize();
    const aspect=(host.clientWidth||1)/(host.clientHeight||1);
    const fitHeight=Math.max(bounds.height,bounds.width/aspect);
    const satelliteExtent=Math.max(0,...items.filter(i=>i.n.target===chosenNode).map(i=>i.root.position.distanceTo(anchorPoint)));
    const selectedHeight=Math.max(430,600/aspect,satelliteExtent*2+200);
    const height=fitHeight+(selectedHeight-fitHeight)*progress;
    camera.left=-height*aspect/2;camera.right=height*aspect/2;camera.top=height/2;camera.bottom=-height/2;camera.updateProjectionMatrix();
    center.set(bounds.cx,bounds.cy,0);
    if(chosenNode) center.lerp(anchorPoint,progress);
    camera.position.copy(center).addScaledVector(direction,1000); camera.up.set(0,1,0); camera.lookAt(center);
    camera.updateMatrixWorld();
    const worldPixel=(host.clientWidth||1)/(camera.right-camera.left);
    for(const item of items)item.caption.element.style.setProperty('--title-offset',(item.ringRadius*worldPixel+14)+'px');
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
    const captionWidth = Math.max(76,Math.min(210,240*worldPixel));
    for (const item of items) {
      item.caption.element.style.width = captionWidth + 'px';
      item.caption.element.classList.toggle('compact-label',compactMap);
      item.caption.element.style.setProperty('--title-offset', (item.ringRadius*worldPixel+22)+'px');
      if(item.n.kind==='review')item.caption.element.style.width='44px';
    }
    for (const f of frogs) {
      const compact = width < 600;
      f.bubble.element.classList.toggle('compact-speech',compact);
      if (!f.walkingNode) f.bubble.position.copy(f.sprite.position).add(new THREE.Vector3(compact ? 230 : 25,compact ? 230 : 88,0));
    }
    webgl.setSize(width,height);labels.setSize(width,height);setCamera(tilt);selectionAppearance();wake();
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
      if(!reduced.matches) { angle += now/2600; animating=true; }
      if(!active) angle=Math.PI*1.05+(reduced.matches?.4:(1+Math.sin(now/2600))*.4);
      f.bubble.visible=false;
      const radius=active?125:item.ringRadius+5;
      f.sprite.position.copy(item.root.position).add(new THREE.Vector3(Math.cos(angle)*radius,Math.sin(angle)*radius,15));
      f.sprite.material.map=textures[checking||reduced.matches?'report':Math.floor(now/180)%2?'walk-a':'walk-b'];
      f.bubble.position.copy(f.sprite.position).addScaledVector(new THREE.Vector3(0,1,0).applyQuaternion(camera.quaternion),size+24/worldPixel);dirty=true;
    }
    if(dirty||animating) { webgl.render(scene,camera);labels.render(scene,camera);
      const ordered=[...labels.domElement.children].sort((a,b)=>Number(a.dataset.flowOrder||0)-Number(b.dataset.flowOrder||0));
      if(ordered.some((e,i)=>labels.domElement.children[i]!==e))ordered.forEach(e=>labels.domElement.append(e));
      dirty=false; }
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
