// UI_STRINGS_START
const STRINGS = {
  "ko": {
    "flow": "전체 흐름",
    "chooseRun": "흐름 고르기",
    "skip": "내용으로 건너뛰기",
    "listView": "그래프를 목록으로 보기",
    "nodes": "하는 일",
    "handoffs": "주고받는 것",
    "yourTurn": "내가 할 일",
    "choiceEffects": "고르면 생기는 일",
    "nothing": "필요해지면 여기에 나타나요.",
    "needsYou": "읽고 결정해 주세요",
    "done": "끝남",
    "doing": "하는 중",
    "waiting": "앞 일을 기다림",
    "needs_you": "내 결정을 기다림",
    "returned": "고치러 돌아옴",
    "legend": "읽는 법",
    "received": "받는 것",
    "outputs": "넘기는 것",
    "noHandoffs": "기록된 주고받기가 없어요.",
    "delivered": "받았어요",
    "notDelivered": "아직 기다려요",
    "from": "보낸 곳",
    "to": "받는 곳",
    "noReason": "돌아온 까닭이 따로 기록되지 않았어요.",
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
    "questionOnly": "이 결정에는 질문만 기록되어 있어요. 설명, 근거, 읽을 파일은 남겨지지 않았어요.",
    "writeFirst": "답을 적으면 보낼 수 있어요.",
    "leaveUnanswered": "답하지 않고 돌아가기",
    "aboutWork": "이 일은",
    "decisionRef": "결정 {id}",
    "askedBy": "물어본 곳: {who}",
    "workedBy": "맡은 곳: {who}",
    "find": "찾기",
    "findHint": "d41 또는 일 이름",
    "findNone": "“{text}”에 맞는 결정이나 일이 이 흐름에 없어요. 다른 흐름이면 위에서 흐름을 바꿔 주세요.",
    "jumpNoRun": "이 주소가 가리키는 흐름을 찾지 못했어요.",
    "roleLeader": "리더",
    "roleWorker": "작업자",
    "roleReviewer": "검토자",
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
    "answered": "답을 보냈어요. 리더 세션이 다음 확인 때 반영해요. 세션이 멈춰 있으면 채팅에서 “답했어요”라고 알려 주세요.",
    "details": "자세한 근거 보기",
    "loadEvidence": "근거 읽기",
    "noEvidence": "읽을 근거 기록이 없어요.",
    "evidenceFailed": "근거를 읽지 못했어요. 다시 해 주세요.",
    "noProjects": "등록된 프로젝트가 없어요. 프로젝트에서 새 흐름을 시작한 뒤 다시 연결해 주세요.",
    "noRun": "아직 흐름이 없어요. 프로젝트에서 새 흐름을 시작한 뒤 다시 연결해 주세요.",
    "noPlan": "아직 계획이 없어요. 이 흐름에 계획을 넣으면 여기에 나타나요.",
    "unreadable": "이 흐름을 읽지 못했어요. 기록을 확인하거나 다른 흐름을 골라 주세요.",
    "lost": "연결이 끊겼어요. 서버가 켜져 있는지 확인한 뒤 다시 연결해 주세요.",
    "unauthorized": "이 창의 열쇠가 없거나 바뀌었어요. 터미널에서 graph-flow open을 실행하거나, 에이전트 세션에 대시보드를 열어 달라고 해 주세요.",
    "retry": "다시 연결",
    "loading": "흐름을 읽고 있어요…",
    "lessons": "배운 것",
    "noLessons": "아직 기록된 배움이 없어요.",
    "complete": "모든 일이 끝났어요 · 일 {total}개",
    "waitingBubble": "읽어 주세요!",
    "unnamed": "이 일",
    "handoff": "넘길 결과",
    "overview": "내 답이 필요한 것 {needs} · 진행 중 {doing} · 끝남 {done}/{total}",
    "runOption": "{project} · {run}",
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
    "pipPassed": "통과한 시도",
    "pipReturned": "돌아온 시도",
    "pipCurrent": "지금 시도",
    "pipUnused": "남은 시도",
    "lineLegend": "선 위의 글은 넘기는 것이에요",
    "unusedAttempts": "시도 0번 · 최대 {max}번",
    "home": "할 일과 기록",
    "graph": "그래프",
    "nothingTitle": "지금은 답할 일이 없어요",
    "doingNow": "지금 하는 중",
    "idle": "지금 진행 중인 일이 없어요. 리더 세션이 다음 일을 시작하면 여기에 나타나요.",
    "log": "일어난 일",
    "logEmpty": "아직 기록된 일이 없어요.",
    "filterEmpty": "여기에 해당하는 기록이 없어요.",
    "filterAll": "전체",
    "filterMine": "내 결정",
    "filterReturned": "되돌아온 것",
    "onlyNode": "“{title}”의 기록만 보는 중",
    "showAll": "전체 보기",
    "evStarted": "흐름을 시작했어요",
    "evPlanned": "계획을 정했어요 · 일 {n}개",
    "evReplanned": "계획을 바꿨어요 · {rev}번째 계획 · 일 {n}개",
    "evRunning": "{n}번째 시도 중",
    "evSubmitted": "{n}번째 시도 제출 · 검사를 기다려요",
    "evPassed": "{n}번째 시도 통과",
    "evReturned": "{n}번째 시도 되돌아옴",
    "evReplan": "{n}번째 시도 되돌아옴 · 시도를 다 써서 새 계획이 필요해요",
    "evNeedsYou": "{n}번째 시도 · 내 답을 기다려요",
    "evHeld": "{n}번째 시도 · 멈춰 두었어요",
    "evReopened": "다시 열었어요",
    "evAsked": "질문",
    "evAnswered": "답함",
    "evFinalPassed": "최종 확인 통과",
    "evFinalFailed": "최종 확인 실패",
    "evLearned": "배운 것을 기록했어요",
    "checksPassed": "검사 {n}개 통과",
    "checksFailed": "통과하지 못한 검사: {names}",
    "rowDetails": "검사와 메모 보기",
    "checkPassed": "통과",
    "checkFailed": "실패",
    "checkTimedOut": "시간 초과",
    "exitCode": "종료 코드 {n}",
    "seconds": "{n}초",
    "gateRun": "리더가 확인",
    "workerRun": "작업자가 확인",
    "outside": "맡은 파일 밖을 건드림: {files}",
    "changedFiles": "바뀐 파일",
    "unsure": "확신이 낮은 부분",
    "findings": "검토 의견",
    "reason": "되돌린 까닭",
    "showLog": "로그 보기",
    "hideLog": "로그 접기",
    "logFailed": "로그를 읽지 못했어요.",
    "tasks": "일 {n}개 표로 보기",
    "colTask": "일",
    "colStatus": "상태",
    "colWorker": "맡은 곳",
    "colTries": "시도",
    "colWaits": "기다리는 것",
    "showInLog": "이 일의 기록 보기",
    "lessonsCount": "배운 것 {n}개",
    "copied": "복사했어요: {text}",
    "copyFailed": "복사하지 못했어요. 직접 적어 주세요: {text}",
    "copyHint": "눌러서 채팅에 붙여넣을 말을 복사",
    "roleHuman": "나",
    "sessionT3": "T3 스레드 {id}",
    "sessionClaude": "Claude 세션 {id}",
    "sessionDashboard": "대시보드",
    "selectHint": "일을 누르면 그 일의 시도와 검사 결과가 여기에 나와요.",
    "attemptsOf": "시도와 검사",
    "runOptionNeeds": "{project} · {run} · 내 답 {n}",
    "since": "{time}부터",
    "returnTimes": "돌아온 횟수 {n}번",
    "allDone": "모든 흐름이 끝났어요!"
  },
  "en": {
    "flow": "Whole flow",
    "chooseRun": "Choose a flow",
    "skip": "Skip to content",
    "listView": "Read the graph as a list",
    "nodes": "The work",
    "handoffs": "What is handed over",
    "yourTurn": "Your turn",
    "choiceEffects": "What each choice does",
    "nothing": "It will appear here when something does.",
    "needsYou": "Ready for you to read",
    "done": "Done",
    "doing": "In progress",
    "waiting": "Waiting to begin",
    "needs_you": "Waiting for you",
    "returned": "Came back",
    "legend": "How to read it",
    "received": "Receives",
    "outputs": "Hands over",
    "noHandoffs": "No handoff is recorded.",
    "delivered": "Delivered",
    "notDelivered": "Not delivered yet",
    "from": "From",
    "to": "To",
    "noReason": "No readable reason was recorded.",
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
    "questionOnly": "Only the question was recorded for this decision. No explanation, evidence or files were left.",
    "writeFirst": "Write an answer to send it.",
    "leaveUnanswered": "Go back without answering",
    "aboutWork": "This work",
    "decisionRef": "Decision {id}",
    "askedBy": "Asked by: {who}",
    "workedBy": "Worked by: {who}",
    "find": "Find",
    "findHint": "d41 or a task name",
    "findNone": "No decision or task in this flow matches “{text}”. If it belongs to another flow, switch flows above.",
    "jumpNoRun": "The flow this address points to was not found.",
    "roleLeader": "leader",
    "roleWorker": "worker",
    "roleReviewer": "reviewer",
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
    "answered": "Answer sent. The leader session applies it at its next check. If that session has stopped, tell it in the chat that you answered.",
    "details": "Details and raw evidence",
    "loadEvidence": "Read evidence",
    "noEvidence": "No evidence log is recorded.",
    "evidenceFailed": "The evidence could not be read. Please try again.",
    "noProjects": "No project is registered. Start a flow in your project, then reconnect.",
    "noRun": "There is no run yet. Start a flow in your project, then reconnect.",
    "noPlan": "This flow has no plan yet. Add a plan and it will appear here.",
    "unreadable": "This flow cannot be read. Check its records or choose another flow.",
    "lost": "Connection lost. Check that the server is running, then reconnect.",
    "unauthorized": "This window’s key is missing or changed. Run graph-flow open, or ask your agent session to open the dashboard.",
    "retry": "Reconnect",
    "loading": "Reading the flow…",
    "lessons": "What we learned",
    "noLessons": "No lessons recorded yet.",
    "complete": "Everything is done · {total} tasks",
    "waitingBubble": "Please read this.",
    "unnamed": "This task",
    "handoff": "Handoff",
    "overview": "{needs} need you · {doing} in progress · {done}/{total} done",
    "runOption": "{project} · {run}",
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
    "pipPassed": "Passed attempt",
    "pipReturned": "Returned attempt",
    "pipCurrent": "Current attempt",
    "pipUnused": "Attempt left",
    "lineLegend": "Text on a line is what gets handed over",
    "unusedAttempts": "0 attempts · up to {max}",
    "home": "To do and log",
    "graph": "Graph",
    "nothingTitle": "Nothing needs your answer",
    "doingNow": "In progress now",
    "idle": "Nothing is in progress. Work appears here when the leader session starts the next task.",
    "log": "What happened",
    "logEmpty": "Nothing has been recorded yet.",
    "filterEmpty": "No entries match.",
    "filterAll": "All",
    "filterMine": "My decisions",
    "filterReturned": "Came back",
    "onlyNode": "Showing only “{title}”",
    "showAll": "Show all",
    "evStarted": "The flow started",
    "evPlanned": "Plan set · {n} tasks",
    "evReplanned": "Plan changed · revision {rev} · {n} tasks",
    "evRunning": "attempt {n} in progress",
    "evSubmitted": "attempt {n} submitted · waiting to be checked",
    "evPassed": "attempt {n} passed",
    "evReturned": "attempt {n} came back",
    "evReplan": "attempt {n} came back · no attempts left, a new plan is needed",
    "evNeedsYou": "attempt {n} · waiting for your answer",
    "evHeld": "attempt {n} · put on hold",
    "evReopened": "reopened",
    "evAsked": "asked",
    "evAnswered": "answered",
    "evFinalPassed": "Final check passed",
    "evFinalFailed": "Final check failed",
    "evLearned": "A lesson was recorded",
    "checksPassed": "{n} checks passed",
    "checksFailed": "checks that did not pass: {names}",
    "rowDetails": "Checks and notes",
    "checkPassed": "passed",
    "checkFailed": "failed",
    "checkTimedOut": "timed out",
    "exitCode": "exit code {n}",
    "seconds": "{n}s",
    "gateRun": "checked by the leader",
    "workerRun": "checked by the worker",
    "outside": "touched files outside its own: {files}",
    "changedFiles": "Changed files",
    "unsure": "Low confidence",
    "findings": "Review findings",
    "reason": "Why it came back",
    "showLog": "Show log",
    "hideLog": "Hide log",
    "logFailed": "The log could not be read.",
    "tasks": "{n} tasks as a table",
    "colTask": "Task",
    "colStatus": "Status",
    "colWorker": "Worked by",
    "colTries": "Attempts",
    "colWaits": "Waiting for",
    "showInLog": "Show this task's entries",
    "lessonsCount": "{n} lessons",
    "copied": "Copied: {text}",
    "copyFailed": "Could not copy. Type it instead: {text}",
    "copyHint": "Copy the words to paste into the chat",
    "roleHuman": "you",
    "sessionT3": "T3 thread {id}",
    "sessionClaude": "Claude session {id}",
    "sessionDashboard": "dashboard",
    "selectHint": "Select a task to see its attempts and check results here.",
    "attemptsOf": "Attempts and checks",
    "runOptionNeeds": "{project} · {run} · {n} need you",
    "since": "since {time}",
    "returnTimes": "Came back {n} times",
    "allDone": "The whole flow is complete!"
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
    if(!groups.has(key))groups.set(key,{column:reverse?b.layer:a.layer,text,key,icon:route.gateState==='returned'?21:0,routes:[]});
    groups.get(key).routes.push(route);
  }
  for(const group of groups.values()) {
    const w=Math.min(gap-12,Math.max(34,Math.ceil(textWidth(group.text,12,6.8))+14+group.icon)),lines=Math.ceil(textWidth(group.text,12,7.2)/(gap-28-group.icon));
    const middle=group.routes.reduce((sum,r)=>sum+(r.start.y+r.end.y)/2,0)/group.routes.length;
    const chip={x:left+group.column*(width+gap)+width+(gap-w)/2,y:Math.max(8,middle-(lines*17+8)/2),width:w,height:lines*17+8,first:group.routes[0].index,key:group.key};
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
  document.querySelector('nav').setAttribute('aria-label', t('chooseRun'));
  $('find-text').placeholder = t('findHint');
  $('map').setAttribute('aria-label', t('graph'));
  document.querySelectorAll('[data-i18n-label]').forEach(e=>e.setAttribute('aria-label',t(e.dataset.i18nLabel)));
}
translate();
let chosen = null, projects = [], view = null, fingerprint = '', mode = 'home', selected = null;
let queuedRefresh = false;
let timer = 0, loading = false, generation = 0, renderer = null;
const decisionController = createDecisionController();
let decisionUI = null, decisionNotice = '', cameFrom = 'home';

async function api(path, body, text = false) {
  const response = await fetch(path, {method: body ? 'POST' : 'GET', headers: {'X-GF-Token': token, ...(body ? {'Content-Type':'application/json'} : {})}, ...(body ? {body:JSON.stringify(body)} : {})});
  if (!response.ok) { const err = new Error('request'); err.status = response.status; throw err; }
  return text ? response.text() : response.json();
}
function query(route, extra = {}, target = chosen) { return route + '?' + new URLSearchParams({project:target.project, run:target.run, ...extra}); }
function notice(key, retry = false) { const box = $('notice'); clear(box); box.hidden = !key; if (key) box.append(el('span', STRINGS[language][key] === undefined ? key : t(key))); if (retry) box.append(button(t('retry'), () => refresh(true))); }
function title(node) { return node && node.title && node.title !== node.id ? node.title : t('unnamed'); }
function otherTitle(value) { return view.nodes.some(n => n.id === value && n.title === value) ? t('unnamed') : value || t('unnamed'); }
// Legacy plans may have only an artifact path; keep that technical fallback out of normal views.
function label(value) { return !value || /[\/\\]|\.[a-z0-9]{1,8}$/.test(value) || view.nodes.some(n => n.id === value) ? t('handoff') : value; }
function relationText(edge) { return edgeRelationLabel({...edge,label:edge.label?label(edge.label):''},language); }
function question(d) { return decisionQuestion(d); }
function decisionTitle(d) { return title(view.nodes.find(n => n.id === d.node)); }
// The same words an agent session uses for this decision, so either side can find the other.
function sessionName(session) {
  const host = /^(t3|claude):(.+)$/.exec(session || '');
  if (host) return t(host[1] === 't3' ? 'sessionT3' : 'sessionClaude', {id:host[2].slice(0, 8)});
  return session === 'dashboard' ? t('sessionDashboard') : session || '';
}
function who(actor) {
  const role = {leader:'roleLeader', worker:'roleWorker', reviewer:'roleReviewer', human:'roleHuman'}[actor?.role];
  return [role ? t(role) : '', sessionName(actor?.session)].filter(Boolean).join(' · ');
}
// Time of day, with the date when it was not today.
function clock(stamp) {
  const time = stamp ? new Date(stamp) : null; if (!time || isNaN(time)) return '';
  const hours = time.toLocaleTimeString(language, {hour:'2-digit', minute:'2-digit'});
  return time.toDateString() === new Date().toDateString() ? hours : time.toLocaleDateString(language, {month:'numeric', day:'numeric'}) + ' ' + hours;
}
// An id the agent also says. Pressing it copies the words to paste back into the chat.
function refChip(id, say) {
  const chip = button(id, async event => {
    event.stopPropagation();
    // Said once; the next refresh puts back whatever the page has to report.
    try { await navigator.clipboard.writeText(say); notice(t('copied', {text:say})); } catch { notice(t('copyFailed', {text:say})); }
  }, 'ref');
  chip.title = t('copyHint'); chip.setAttribute('aria-label', `${id}. ${t('copyHint')}`); return chip;
}
function workedBy(n) { return [n.worker?.model, n.worker?.effort, sessionName(n.session)].filter(Boolean).join(' · '); }
function decisionHeading(parent, d, tag) {
  const reference = el('p', undefined, 'ref-line'); reference.append(refChip(d.id, `${d.id} · ${decisionTitle(d)}`));
  const asker = who(d.asked_by); if (asker) reference.append(el('span', t('askedBy', {who:asker})));
  if (clock(d.asked)) reference.append(el('span', clock(d.asked)));
  parent.append(reference, el(tag, decisionTitle(d)), el('p', purposeWording(d.purpose, language)));
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
function failedBlock(parent, d) {
  if (!d.failed?.length) return;
  const failed = card(t('failed')); failed.classList.add('failed');
  textList(failed, d.failed.map(text => text === STRINGS.en.untitledFailure ? t('untitledFailure') : text)); parent.append(failed);
}
function decisionCard(d) {
  const c = el('div', undefined, 'card paper'); decisionHeading(c, d, 'h3'); failedBlock(c, d); if (d.context.why) c.append(el('p', d.context.why));
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
  if (node) {
    const reference = el('p', undefined, 'ref-line'); reference.append(refChip(node.id, `${node.id} · ${title(node)}`)); if (workedBy(node)) reference.append(el('span', t('workedBy', {who:workedBy(node)})));
    p.append(el('h2', title(node)), reference, el('p', `${status(node)} · ${attempts(node)}`));
    if (node.summary) p.append(el('p', node.summary, 'muted'));
    p.append(el('p', t('attemptsOf'), 'eyebrow'), logList(view.timeline.filter(r => r.node === node.id && r.kind !== 'asked' && r.kind !== 'answered'), 'notStarted', false));
    p.append(handoffsCard('received', node.inputs, 'from'), handoffsCard('outputs', node.outputs, 'to'), button(t('showInLog'), () => showNode(node.id), 'primary'));
  } else p.append(el('p', t('selectHint')));
  const legend=el('div',undefined,'legend');legend.append(el('p',t('legend'),'eyebrow'));
  const row=(...items)=>{const line=el('p');items.forEach(([mark,text])=>{const item=el('span',undefined,'legend-item');if(mark)item.append(mark);item.append(el('span',text));line.append(item);});legend.append(line);};
  const pip=state=>el('span',undefined,'pip '+state),dot=key=>el('span',undefined,'dot '+key);
  row(...['goal','work','review','decision'].map(kind=>[typeIcon(kind),t(kind)]));
  row(...['done','doing','needs_you','waiting'].map(key=>[dot(key),t(key)]));
  row(...[['passed','pipPassed'],['returned','pipReturned'],['current','pipCurrent'],['unused','pipUnused']].map(([state,key])=>[pip(state),t(key)]));
  row([cometGlyph(),t('cometLegend')]);
  row([null,t('lineLegend')]);
  p.append(legend);
}
// One entry of the record. An attempt carries its real checks; the rest are single sentences.
const rowOpen = new Map(), logShown = new Map();
function rowSentence(r) {
  const n = r.attempt || 1;
  if (r.kind === 'started') return t('evStarted');
  if (r.kind === 'planned') return r.revision > 1 ? t('evReplanned', {rev:r.revision, n:r.count}) : t('evPlanned', {n:r.count});
  if (r.kind === 'final') return r.result === 'passed' ? t('evFinalPassed') : [t('evFinalFailed'), ...(r.failed || [])].join(' · ');
  if (r.kind === 'learned') return `${t('evLearned')} · ${r.text}`;
  if (r.kind === 'reopened') return [t('evReopened'), r.reason].filter(Boolean).join(' · ');
  if (r.kind === 'asked') return [t('evAsked'), r.question].filter(Boolean).join(' · ');
  if (r.kind === 'answered') return [t('evAnswered'), ({approved:t('approve'), revision_requested:t('sendBack')})[r.outcome], r.answer].filter(Boolean).join(' · ');
  const failed = (r.checks || []).filter(c => c.result === 'failed').map(c => c.title || c.id), passed = (r.checks || []).filter(c => c.result === 'passed').length;
  const key = {running:'evRunning', submitted:'evSubmitted', passed:'evPassed', returned:'evReturned', replan:'evReplan', needs_you:'evNeedsYou', held:'evHeld'}[r.state] || 'evRunning';
  const outcome = failed.length ? t('checksFailed', {names:failed.join(', ')}) : r.state === 'returned' && r.reason ? r.reason : passed && r.state !== 'running' ? t('checksPassed', {n:passed}) : '';
  return [t(key, {n}), outcome].filter(Boolean).join(' · ');
}
function rowTone(r) {
  if (r.kind === 'asked' || r.kind === 'answered' || r.state === 'needs_you') return 'mine';
  if (r.kind === 'reopened' || r.state === 'returned' || r.state === 'replan' || (r.kind === 'final' && r.result !== 'passed')) return 'returned';
  if (r.state === 'passed' || (r.kind === 'final' && r.result === 'passed')) return 'passed';
  return r.state === 'running' || r.state === 'submitted' ? 'running' : '';
}
function checkLine(c) {
  const item = el('li', undefined, c.result === 'failed' ? 'check-failed' : '');
  const result = c.timed_out ? t('checkTimedOut') : t(c.result === 'failed' ? 'checkFailed' : 'checkPassed');
  item.append(el('strong', `${c.result === 'failed' ? '✗' : '✓'} ${c.title || c.id}`), el('span', ` · ${result} · ${t(c.phase === 'gate' ? 'gateRun' : 'workerRun')}`));
  if (c.command) { const run = el('p', undefined, 'muted'); run.append(el('code', c.command), el('span', [c.exit_code === null || c.exit_code === undefined ? '' : ' → ' + t('exitCode', {n:c.exit_code}), typeof c.duration_ms === 'number' ? t('seconds', {n:(c.duration_ms / 1000).toFixed(2)}) : ''].filter(Boolean).join(' · '))); item.append(run); }
  if (c.violations?.length) item.append(el('p', t('outside', {files:c.violations.join(', ')})));
  if (c.log) {
    const output = el('pre'); output.hidden = true; output.tabIndex = 0;
    const show = text => { output.textContent = text; output.hidden = false; toggle.textContent = t('hideLog'); };
    const target = chosen, toggle = button(t('showLog'), async () => {
      if (!output.hidden) { output.hidden = true; toggle.textContent = t('showLog'); logShown.delete(c.log); return; }
      try { const text = await api(query('/api/evidence', {path:c.log}, target), null, true); if (sameRun(target, chosen)) logShown.set(c.log, text); show(text); } catch { show(t('logFailed')); }
    }, 'small');
    item.append(toggle, output); if (logShown.has(c.log)) show(logShown.get(c.log));
  }
  return item;
}
function logRow(r, anchor = true) {
  const item = el('li', undefined, rowTone(r)); if (anchor) item.id = r.id;
  const head = el('div', undefined, 'row-head'), text = el('span', undefined, 'row-text');
  head.append(el('span', clock(r.ts), 'row-time'));
  if (r.decision) text.append(refChip(r.decision, `${r.decision} · ${r.node_title || r.question}`));
  if (r.node) text.append(el('strong', title({id:r.node, title:r.node_title})), refChip(r.node, `${r.node} · ${r.node_title}`));
  text.append(el('span', rowSentence(r))); head.append(text);
  const by = [who(r.by), r.kind === 'attempt' ? [r.worker?.model, r.worker?.effort].filter(Boolean).join(' · ') : ''].filter(Boolean).join(' · ');
  if (by) head.append(el('span', by, 'row-who'));
  item.append(head);
  if (r.kind !== 'attempt') return item;
  const extra = [['reason', r.reason && !r.checks.some(c => c.result === 'failed') ? [r.reason] : []], ['findings', r.findings || []], ['workerNote', r.notes ? [r.notes] : []], ['unsure', r.unsure || []], ['changedFiles', r.files || []]].filter(([, values]) => values.length);
  if (!r.checks.length && !extra.length) return item;
  const details = el('details'); details.open = rowOpen.has(r.id) ? rowOpen.get(r.id) : r.state === 'returned' || r.state === 'replan';
  details.addEventListener('toggle', () => rowOpen.set(r.id, details.open));
  details.append(el('summary', t('rowDetails')));
  if (r.checks.length) { const checks = el('ul', undefined, 'checks'); r.checks.forEach(c => checks.append(checkLine(c))); details.append(checks); }
  for (const [key, values] of extra) { details.append(el('p', t(key), 'eyebrow')); textList(details, values); }
  item.append(details); return item;
}
function logList(rows, empty, anchor = true) {
  const list = el('ol', undefined, 'log');
  if (!rows.length) list.append(el('li', t(empty)));
  [...rows].sort((a, b) => b.seq - a.seq).forEach(r => list.append(logRow(r, anchor)));
  return list;
}
let logFilter = 'all', logNode = null, found = null, mark = null;
function home() {
  const box = $('home'); clear(box);
  const inbox = el('section'); inbox.append(el('p', t('yourTurn'), 'eyebrow'), el('h2', t(view.decisions.length ? 'needsYou' : 'nothingTitle')));
  view.decisions.forEach(d => inbox.append(decisionCard(d)));
  if (!view.decisions.length) inbox.append(el('p', t('nothing'), 'muted'));
  box.append(inbox);
  if (!view.complete) {
    const now = el('section'), list = el('ul', undefined, 'now'); now.append(el('h2', t('doingNow')));
    const active = view.nodes.filter(n => !needs(n) && !['passed','pending','ready','blocked'].includes(n.status) && n.attempts);
    for (const n of active) {
      const item = el('li'); if (n.status === 'running') item.append(walker());
      item.append(el('strong', title(n)), refChip(n.id, `${n.id} · ${title(n)}`), el('span', `${status(n)} · ${attempts(n)}`));
      const by = [workedBy(n), clock(n.started) ? t('since', {time:clock(n.started)}) : ''].filter(Boolean).join(' · '); if (by) item.append(el('span', by, 'row-who'));
      list.append(item);
    }
    now.append(active.length ? list : el('p', t('idle'), 'muted')); if (active.length || !view.decisions.length) box.append(now);
  }
  const log = el('section'); log.id = 'log'; log.append(el('h2', t('log')));
  const filters = el('div', undefined, 'filters');
  for (const [key, name] of [['all','filterAll'],['mine','filterMine'],['returned','filterReturned']]) { const b = button(t(name), () => { logFilter = key; home(); }, 'small'); b.setAttribute('aria-pressed', String(logFilter === key)); filters.append(b); }
  const only = view.nodes.find(n => n.id === logNode);
  if (only) filters.append(el('span', t('onlyNode', {title:title(only)})), button(t('showAll'), () => { logNode = null; home(); }, 'small'));
  const rows = view.timeline.filter(r => (!only || r.node === only.id) && (logFilter === 'all' || rowTone(r) === (logFilter === 'mine' ? 'mine' : 'returned')));
  log.append(filters, logList(rows, view.timeline.length ? 'filterEmpty' : 'logEmpty')); box.append(log);
  const tasks = el('details'); tasks.id = 'tasks'; tasks.open = !!rowOpen.get('tasks'); tasks.addEventListener('toggle', () => rowOpen.set('tasks', tasks.open));
  tasks.append(el('summary', t('tasks', {n:view.nodes.length})));
  const wrap = el('div', undefined, 'table-wrap'), table = el('table', undefined, 'tasks'), heads = el('tr');
  ['colTask','colStatus','colWorker','colTries','colWaits'].forEach(key => { const th = el('th', t(key)); th.scope = 'col'; heads.append(th); }); table.append(heads);
  for (const n of view.nodes) {
    const line = el('tr'), name = el('td'); name.append(button(title(n), () => showNode(n.id), 'link'), refChip(n.id, `${n.id} · ${title(n)}`));
    const waits = n.inputs.filter(i => !i.delivered).map(i => otherTitle(i.other_title));
    line.append(name, el('td', status(n)), el('td', workedBy(n)), el('td', `${n.attempts || 0}/${n.max_attempts || 3}`), el('td', [...new Set(waits)].join(', '))); table.append(line);
  }
  wrap.append(table); tasks.append(wrap); box.append(tasks);
  if (view.lessons.length) { const lessons = el('details'); lessons.open = !!rowOpen.get('lessons'); lessons.addEventListener('toggle', () => rowOpen.set('lessons', lessons.open)); lessons.append(el('summary', t('lessonsCount', {n:view.lessons.length}))); textList(lessons, view.lessons.map(l => l.node_title ? `${otherTitle(l.node_title)} · ${l.text}` : l.text)); box.append(lessons); }
  const marked = document.getElementById(mark || ''); if (marked) marked.classList.add('found');
  if (found) { const target = document.getElementById(found); found = null; if (target) target.scrollIntoView({block:target.id === 'log' ? 'start' : 'center', behavior:reduced.matches ? 'auto' : 'smooth'}); }
}
// Show one task's entries in the record, where the agent's words about it can be matched by time.
function showNode(id) { if (!showMode('home')) return; logNode = id; logFilter = 'all'; mark = null; found = 'log'; home(); }
function accessible() {
  clear($('node-list')); clear($('edge-list')); clear($('decision-list'));
  const order = layeredLayout(view.nodes,view.edges,view.decisions).order;
  [...view.nodes].sort((a,b)=>order.indexOf(a.id)-order.indexOf(b.id)).forEach(n => { const item = el('li', undefined, 'card'); item.append(button(title(n), () => selectNode(n.id)), el('p', status(n)), el('p', attempts(n), 'muted'), el('p', n.summary)); if (n.returned_reasons.length) textList(item, n.returned_reasons.flat(), 'noReason'); $('node-list').append(item); });
  view.edges.forEach(e => { const a = view.nodes.find(n => n.id === e.from), b = view.nodes.find(n => n.id === e.to); $('edge-list').append(el('li', `${title(a)} → ${title(b)} · ${relationText(e)} · ${t(e.delivered ? 'delivered' : 'notDelivered')}`)); });
  view.decisions.forEach(d => { const item = el('li'); item.append(button(t('read'), () => openDecision(d.id))); decisionHeading(item, d, 'h3'); failedBlock(item, d); if (d.context.why) item.append(el('p', d.context.why)); $('decision-list').append(item); });
  if (!view.decisions.length) $('decision-list').append(el('li', t('nothingTitle')));
}
function showMode(next) {
  if (next !== 'decision' && !discardDecision()) return false;
  mode = next; $('home').hidden = next !== 'home'; $('flow').hidden = next !== 'flow'; $('decision').hidden = next !== 'decision'; $('accessible').hidden = next !== 'flow';
  $('home-tab').setAttribute('aria-pressed', String(next === 'home')); $('flow-tab').setAttribute('aria-pressed', String(next === 'flow'));
  // The map can only measure its cards while it is on screen.
  if (renderer && next === 'flow' && view) renderer.update(view, selected); return true;
}
function discardDecision() {
  if (!decisionController.close()) return false;
  decisionUI = null; clear($('decision')); return true;
}
function closeInvalidDecision(run, decisions) {
  const reason = decisionController.refresh({decisions}, run);
  if (!reason) return false;
  goHome(); decisionNotice = reason; notice(decisionNotice); return true;
}
function goHome() { if (showMode('home') && view) home(); }
function showGraph() { if (!showMode('flow')) return; panel(); }
function selectNode(id) { const n=view.nodes.find(n=>n.id===id),d=view.decisions.find(d=>d.node===id); if(n?.kind==='decision'&&d){openDecision(d.id);return;} if (!showMode('flow')) return; selected = selected === id ? null : id; panel(); if (renderer) renderer.select(selected); }
function focusHeading(heading) { heading.tabIndex = -1; heading.focus(); }
function openDecision(id, focus = true) {
  const session = decisionController.open(id); if (!session) return;
  const current = () => decisionController.session === session;
  const d = session.decision;
  if (decisionUI?.session === session) { decisionUI.update(); return; }
  decisionNotice = ''; notice('');
  if (mode !== 'decision') cameFrom = mode;
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
    // Say why sending is unavailable instead of leaving a silent disabled button.
    if (isQuestion && current() && !session.busy && (!message.textContent || message.textContent === t('writeFirst'))) message.textContent = input.value.trim() ? '' : t('writeFirst');
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
    if (result.close && mode === 'decision') leaveDecision();
    decisionNotice = result.notice; notice(decisionNotice);
    if (current()) { message.textContent = t(result.notice); updateActions(); }
    $('picker').disabled = !!decisionController.session?.busy;
    if (result.refresh) refresh(true);
  };
  let approveButton;
  const actionButton = (outcome, text, cls) => { const b = button(text, () => send(outcome), cls); b.dataset.outcome = outcome; return b; };
  if (isQuestion) actions.append(actionButton('answered', t('answer'), 'primary'));
  else { approveButton = actionButton('approved', '', 'primary'); actions.append(approveButton, actionButton('revision_requested', t('sendBack'))); }
  const backButton = button(t('leaveUnanswered'), leaveDecision); actions.append(backButton); reading.append(actions);
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
    const node = view.nodes.find(n => n.id === decision.node); if (node?.summary) introduction.append(el('p', `${t('aboutWork')}: ${node.summary}`, 'muted'));
    updateFiles(decision);
    note.textContent = decision.worker_note || ''; report.hidden = !decision.worker_note;
    clear(outcomes); outcomes.append(el('p', t('choiceEffects'), 'eyebrow'));
    const effects = [['if_approved','ifApproved'],['if_rejected','ifRejected'],['undo','undo']].filter(([key]) => decision.context[key]);
    for (const [key, name] of effects) outcomes.append(el('small', t(name)), el('p', decision.context[key]));
    outcomes.hidden = !effects.length;
    clear(surrounding); if (decision.context.why) surrounding.append(card(t('why'), decision.context.why));
    failedBlock(surrounding, decision);
    for (const key of ['verified','unverified']) { if (!decision[key]?.length) continue; const c = card(t(key)); textList(c, decision[key]); surrounding.append(c); }
    files.hidden = !decision.files?.length;
    const bare = !decision.worker_note && !effects.length && !decision.context.why && !decision.failed?.length && !decision.verified?.length && !decision.unverified?.length && !decision.files?.length;
    if (bare) surrounding.append(el('p', t('questionOnly'), 'muted'));
    reminder.hidden = !decision.has_evidence && !decisionController.requiresDetails;
    if (approveButton) approveButton.textContent = purposeAction(decision.purpose, language, decision.failed);
    updateActions();
  };
  decisionUI = {session, update}; update(); if (focus) focusHeading(introduction.querySelector('h2'));
}
function leaveDecision() { if (cameFrom === 'flow') showGraph(); else goHome(); }
let pendingJump = null;
function readFragment() {
  const target = Object.fromEntries(new URLSearchParams(location.hash.slice(1)));
  if (!target.decision && !target.node && !target.run) return;
  history.replaceState(null, '', location.pathname + location.search);
  pendingJump = target;
  if (target.project && target.run && !decisionController.session?.busy) setChosen({project:target.project, run:target.run});
  refresh(true);
}
function jump(target) {
  if (target.run && !(chosen && chosen.run === target.run && (!target.project || chosen.project === target.project))) { decisionNotice = t('jumpNoRun'); notice(decisionNotice); return false; }
  const miss = text => { decisionNotice = t('findNone', {text}); notice(decisionNotice); return false; };
  if (target.decision) {
    const id = target.decision.toLowerCase();
    if (view.decisions.some(d => d.id === id)) { openDecision(id); return true; }
    const row = [...view.timeline].reverse().find(r => r.decision === id); if (!row) return miss(target.decision);
    decisionNotice = ''; notice(''); if (!showMode('home')) return false;
    logNode = null; logFilter = 'all'; found = mark = row.id; home(); return true;
  }
  if (target.node) {
    const text = target.node.toLowerCase();
    const node = view.nodes.find(n => n.id.toLowerCase() === text) || view.nodes.find(n => (n.title || '').toLowerCase().includes(text));
    if (!node) return miss(target.node);
    decisionNotice = ''; notice(''); showNode(node.id); return true;
  }
  return true;
}
function find(text) {
  text = text.trim(); if (!text || !view) return false;
  return /^d\d+$/i.test(text) ? jump({decision:text}) : jump({node:text});
}
function applyView(next) {
  if (decisionController.session?.busy) return;
  closeInvalidDecision(chosen, next.decisions);
  const nextFingerprint = JSON.stringify(next); if (nextFingerprint === fingerprint) return;
  language = viewLanguage(next, navigator.language); translate();
  view = next; fingerprint = nextFingerprint; if (!view.nodes.some(n => n.id === selected)) selected = null; if (!view.nodes.some(n => n.id === logNode)) logNode = null; showMode(mode);
  $('title').textContent = view.title || t('brand'); $('where').textContent = [view.project, view.run].filter(Boolean).join(' · ');
  $('subtitle').textContent = view.complete ? t('complete', {total:view.nodes.length}) : t('overview', {total:view.nodes.length, done:view.counts.done, doing:view.counts.doing, needs:view.counts.needs_you});
  accessible(); panel(); home(); if (renderer && mode === 'flow') renderer.update(view, selected);
  if (mode === 'decision' && decisionController.session) openDecision(decisionController.session.target.id, false);
}
function setChosen(next) {
  if (decisionController.session?.busy || sameRun(chosen, next)) return;
  closeInvalidDecision(next, []); chosen = next; generation++; resetView(); logNode = null; logFilter = 'all'; found = mark = null; rowOpen.clear(); logShown.clear(); showMode('home');
}
function chooseRuns(data) {
  projects = data.projects;
  const runs = projects.flatMap(p => (p.runs || []).map((r, i) => ({...r, project:p.root, projectName:p.name, number:i + 1})));
  runs.sort((a,b) => Number(b.status === 'open') - Number(a.status === 'open') || (b.last_event || '').localeCompare(a.last_event || ''));
  if (!chosen || !runs.some(r => r.project === chosen.project && r.id === chosen.run)) { const first = runs.find(r => !r.error) || runs[0]; setChosen(first ? {project:first.project,run:first.id} : null); }
  const picker = $('picker'); picker.disabled = !!decisionController.session?.busy; clear(picker);
  runs.forEach((r, i) => { const option = el('option', t(r.open_decisions ? 'runOptionNeeds' : 'runOption', {project:r.projectName, run:r.id, n:r.open_decisions})); option.value = String(i); option.selected = !!chosen && r.project === chosen.project && r.id === chosen.run; picker.append(option); });
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
    if (pendingJump && view && !decisionController.session?.busy) { const target = pendingJump; pendingJump = null; jump(target); }
  } catch (error) { if (currentGeneration === generation) notice(error.status === 401 ? 'unauthorized' : error.status === 400 || error.status === 404 || error.status === 500 ? 'unreadable' : 'lost', true); }
  finally { loading = false; if (queuedRefresh) { queuedRefresh = false; refresh(true); } else schedule(); }
}
function resetView() { language = viewLanguage(null, navigator.language); translate(); closeInvalidDecision(chosen, []); view = null; selected = null; fingerprint = ''; ['node-list','edge-list','decision-list','panel','home'].forEach(id => clear($(id))); if (renderer) renderer.update({nodes:[],edges:[],decisions:[],complete:false}, null); $('flow').hidden = true; $('home').hidden = true; $('accessible').hidden = true; $('decision').hidden = true; $('subtitle').textContent = ''; $('where').textContent = ''; }
function schedule() { clearTimeout(timer); if (!document.hidden) timer = setTimeout(refresh, 2000); }
$('home-tab').addEventListener('click', () => { if (view) goHome(); });
$('flow-tab').addEventListener('click', () => { if (view) showGraph(); });
$('find').addEventListener('submit', event => { event.preventDefault(); if (find($('find-text').value)) $('find-text').value = ''; });
addEventListener('hashchange', readFragment);
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !e.isComposing && view) { if (mode === 'decision') leaveDecision(); else if (mode === 'flow' && selected) selectNode(selected); } });
document.addEventListener('visibilitychange', () => { clearTimeout(timer); if (renderer) renderer.wake(); if (!document.hidden) refresh(true); });
reduced.addEventListener('change', () => { if (renderer) renderer.wake(); });
notice('loading'); readFragment(); refresh();

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
// Two walking frames; the second stays hidden when motion is reduced.
function walker() {
  const frames=el('span',undefined,'walker');frames.setAttribute('aria-hidden','true');
  for(const source of ['/static/assets/frog-walk-a.png','/static/assets/frog-walk-b.png']){const frog=el('img');frog.src=source;frog.alt='';frames.append(frog);}
  return frames;
}
// A rebuilt element joins a looping animation at the phase it would have reached.
function inPhase(element, period) {element.style.animationDelay=-(performance.now()%period)+'ms';return element;}
function nodeDescription(n) {return `${t(n.kind||'work')}. ${title(n)}. ${status(n)}. ${attempts(n)}. ${t('returnTimes',{n:cometCount(n)})}`;}
function nodeCard(n, expanded = false) {
  const root=el('article',undefined,'node-card '+cardTone(n)+(n.status==='running'?' working':'')+(expanded?' expanded':''));root.dataset.node=n.id;
  const header=button('',()=>{
    const decision=view.decisions.find(d=>d.node===n.id);
    if(n.kind==='decision'){if(decision)openDecision(decision.id);else selectNode(n.id);}
    else selectNode(n.id);
  },'node-header');
  header.setAttribute('aria-label',nodeDescription(n));header.setAttribute('aria-expanded',String(expanded));
  header.append(typeIcon(n.kind),el('strong',title(n),'node-title'),el('span',`${t(n.kind||'work')} · ${status(n)}`,'node-status'));
  const pips=el('span',undefined,'attempt-pips');pips.setAttribute('aria-label',attempts(n));
  attemptPips(n.laps,n.max_attempts,n.status).forEach(p=>{const pip=el('span',undefined,'pip '+p.state);pip.setAttribute('aria-hidden','true');pips.append(pip);});
  const tries=el('span',undefined,'attempt-row');
  tries.append(pips,el('span',n.status==='passed'&&n.attempts?(n.attempts===1?t('firstPass'):t('finishedAttempts',{n:n.attempts})):attempts(n),'attempt-caption'));
  header.append(tries);
  const reference=el('span',undefined,'ref-line');reference.append(el('span',n.id,'ref'));if(workedBy(n))reference.append(el('span',workedBy(n)));header.append(reference);
  if(cometCount(n)){const badge=el('span',undefined,'comet-badge');badge.append(cometGlyph(),el('span',String(cometCount(n))));header.append(badge);}
  root.append(header);
  return root;
}
function createMap() {
  const map=$('map');map.tabIndex=0;
  const toolbar=el('div',undefined,'map-toolbar'),viewport=el('div',undefined,'map-viewport'),spacer=el('div',undefined,'map-spacer'),stage=el('div',undefined,'map-stage');
  viewport.tabIndex=0;viewport.setAttribute('aria-label',t('mapHelp'));spacer.append(stage);viewport.append(spacer);map.append(toolbar,viewport);
  let data={nodes:[],edges:[],decisions:[]},chosenNode=null,layout=null,scale=1,automatic=true;
  const nodes=new Map(),chips=new Map(),seen=new Map();let drawing=null,wasComplete=null;
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
    const focused=document.activeElement?.closest?.('[data-node]')?.dataset.node,focusedChip=document.activeElement?.dataset?.chip;
    const activeIds=new Set(data.nodes.map(n=>n.id));
    for(const [key,element] of nodes)if(!activeIds.has(key)){element.remove();nodes.delete(key);}
    for(const n of data.nodes) {
      const expanded=n.id===chosenNode&&n.kind!=='decision';
      const signature=JSON.stringify([n,expanded,data.decisions.filter(d=>d.node===n.id)]);
      let element=nodes.get(n.id);
      if(!element){element=el('div',undefined,'node-position');nodes.set(n.id,element);stage.append(element);}
      if(element.dataset.signature!==signature) {
        const card=nodeCard(n,expanded),before=seen.get(n.id),tone=cardTone(n);
        // One-shot motion only for a change observed while the page was open.
        if(before&&cometCount(n)>before.comets)card.classList.add('shake');
        else if(before&&before.tone!==tone&&['passed','current'].includes(tone))card.classList.add('pop');
        element.replaceChildren(card);if(n.status==='running')element.append(walker());element.dataset.signature=signature;
      }
      seen.set(n.id,{tone:cardTone(n),comets:cometCount(n)});
    }
    const heights=Object.fromEntries([...nodes].map(([id,e])=>[id,e.firstElementChild?.offsetHeight||0]));
    layout=layeredLayout(data.nodes,data.edges.map(e=>({...e,label:e.label?label(e.label):''})),data.decisions,true,{heights,language});
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
      const d=route.skip?`M${a.x} ${a.y} C${mx} ${a.y} ${mx} ${my} ${mx} ${my} V${route.channel+12} Q${mx} ${route.channel} ${mx+bend*12} ${route.channel} H${b.x-bend*30} Q${b.x-bend*18} ${route.channel} ${b.x-bend*18} ${route.channel+12} V${b.y-12} Q${b.x-bend*18} ${b.y} ${b.x-bend*6} ${b.y} H${b.x}`
        :c?`M${a.x} ${a.y} Q${mx-bend*14} ${a.y} ${mx} ${my} Q${mx+bend*14} ${b.y} ${b.x} ${b.y}`:`M${a.x} ${a.y} C${mx} ${a.y} ${mx} ${b.y} ${b.x} ${b.y}`;
      const flowing=route.gateState==='open'&&data.nodes.find(n=>n.id===route.to)?.status==='running';
      const line=svg('path',{d,class:'edge-path '+route.gateState+(flowing?' flowing':''),'marker-end':`url(#arrow-${route.gateState})`});
      drawing.append(flowing?inPhase(line,1000):line);
      if(!c||chips.has(c.first))continue;
      const chip=route.decision?button('',()=>openDecision(route.decision),'edge-chip '+route.gateState):el('div',undefined,'edge-chip '+route.gateState);
      const source=data.nodes.find(n=>n.id===route.from),targets=layout.routes.filter(r=>r.chip===c).map(r=>title(data.nodes.find(n=>n.id===r.to))).join(', ');
      chip.setAttribute('aria-label',`${edgeRelationLabel(route,language)}. ${title(source)} → ${targets}`);
      if(route.gateState==='returned')chip.append(cometGlyph());chip.append(el('span',route.decision?`${route.text} · ${route.decision}`:route.text));chip.dataset.chip=c.key;setRect(chip,c);stage.append(chip);chips.set(c.first,chip);
    }
    // All focusable controls are ordered by column and then vertical position.
    [...nodes.values(),...chips.values()].sort((a,b)=>parseFloat(a.style.left)-parseFloat(b.style.left)||parseFloat(a.style.top)-parseFloat(b.style.top)).forEach(e=>stage.append(e));
    stage.querySelectorAll('.overview-frog,.goal-card').forEach(e=>e.remove());
    const goal=el('article',undefined,'goal-card node-card '+(data.complete?'passed':'unused')+(data.complete&&wasComplete===false?' pop':''));wasComplete=!!data.complete;goal.append(typeIcon('goal'),el('strong',data.title||t('goal')),el('span',`${t('goal')} · ${data.complete?t('passed'):t('notStarted')}`));setRect(goal,layout.goal);stage.append(goal);
    for(const n of data.nodes.filter(n=>needs(n)||['held','awaiting_approval'].includes(n.status))) {
      const p=layout.positions[n.id],report=el('div',undefined,'overview-frog');const frog=el('img');frog.src='/static/assets/frog-report.png';frog.alt='';report.append(inPhase(frog,1200),el('span',[t('waitingBubble'),...data.decisions.filter(d=>d.node===n.id).map(d=>d.id)].join(' '),'speech'));Object.assign(report.style,{left:p.x+'px',top:p.y+p.height+8+'px'});stage.append(report);
    }
    if(data.complete){const frog=el('img',undefined,'overview-frog waving');frog.src='/static/assets/frog-wave.png';frog.alt=t('allDone');inPhase(frog,1200);Object.assign(frog.style,{left:layout.goal.x+52+'px',top:layout.goal.y+layout.goal.height+10+'px'});stage.append(frog);}
    size();
    if(reveal&&layout.positions[id]){const p=layout.positions[id],w=viewport.clientWidth||900;
      if(p.x*scale<viewport.scrollLeft+12||(p.x+p.width)*scale>viewport.scrollLeft+w-12)viewport.scrollLeft=Math.max(0,p.x*scale-(w-p.width*scale)/2);
      viewport.scrollTop=Math.max(0,p.y*scale-20);
    }
    if(focused)nodes.get(focused)?.querySelector('button')?.focus({preventScroll:true});
    if(focusedChip)[...chips.values()].find(e=>e.dataset.chip===focusedChip&&e.tagName==='BUTTON')?.focus({preventScroll:true});
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
