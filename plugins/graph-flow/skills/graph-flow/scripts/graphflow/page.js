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
    "cometLegend": "고치러 돌아온 횟수",
    "goal": "목표",
    "work": "작업",
    "review": "검토",
    "decision": "결정",
    "handsOver": "넘겨줌",
    "reviews": "검토함",
    "waitsForDecision": "결정을 기다림",
    "towardGoal": "목표로",
    "fit": "맞추기",
    "zoomIn": "크게 보기",
    "zoomOut": "작게 보기",
    "mapHelp": "끌어서 이동 · + − 확대 · 0 맞추기",
    "firstPass": "한 번에",
    "finishedAttempts": "{n}번 만에",
    "passes": "통과 →",
    "fails": "미통과 ↓",
    "pastAttempt": "{n}번째 시도",
    "loopDescription": "만들기에서 검사로, 통과하면 다음 일로 넘겨요. 통과하지 못하면 고쳐서 다시 만들어요.",
    "pipPassed": "통과한 시도",
    "pipReturned": "돌아온 시도",
    "pipCurrent": "지금 시도",
    "pipUnused": "남은 시도",
    "lineLegend": "선 위의 글은 넘기는 것이에요",
    "unusedAttempts": "시도 0번 · 최대 {max}번"
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
    "cometLegend": "Times it came back",
    "goal": "Goal",
    "work": "Work",
    "review": "Review",
    "decision": "Decision",
    "handsOver": "hands over",
    "reviews": "reviews",
    "waitsForDecision": "waits for a decision",
    "towardGoal": "toward the goal",
    "fit": "Fit",
    "zoomIn": "Zoom in",
    "zoomOut": "Zoom out",
    "mapHelp": "Drag to pan · + − zoom · 0 fit",
    "firstPass": "First attempt",
    "finishedAttempts": "In {n} attempts",
    "passes": "passes →",
    "fails": "fails ↓",
    "pastAttempt": "Attempt {n}",
    "loopDescription": "Make, then check. Passes lead to the next handoff. Failed checks lead to fix, then make again.",
    "pipPassed": "Passed attempt",
    "pipReturned": "Returned attempt",
    "pipCurrent": "Current attempt",
    "pipUnused": "Attempt left",
    "lineLegend": "Text on a line is what gets handed over",
    "unusedAttempts": "0 attempts · up to {max}"
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
    session.kind === 'authorization' || session.purpose === 'hold' || session.failed?.length) || session.detailsOpened || (!(session.purpose === 'hold' || session.failed?.length) && session.fileOpened));
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
    get requiresDetails() { return !!session && !canApprove({...session, detailsOpened:false, fileOpened:false}); },
    open(id) {
      if (session?.busy) return null;
      const decision = view?.decisions.find(d => d.id === id);
      if (!decision || !chosen) return null;
      if (!session || !sameRun(session.target, chosen) || session.target.id !== id) {
        session = {target:Object.freeze({project:chosen.project, run:chosen.run, id}), draft:'', detailsOpened:false, fileOpened:false, busy:false};
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
    openFile() { if (current()) session.fileOpened = true; },
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
export const MIN_FIT_SCALE = .5;
export function attemptPips(laps = [], maxAttempts = 3, status = '') {
  return Array.from({length:maxAttempts}, (_, i) => ({state: laps[i] === 'current' && ['awaiting_approval','held'].includes(status) ? 'waiting_for_you' : laps[i] || 'unused'}));
}
export function innerLoopState(status, attempts = 0) {
  if (['awaiting_approval','held','waiting_for_you'].includes(status)) return 'report';
  if (status === 'passed') return 'exit';
  if (['submitted','unverified'].includes(status)) return 'check';
  if (status === 'running') return attempts > 1 ? 'fix' : 'make';
  return null;
}
export function edgeRelationLabel(edge, language = 'en') {
  const words = STRINGS[language];
  if (edge.relation === 'toward_goal') return words.towardGoal;
  if (edge.relation === 'reviews') return words.reviews;
  if (edge.relation === 'waits_for_decision') return words.waitsForDecision;
  return words.handsOver + (edge.label ? ': ' + edge.label : '');
}
// The short text drawn on a line. A named handoff shows only its name; the full relation stays in the accessible label.
export function edgeChipText(edge, language = 'en') {
  if (edge.relation === 'toward_goal') return '';
  if ((edge.relation || 'hands_over') === 'hands_over' && edge.label) return edge.label;
  return edgeRelationLabel(edge, language);
}
const textWidth = (text, wide, narrow) => Array.from(text || '').reduce((sum, c) => sum + (c.charCodeAt(0) > 0x2e80 ? wide : narrow), 0);
export function fitScale(bounds, width, height, mobile = false) {
  const available = mobile ? height / bounds.height : Math.min(width / bounds.width, height / bounds.height);
  return Math.max(MIN_FIT_SCALE, Math.min(1, available));
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
export function layeredLayout(nodes, edges, decisions = [], sort = true, options = {}) {
  const width=232, gap=104, rowGap=64, left=24, top=72, byId=new Map(nodes.map(n=>[n.id,n]));
  // A review's arrow points back to its target; its dependency still points forward.
  const dependencies=edges.filter(e=>e.relation!=='reviews'&&byId.has(e.from)&&byId.has(e.to));
  const parents=new Map(nodes.map(n=>[n.id,dependencies.filter(e=>e.to===n.id).map(e=>e.from)]));
  nodes.filter(n=>n.kind==='review'&&byId.has(n.target)).forEach(n=>parents.set(n.id,[n.target]));
  const depths=new Map();
  const depth=(id,seen=new Set())=>{
    if(depths.has(id))return depths.get(id);
    if(seen.has(id))return 0;
    const next=new Set(seen);next.add(id);
    const d=Math.max(0,...(parents.get(id)||[]).map(p=>depth(p,next)+1));depths.set(id,d);return d;
  };
  const layers=[];
  nodes.forEach(n=>(layers[depth(n.id)] ||= []).push(n.id));
  const height=n=>{
    const lines=Math.max(1,Math.ceil(textWidth(n.title,17,9.5)/158));
    const base=92+lines*24;
    const expanded=options.expanded===n.id ? 210+(n.returned_reasons||[]).reduce((sum,rs)=>sum+30+Math.max(1,Math.ceil(textWidth(rs.join(' · '),13,7)/170))*21,0) : 0;
    return Math.max(base+expanded,options.heights?.[n.id]||0);
  };
  let positions={};
  const place=()=>{
    positions={}; layers.forEach((ids,d)=>{let y=top;ids.forEach(id=>{const h=height(byId.get(id));if(byId.get(id).kind==='review'&&positions[byId.get(id).target])y=Math.max(y,positions[byId.get(id).target].y);positions[id]={x:left+d*(width+gap),y,width,height:h,depth:d,layer:d};y+=h+rowGap;});});
  };
  const cost=()=>crossingCount(dependencies,positions)*1e7+dependencies.reduce((s,e)=>s+Math.abs(positions[e.from].y-positions[e.to].y),0);
  place();
  if(sort)for(let sweep=0;sweep<8;sweep++) {
    const order=layers.map((_,d)=>d);if(sweep%2)order.reverse();
    for(const d of order) {
      const ids=layers[d];if(!ids)continue;
      const bary=id=>{
        const n=byId.get(id);
        const neighbours=n.kind==='review'&&positions[n.target]?[positions[n.target].y]:dependencies.filter(e=>sweep%2?e.from===id:e.to===id).map(e=>positions[sweep%2?e.to:e.from].y);
        return neighbours.length?neighbours.reduce((a,b)=>a+b,0)/neighbours.length:positions[id].y;
      };
      const before=cost(),old=[...ids];ids.sort((a,b)=>bary(a)-bary(b));place();
      if(cost()>before){layers[d]=old;place();}
    }
  }
  const last=Math.max(0,...depths.values()), goal={x:left+(last+1)*(width+gap),y:top,width:148,height:116,layer:last+1};
  const terminals=nodes.filter(n=>!dependencies.some(e=>e.from===n.id)).map(n=>n.id);
  const allEdges=[...edges,...terminals.map(id=>({from:id,to:'__goal',label:'',relation:'toward_goal',gate:byId.get(id).status==='passed'?'open':'closed'}))];
  // Edges that hand the same thing from the same node share one label; only the lines fork.
  const chips=[],routes=[],groups=new Map(),anchor=(id,p)=>p.y+(options.expanded===id?52:p.height/2);
  for(const [index,e] of allEdges.entries()) {
    const a=positions[e.from],b=e.to==='__goal'?goal:positions[e.to];if(!a||!b)continue;
    const reverse=a.x>b.x,text=edgeChipText(e,options.language||'en');
    const waiting=decisions.find(d=>d.node===e.from)||(e.relation==='waits_for_decision'?decisions.find(d=>d.node===e.to):null);
    const route={...e,index,text,reverse,start:{x:reverse?a.x:a.x+a.width,y:anchor(e.from,a)},end:{x:reverse?b.x+b.width:b.x,y:anchor(e.to,b)},chip:null,gateState:waiting?'waiting_for_you':e.gate||'closed',decision:waiting?.id,skip:Math.abs(a.layer-b.layer)>1,channel:20+(index%4)*10};
    routes.push(route);if(!text)continue;
    const key=JSON.stringify([e.from,text,reverse,route.gateState,route.decision||'']);
    if(!groups.has(key))groups.set(key,{column:reverse?b.layer:a.layer,text,routes:[]});
    groups.get(key).routes.push(route);
  }
  for(const group of groups.values()) {
    const w=Math.min(gap-12,Math.max(34,Math.ceil(textWidth(group.text,12,6.8))+14)),lines=Math.ceil(textWidth(group.text,12,6.8)/(gap-26));
    const middle=group.routes.reduce((sum,r)=>sum+(r.start.y+r.end.y)/2,0)/group.routes.length;
    const chip={x:left+group.column*(width+gap)+width+(gap-w)/2,y:Math.max(8,middle-(lines*17+8)/2),width:w,height:lines*17+8,first:group.routes[0].index};
    while(chips.some(c=>chip.x<c.x+c.width+6&&chip.x+chip.width+6>c.x&&chip.y<c.y+c.height+8&&chip.y+chip.height+8>c.y))chip.y+=12;
    chips.push(chip);group.routes.forEach(r=>{r.chip=chip;});
  }
  const cardRects=Object.entries(positions).map(([id,p])=>({id,...p}));
  const bounds={width:goal.x+goal.width+left,height:Math.max(360,goal.y+goal.height+80,...cardRects.map(p=>p.y+p.height+76),...chips.map(c=>c.y+c.height+40))};
  return {positions,layers,order:layers.flat(),routes,chips,cardRects,goal,terminals,bounds};
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
  document.querySelectorAll('[data-i18n-label]').forEach(e=>e.setAttribute('aria-label',t(e.dataset.i18nLabel)));
}
translate();
let chosen = null, projects = [], view = null, fingerprint = '', mode = 'flow', selected = null;
let queuedRefresh = false;
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
function relationText(edge) { return edgeRelationLabel({...edge,label:edge.label?label(edge.label):''},language); }
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
function attempts(node) { return t(node.attempts?'attempt':'unusedAttempts', {n:node.attempts||0, max:node.max_attempts||3}); }
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
  const legend=el('div',undefined,'legend');legend.append(el('p',t('legend'),'eyebrow'));
  const row=(...items)=>{const line=el('p');items.forEach(([mark,text])=>{const item=el('span',undefined,'legend-item');if(mark)item.append(mark);item.append(el('span',text));line.append(item);});legend.append(line);};
  const pip=state=>el('span',undefined,'pip '+state),dot=key=>el('span',undefined,'dot '+key);
  row(...['goal','work','review','decision'].map(kind=>[typeIcon(kind),t(kind)]));
  row(...['done','doing','needs_you','waiting'].map(key=>[dot(key),t(key)]));
  row(...[['passed','pipPassed'],['returned','pipReturned'],['current','pipCurrent'],['unused','pipUnused']].map(([state,key])=>[pip(state),t(key)]));
  row([cometGlyph(),t('cometLegend')]);
  row([null,t('lineLegend')]);
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
  view.edges.forEach(e => { const a = view.nodes.find(n => n.id === e.from), b = view.nodes.find(n => n.id === e.to); $('edge-list').append(el('li', `${title(a)} → ${title(b)} · ${relationText(e)} · ${t(e.delivered ? 'delivered' : 'notDelivered')}`)); });
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
function selectNode(id) { const n=view.nodes.find(n=>n.id===id),d=view.decisions.find(d=>d.node===id); if(n?.kind==='decision'&&d){openDecision(d.id);return;} if (!showMode('flow')) return; selected = id; panel(); if (renderer) renderer.select(id); }
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
          decisionController.openFile(); updateActions();
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
  view.nodes.forEach(n => { const item=el('li');item.append(nodeCard(n));strip.append(item); }); box.append(strip);
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
    notice(decisionNotice || (!data.plan ? 'noPlan' : '')); applyView(data.view);
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

function svg(tag, attributes = {}) {
  const element=document.createElementNS(['http:', '', 'www.w3.org/2000/svg'].join('/'),tag);
  Object.entries(attributes).forEach(([key,value])=>element.setAttribute(key,String(value)));return element;
}
function typeIcon(kind) {
  const icon=svg('svg',{viewBox:'0 0 36 36','aria-hidden':'true',class:'type-icon'});
  const path=d=>icon.append(svg('path',{d,fill:'var(--paper)',stroke:'#1a1330','stroke-width':2.6,'stroke-linejoin':'round','stroke-linecap':'round'}));
  if(kind==='goal')path('M18 3 22 12 32 13 25 21 27 32 18 27 8 32 10 21 3 13 14 12Z');
  else if(kind==='review')path('M27 5C8 0 0 23 17 31 24 34 31 29 33 24 17 30 8 12 27 5Z');
  else if(kind==='decision') {
    path('M12 13H24V27H12ZM3 12H10V27H3ZM26 12H33V27H26ZM18 13V6M14 7Q18 2 22 7');
    icon.append(svg('circle',{cx:18,cy:20,r:3,fill:'#ffd166',stroke:'#1a1330','stroke-width':2}));
  } else {
    icon.append(svg('circle',{cx:18,cy:17,r:11,fill:'#c3b1ff',stroke:'#1a1330','stroke-width':2.6}));
    path('M8 15C-5 27 14 33 32 13M5 23C12 26 26 21 32 13');
  }
  return icon;
}
function cometGlyph() {
  const icon=svg('svg',{viewBox:'0 0 32 22','aria-hidden':'true',class:'comet-icon'});
  icon.append(svg('path',{d:'M25 14 2 2 11 18Z',fill:'#ff9479',stroke:'#1a1330','stroke-width':2,'stroke-linejoin':'round'}),svg('circle',{cx:24,cy:14,r:6,fill:'#fff6ea',stroke:'#1a1330','stroke-width':2}));return icon;
}
function cardTone(n) {return needs(n)||['held','awaiting_approval'].includes(n.status)?'waiting_for_you':n.status==='passed'||n.answered?'passed':['running','submitted','unverified'].includes(n.status)?'current':'unused';}
function nodeDescription(n) {return `${t(n.kind||'work')}. ${title(n)}. ${status(n)}. ${attempts(n)}. ${t('returnTimes',{n:cometCount(n)})}`;}
function nodeCard(n, expanded = false) {
  const root=el('article',undefined,'node-card '+cardTone(n)+(expanded?' expanded':''));root.dataset.node=n.id;
  const header=button('',()=>{
    const decision=view.decisions.find(d=>d.node===n.id);
    if(n.kind==='decision'){if(decision)openDecision(decision.id);else selectNode(n.id);}
    else if(selected===n.id)wholeFlow();else selectNode(n.id);
  },'node-header');
  header.setAttribute('aria-label',nodeDescription(n));header.setAttribute('aria-expanded',String(expanded));
  header.append(typeIcon(n.kind),el('strong',title(n),'node-title'),el('span',`${t(n.kind||'work')} · ${status(n)}`,'node-status'));
  const pips=el('span',undefined,'attempt-pips');pips.setAttribute('aria-label',attempts(n));
  attemptPips(n.laps,n.max_attempts,n.status).forEach(p=>{const pip=el('span',undefined,'pip '+p.state);pip.setAttribute('aria-hidden','true');pips.append(pip);});
  const tries=el('span',undefined,'attempt-row');
  tries.append(pips,el('span',n.status==='passed'&&n.attempts?(n.attempts===1?t('firstPass'):t('finishedAttempts',{n:n.attempts})):attempts(n),'attempt-caption'));
  header.append(tries);
  if(cometCount(n)){const badge=el('span',undefined,'comet-badge');badge.append(cometGlyph(),el('span',String(cometCount(n))));header.append(badge);}
  root.append(header);
  if(expanded)root.append(innerLoop(n));
  return root;
}
function innerLoop(n) {
  const loop=el('div',undefined,'inner-loop'),state=innerLoopState(needs(n)?'waiting_for_you':n.status,n.attempts);
  const diagram=el('div',undefined,'loop-diagram');diagram.setAttribute('aria-label',t('loopDescription'));
  const lines=svg('svg',{viewBox:'0 0 228 170','aria-hidden':'true',class:'loop-lines'});
  lines.append(svg('path',{d:'M62 73H136M130 68 136 73 130 78M167 94V153H130M136 148 130 153 136 158M68 153H31V94M26 100 31 94 36 100M198 73H226M220 68 226 73 220 78',fill:'none',stroke:'#6a5a8e','stroke-width':2.5,'stroke-linejoin':'round'}));diagram.append(lines);
  for(const key of ['make','check','fix']) {
    const station=el('div',undefined,'loop-state '+key+(state===key?' active':''));station.append(el('span',t(key)));
    if(state===key){const frog=el('img');frog.src='/static/assets/frog-walk-a.png';frog.alt='';station.append(frog);}
    diagram.append(station);
  }
  diagram.append(el('span',t('passes'),'loop-passes'),el('span',t('fails'),'loop-fails'));
  if(state==='exit')diagram.append(el('span','✓','loop-exit'));
  if(state==='report'){const report=el('img',undefined,'loop-report');report.src='/static/assets/frog-report.png';report.alt=t('awaiting');diagram.append(report);}
  loop.append(diagram);
  (n.returned_reasons||[]).forEach((reasons,i)=>{const row=el('p',undefined,'earlier-attempt');row.append(cometGlyph(),el('span',`${t('pastAttempt',{n:i+1})} · ${t('whyReturned')}: ${reasons.length?reasons.join(' · '):t('noReason')}`));loop.append(row);});
  return loop;
}
function createMap() {
  const map=$('map');map.tabIndex=0;
  const toolbar=el('div',undefined,'map-toolbar'),viewport=el('div',undefined,'map-viewport'),spacer=el('div',undefined,'map-spacer'),stage=el('div',undefined,'map-stage');
  viewport.tabIndex=0;viewport.setAttribute('aria-label',t('mapHelp'));spacer.append(stage);viewport.append(spacer);map.append(toolbar,viewport);
  let data={nodes:[],edges:[],decisions:[]},chosenNode=null,layout=null,scale=1,automatic=true;
  const nodes=new Map(),chips=new Map();let drawing=null;
  const zoomText=el('output');zoomText.setAttribute('aria-live','polite');
  const zoom=amount=>{automatic=false;scale=Math.max(MIN_FIT_SCALE,Math.min(1.6,scale+amount));size();};
  const fit=()=>{automatic=true;size();viewport.scrollLeft=0;viewport.scrollTop=0;};
  toolbar.append(button('−',()=>zoom(-.1)),button('+',()=>zoom(.1)),button(t('fit'),fit),zoomText,el('span',t('mapHelp'),'map-help'));
  toolbar.children[0].dataset.i18nLabel='zoomOut';toolbar.children[1].dataset.i18nLabel='zoomIn';toolbar.children[2].dataset.i18n='fit';toolbar.children[4].dataset.i18n='mapHelp';viewport.dataset.i18nLabel='mapHelp';translate();
  function size() {
    if(!layout)return;
    const w=viewport.clientWidth||900,h=viewport.clientHeight||600;
    if(automatic)scale=fitScale(layout.bounds,w-20,h-20,matchMedia('(max-width:760px)').matches);
    Object.assign(stage.style,{width:layout.bounds.width+'px',height:layout.bounds.height+'px',transform:`scale(${scale})`});
    Object.assign(spacer.style,{width:Math.max(w,layout.bounds.width*scale)+'px',height:Math.max(h,layout.bounds.height*scale)+'px'});
    zoomText.textContent=Math.round(scale*100)+'%';
  }
  const setRect=(element,rect)=>Object.assign(element.style,{left:rect.x+'px',top:rect.y+'px',width:rect.width+'px',minHeight:rect.height+'px'});
  function update(next,id) {
    const reveal=id&&id!==chosenNode;data=next;chosenNode=id;map.classList.toggle('has-expanded',!!id);
    const focused=document.activeElement?.closest?.('[data-node]')?.dataset.node;
    const activeIds=new Set(data.nodes.map(n=>n.id));
    for(const [key,element] of nodes)if(!activeIds.has(key)){element.remove();nodes.delete(key);}
    for(const n of data.nodes) {
      const expanded=n.id===chosenNode&&n.kind!=='decision';
      const signature=JSON.stringify([n,expanded,data.decisions.filter(d=>d.node===n.id)]);
      let element=nodes.get(n.id);
      if(!element){element=el('div',undefined,'node-position');nodes.set(n.id,element);stage.append(element);}
      if(element.dataset.signature!==signature){element.replaceChildren(nodeCard(n,expanded));element.dataset.signature=signature;}
    }
    const heights=Object.fromEntries([...nodes].map(([id,e])=>[id,e.firstElementChild?.offsetHeight||0]));
    layout=layeredLayout(data.nodes,data.edges.map(e=>({...e,label:e.label?label(e.label):''})),data.decisions,true,{expanded:chosenNode,heights,language});
    // Reorder existing controls without replacing them: tab order follows the drawing.
    for(const id of layout.order){const e=nodes.get(id);setRect(e,layout.positions[id]);stage.append(e);}
    if(drawing)drawing.remove();drawing=svg('svg',{width:layout.bounds.width,height:layout.bounds.height,class:'edge-layer','aria-hidden':'true'});
    const defs=svg('defs');
    for(const state of ['open','closed','returned','waiting_for_you']) {
      const marker=svg('marker',{id:'arrow-'+state,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M0 0 10 5 0 10Z',class:state}));defs.append(marker);
    }
    drawing.append(defs);stage.prepend(drawing);
    for(const element of chips.values())element.remove();chips.clear();
    for(const route of layout.routes) {
      const {start:a,end:b,chip:c}=route,bend=route.reverse?-1:1,mx=c?c.x+c.width/2:route.skip?a.x+bend*7:(a.x+b.x)/2,my=c?c.y+c.height/2:route.skip?a.y:(a.y+b.y)/2;
      const d=route.skip?`M${a.x} ${a.y} C${mx} ${a.y} ${mx} ${my} ${mx} ${my} V${route.channel+12} Q${mx} ${route.channel} ${mx+12} ${route.channel} H${b.x-30} Q${b.x-18} ${route.channel} ${b.x-18} ${route.channel+12} V${b.y-12} Q${b.x-18} ${b.y} ${b.x-6} ${b.y} H${b.x}`
        :c?`M${a.x} ${a.y} Q${mx-bend*14} ${a.y} ${mx} ${my} Q${mx+bend*14} ${b.y} ${b.x} ${b.y}`:`M${a.x} ${a.y} C${mx} ${a.y} ${mx} ${b.y} ${b.x} ${b.y}`;
      drawing.append(svg('path',{d,class:'edge-path '+route.gateState,'marker-end':`url(#arrow-${route.gateState})`}));
      if(!c||chips.has(c.first))continue;
      const chip=route.decision?button('',()=>openDecision(route.decision),'edge-chip '+route.gateState):el('div',undefined,'edge-chip '+route.gateState);
      const source=data.nodes.find(n=>n.id===route.from),targets=layout.routes.filter(r=>r.chip===c).map(r=>title(data.nodes.find(n=>n.id===r.to))).join(', ');
      chip.setAttribute('aria-label',`${edgeRelationLabel(route,language)}. ${title(source)} → ${targets}`);
      if(route.gateState==='returned')chip.append(cometGlyph());chip.append(el('span',route.text));setRect(chip,c);stage.append(chip);chips.set(c.first,chip);
    }
    // All focusable controls are ordered by column and then vertical position.
    [...nodes.values(),...chips.values()].sort((a,b)=>parseFloat(a.style.left)-parseFloat(b.style.left)||parseFloat(a.style.top)-parseFloat(b.style.top)).forEach(e=>stage.append(e));
    stage.querySelectorAll('.overview-frog,.goal-card').forEach(e=>e.remove());
    const goal=el('article',undefined,'goal-card node-card '+(data.complete?'passed':'unused'));goal.append(typeIcon('goal'),el('strong',data.title||t('goal')),el('span',`${t('goal')} · ${data.complete?t('passed'):t('notStarted')}`));setRect(goal,layout.goal);stage.append(goal);
    for(const n of data.nodes.filter(n=>needs(n)||['held','awaiting_approval'].includes(n.status))) {
      const p=layout.positions[n.id],report=el('div',undefined,'overview-frog');const frog=el('img');frog.src='/static/assets/frog-report.png';frog.alt='';report.append(frog,el('span',t('waitingBubble'),'speech'));Object.assign(report.style,{left:p.x+'px',top:p.y+p.height+8+'px'});stage.append(report);
    }
    if(data.complete){const frog=el('img',undefined,'overview-frog waving');frog.src='/static/assets/frog-wave.png';frog.alt=t('complete');Object.assign(frog.style,{left:layout.goal.x+52+'px',top:layout.goal.y+layout.goal.height+10+'px'});stage.append(frog);}
    size();
    if(reveal&&layout.positions[id]){const p=layout.positions[id],w=viewport.clientWidth||900;
      if(p.x*scale<viewport.scrollLeft+12||(p.x+p.width)*scale>viewport.scrollLeft+w-12)viewport.scrollLeft=Math.max(0,p.x*scale-(w-p.width*scale)/2);
      viewport.scrollTop=Math.max(0,p.y*scale-20);
    }
    if(focused)nodes.get(focused)?.querySelector('button')?.focus({preventScroll:true});
  }
  map.addEventListener('keydown',e=>{
    if(!['map-viewport','map'].includes(e.target.id||e.target.className))return;
    if(['+','=','-','0','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))e.preventDefault();
    if(e.key==='+'||e.key==='=')zoom(.1);if(e.key==='-')zoom(-.1);if(e.key==='0')fit();
    if(e.key==='ArrowLeft')viewport.scrollLeft-=80;if(e.key==='ArrowRight')viewport.scrollLeft+=80;
    if(e.key==='ArrowUp')viewport.scrollTop-=80;if(e.key==='ArrowDown')viewport.scrollTop+=80;
  });
  let drag=null;
  viewport.addEventListener('pointerdown',e=>{if(e.target.closest('button,summary,a'))return;drag={x:e.clientX,y:e.clientY,left:viewport.scrollLeft,top:viewport.scrollTop};viewport.setPointerCapture(e.pointerId);viewport.classList.add('panning');});
  viewport.addEventListener('pointermove',e=>{if(drag){viewport.scrollLeft=drag.left+drag.x-e.clientX;viewport.scrollTop=drag.top+drag.y-e.clientY;}});
  const release=()=>{drag=null;viewport.classList.remove('panning');};viewport.addEventListener('pointerup',release);viewport.addEventListener('pointercancel',release);
  new ResizeObserver(size).observe(viewport);
  return {update,select:id=>update(data,id),wake:size};
}
renderer = createMap(); if(view)renderer.update(view,selected);
}
