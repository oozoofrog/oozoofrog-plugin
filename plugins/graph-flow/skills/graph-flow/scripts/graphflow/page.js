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
    "needsYou": "내가 할 일",
    "done": "끝남",
    "doing": "하는 중",
    "waiting": "앞 일을 기다림",
    "needs_you": "내가 할 일",
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
    "attempt": "{n}번째 시도예요 · 최대 {max}번",
    "notStarted": "시작 전이에요",
    "passed": "끝났어요",
    "running": "만들고 있어요",
    "retrying": "고치고 있어요",
    "submitted": "검사받고 있어요",
    "awaiting": "내가 할 일",
    "held": "다음 방향을 기다려요",
    "exhausted": "다음 계획이 필요해요",
    "noAction": "지금은 하실 일이 없어요. 세 번 안에 통과하지 못하면 알려 드릴게요.",
    "read": "읽고 결정하기",
    "why": "왜 내가 봐야 하나요",
    "verified": "이미 확인된 것",
    "unverified": "아직 확인 안 된 것",
    "workerNote": "작업자 메모",
    "notRecorded": "따로 기록되지 않았어요.",
    "questionOnly": "이 결정에는 질문만 기록되어 있어요. 설명, 근거, 읽을 파일은 남겨지지 않았어요.",
    "writeFirst": "답을 적으면 보낼 수 있어요.",
    "leaveUnanswered": "답하지 않고 돌아가기",
    "aboutWork": "일의 상세 내용",
    "decisionRef": "결정 {id}",
    "askedBy": "물어본 곳: {who}",
    "workedBy": "맡은 곳: {who}",
    "find": "찾기",
    "findHint": "결정 번호 또는 일 이름",
    "findNone": "“{text}”에 맞는 결정이나 일이 이 흐름에 없어요. 다른 흐름이면 위에서 흐름을 바꿔 주세요.",
    "jumpNoRun": "이 주소가 가리키는 흐름을 찾지 못했어요.",
    "roleLeader": "진행 담당자",
    "roleWorker": "작업 담당자",
    "roleReviewer": "검토 담당자",
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
    "answered": "답을 보냈어요. 진행 담당자이 다음 확인 때 반영해요. 세션이 멈춰 있으면 채팅에서 “답했어요”라고 알려 주세요.",
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
    "complete": "모든 일이 끝났어요",
    "unnamed": "이 일",
    "handoff": "넘길 결과",
    "overview": "진행 중 {doing} · 끝남 {done}/{total}",
    "runOption": "{run}",
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
    "noFiles": "이 결정에는 읽을 파일이 기록되지 않았어요.",
    "goal": "목표",
    "work": "작업",
    "review": "검토",
    "decision": "결정",
    "handsOver": "넘겨줌",
    "reviews": "검토를 맡겼어요",
    "waitsForDecision": "결정을 기다림",
    "towardGoal": "목표로",
    "fit": "화면에 맞추기",
    "zoomIn": "크게 보기",
    "zoomOut": "작게 보기",
    "mapHelp": "끌어서 이동 · + − 확대 · 0 맞추기",
    "firstPass": "시도 1회",
    "finishedAttempts": "시도 {n}회",
    "lineLegend": "실선 → 넘겼어요 · 파선 ⇢ 아직 기다려요 · 점선 ↶ 검토해요",
    "unusedAttempts": "최대 {max}번 시도할 수 있어요",
    "home": "할 일과 기록",
    "graph": "그래프",
    "nothingTitle": "지금은 답할 일이 없어요",
    "doingNow": "지금 하는 중",
    "idle": "지금 진행 중인 일이 없어요. 진행 담당자이 다음 일을 시작하면 여기에 나타나요.",
    "log": "일어난 일",
    "logEmpty": "아직 기록된 일이 없어요.",
    "filterEmpty": "여기에 해당하는 기록이 없어요.",
    "filterAll": "전체",
    "filterMine": "내가 할 일",
    "filterReturned": "되돌아온 것",
    "onlyNode": "“{title}”의 기록만 보는 중",
    "showAll": "전체 보기",
    "evStarted": "실행 기록을 만들었어요",
    "evPlanned": "계획을 올렸어요",
    "evReplanned": "계획을 바꿨어요 · {rev}번째 계획",
    "evRunning": "{n}번째 시도 중",
    "evSubmitted": "{n}번째 시도 제출 · 검사를 기다려요",
    "evPassed": "{n}번째 시도 통과",
    "evReturned": "{n}번째 시도 되돌아옴",
    "evReplan": "{n}번째 시도 되돌아옴 · 시도를 다 써서 새 계획이 필요해요",
    "evNeedsYou": "{n}번째 시도 · 내가 할 일",
    "evHeld": "{n}번째 시도 · 멈춰 두었어요",
    "evReopened": "다시 열었어요",
    "evAsked": "질문",
    "evAnswered": "질문에 답했어요",
    "evFinalPassed": "최종 확인 통과",
    "evFinalFailed": "최종 확인 실패",
    "evLearned": "배운 것을 기록했어요",
    "checksPassed": "검사 {n}개 통과",
    "checksFailed": "✕ {n}번째 시도에서 “{names}” 확인이 통과하지 못했어요",
    "rowDetails": "검사와 메모 보기",
    "checkPassed": "통과",
    "checkFailed": "실패",
    "checkTimedOut": "시간 초과",
    "exitCode": "명령 반환값 {n}",
    "seconds": "{n}초",
    "gateRun": "진행 담당자이 확인했어요",
    "workerRun": "작업 담당자이 확인했어요",
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
    "runOptionNeeds": "{run}",
    "since": "{time}부터",
    "returnTimes": "이전에 {n}번 돌아왔어요",
    "allDone": "이 흐름이 끝났어요",
    "answerHere": "결정 {id} · 읽고 결정하기",
    "lineOpen": "넘겨줬어요",
    "lineClosed": "아직 넘기지 않았어요",
    "lineWaiting": "내가 할 일을 기다려요",
    "lineReturned": "전달을 기다려요",
    "lineReview": "검토해요",
    "tries": "시도 {n}/{max}",
    "closeDetails": "자세한 내용 닫기",
    "mapDirection": "왼쪽에서 오른쪽으로",
    "checkMet": "✓ {title}",
    "workingHere": "작업 담당자이 진행 중이에요",
    "offLeft": "← 왼쪽",
    "offRight": "오른쪽 →",
    "offTop": "↑ 위쪽",
    "offBottom": "↓ 아래쪽",
    "offCount": "{direction} {n}개",
    "visibleCards": "{summary} · {n}개가 보여요",
    "graphEdges": "화면 밖의 일로 이동해요",
    "history": "이 일의 시도와 검사 기록",
    "currentAttempt": "지금 시도",
    "earlierAttempt": "이전 시도",
    "gateReview": "답하기 전에 이 결정의 기록을 확인해 주세요.",
    "noAttemptChecks": "이 시도의 검사 결과는 아직 기록되지 않았어요.",
    "previousReason": "이전에 돌아온 까닭: {reason}",
    "offWorking": " · 진행 {n}",
    "offNeeds": " · 내가 할 일 {n}",
    "workerDetails": "담당자 · 받는 것 · 넘기는 것",
    "attemptRecord": "{n}번째 시도의 검사와 메모",
    "earlierFailure": "✕ {n}번째 시도에서 “{reason}” 확인이 통과하지 못했어요",
    "findDecisionHint": "{id} 또는 일 이름",
    "scopeCheck": "맡은 파일만 고쳤어요",
    "noCurrentChecks": "지금 시도의 검사 결과도 아직 없어요.",
    "revisionHint": "고칠 곳을 적으면 보낼 수 있어요",
    "nodeRef": "일 {id}",
    "answeredApproval": "결과를 받아들이기로 답했어요",
    "answeredRevision": "고쳐 달라고 답했어요",
    "answeredRejection": "받아들이지 않기로 답했어요",
    "lineSampleOpen": "결과 전달",
    "lineSampleClosed": "전달 대기",
    "lineSampleReview": "검토 관계",
    "attemptShort": "{n}번째 시도",
    "earlierHistory": "이전 시도 기록",
    "failureUnknownAttempt": "✕ 기록된 시도에서 “{names}” 확인이 통과하지 못했어요",
    "modelName": "모델 {model}",
    "blindApproval": "채팅에서 에이전트 세션에 결과를 보여 달라고 하거나, 고칠 곳을 적어 돌려보내 주세요.",
    "showDiagram": "선으로 된 그래프 보기",
    "showFlowList": "읽기 쉬운 목록 보기",
    "mapDown": "위에서 아래로",
    "pastReturn": "이전 시도 {n}번 되돌아옴",
    "nothingToJudge": "판단할 자료가 없어요",
    "nothingToJudgeBody": "읽을 파일도, 지금 시도의 검사 결과도 없어요. 결과를 보여 달라고 돌려보내거나 채팅에서 다시 물어봐 주세요.",
    "confirmBlind": "파일과 검사 결과 없이 받아들일게요",
    "blindHint": "자료 없이 받아들이려면 위 내용을 확인해 주세요.",
    "acceptBlind": "자료 없이 받아들이기",
    "minZoom": "글자를 읽을 수 있는 최소 크기예요",
    "readGateHint": "파일이나 근거를 먼저 열어 주세요",
    "approveEffect": "받아들이기로 한 답이 진행 담당자에 전달돼요",
    "revisionEffect": "고칠 곳이 진행 담당자에 전달돼요",
    "answerEffect": "답이 진행 담당자에 전달돼요",
    "retryEffect": "다음은 최대 {max}번 중 {n}번째 시도예요",
    "decisionWork": "관련 일 · {title}",
    "fitAll": "전체 보기",
    "readScale": "읽기 크기",
    "planSummary": "일 {work}개 · 검토 {review}개 · 결정 {decision}개",
    "planStart": "시작",
    "planStartEffect": "시작하면 담당자가 이 계획의 일을 시작할 수 있어요.",
    "planBackEffect": "고칠 내용을 담당자에게 보내요.",
    "planSentBack": "계획을 돌려보냈어요",
    "planWaiting": "계획을 확인해 주세요",
    "planSentNote": "내가 보낸 내용",
    "planWaitingRevision": "담당자가 고친 새 계획을 기다리고 있어요.",
    "planChecks": "확인할 것",
    "plannedCommand": "실행할 명령",
    "planDeliverables": "만들 결과",
    "evSuperseded": "새 계획으로 바뀌었어요",
    "purposePlan": "시작하기 전에 계획을 확인해 주세요.",
    "untitledCheck": "설명이 아직 없는 검사예요",
    "ranCommand": "실행한 명령",
    "returnedBy": "{who}가 돌려보냈어요 · {reason} — 통과하지 못했어요",
    "returnedShort": "{reason} — 통과하지 못했어요",
    "returnLeader": "리더",
    "returnReviewer": "검토자",
    "recordOrder": "기록 {n}",
    "results": "결과 보기",
    "resultLocations": "결과 파일",
    "checkingKey": "◷ 검사받는 중",
    "reviewKey": "⌕ 검토 작업",
    "returnedKey": "↩ 고치러 돌아옴",
    "pendingKey": "○ 시작 전",
    "planChecklist": "확인할 것 · 검사 {checks}개 · 예정된 질문 {decisions}번",
    "planReturned": "돌려보낸 계획",
    "planUnverified": "답이 확인되지 않았어요",
    "planUnverifiedHelp": "이 답으로는 일을 시작할 수 없어요. 담당자에게 계획을 다시 올려 달라고 한 뒤 새 질문에 답해 주세요.",
    "planKeyMismatch": "이 창의 확인 키가 실행을 만들 때의 키와 달라요. 원래 실행을 만든 환경에서 대시보드를 다시 열어 주세요.",
    "planTampered": "계획 파일이 기록과 달라요",
    "planTamperedHelp": "안전을 위해 계획과 실행을 잠갔어요. 담당자에게 기록된 원본을 복구하고 계획을 다시 올려 달라고 해 주세요.",
    "planGoal": "실제로 할 일",
    "planOwns": "고칠 수 있는 파일",
    "planNeeds": "먼저 받아야 할 것",
    "planReads": "읽을 자료",
    "labelOnly": "이름·요약·검사 제목은 설명용이에요. 아래 지시와 파일, 명령을 기준으로 확인해 주세요.",
    "planIntegration": "전체 결과 검사",
    "planPromoted": "이 계획에 포함된 고정 검사",
    "planQuestions": "예정된 질문 {decisions}번 · 어디에서 물을까요?",
    "planCardChecks": "검사 {n}개 · {first}",
    "planCardDelivery": "결과 · {files}",
    "planCardQuestion": "? 여기서 물어요 · {n}번",
    "noPlannedChecks": "별도 검사가 없어요",
    "supersededNotice": "{old} 질문은 새 계획의 질문으로 바뀌었어요.",
    "supersededLink": "현재 질문 {id} 보기",
    "checkNotMet": "{title} — 통과하지 못했어요",
    "lineKinds": "선의 뜻",
    "stateKinds": "일의 상태",
    "markKinds": "표시",
    "fromTab": "{tab}에서 온 질문이에요",
    "backToTab": "← {tab}로 돌아가기",
    "endedAttempt": "완료된 시도",
    "commandScope": "실행 위치 · {cwd} / 제한 시간 · {seconds}초",
    "checkPrompt": "사람에게 물을 내용",
    "checkHost": "확인 도구 · {tool} / 기대 결과 · {expect}",
    "planItems": "전체 항목 {n}개",
    "answeredPlan": "이 계획대로 시작하기로 답했어요",
    "exitSuccess": "정상 종료 (값 {n})",
    "exitFailure": "확인이 필요해요 (값 {n})"
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
    "needsYou": "Your turn",
    "done": "Done",
    "doing": "In progress",
    "waiting": "Waiting to begin",
    "needs_you": "Your turn",
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
    "attempt": "Attempt {n} · up to {max} attempts",
    "notStarted": "Not started",
    "passed": "Finished",
    "running": "Making it",
    "retrying": "Redoing work that came back",
    "submitted": "Being checked",
    "awaiting": "Your turn",
    "held": "Waiting for the next direction",
    "exhausted": "Needs a new plan",
    "noAction": "Nothing to do here now. You’ll be told if three attempts are not enough.",
    "read": "Read and decide",
    "why": "Why you are needed",
    "verified": "Already verified",
    "unverified": "Not yet verified",
    "workerNote": "Worker note",
    "notRecorded": "Not recorded.",
    "questionOnly": "Only the question was recorded for this decision. No explanation, evidence or files were left.",
    "writeFirst": "Write an answer to send it.",
    "leaveUnanswered": "Go back without answering",
    "aboutWork": "Work details",
    "decisionRef": "Decision {id}",
    "askedBy": "Asked by: {who}",
    "workedBy": "Worked by: {who}",
    "find": "Find",
    "findHint": "Decision ID or work name",
    "findNone": "No decision or task in this flow matches “{text}”. If it belongs to another flow, switch flows above.",
    "jumpNoRun": "The flow this address points to was not found.",
    "roleLeader": "Coordinator",
    "roleWorker": "Worker",
    "roleReviewer": "Reviewer",
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
    "complete": "Everything is done",
    "unnamed": "This task",
    "handoff": "Handoff",
    "overview": "In progress {doing} · Finished {done}/{total}",
    "runOption": "{run}",
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
    "noFiles": "No files to read are recorded for this decision.",
    "goal": "Goal",
    "work": "Work",
    "review": "Review",
    "decision": "Decision",
    "handsOver": "hands over",
    "reviews": "reviewed by",
    "waitsForDecision": "waits for a decision",
    "towardGoal": "toward the goal",
    "fit": "Fit to view",
    "zoomIn": "Zoom in",
    "zoomOut": "Zoom out",
    "mapHelp": "Drag to move · + − zoom · 0 fit",
    "firstPass": "1 attempt",
    "finishedAttempts": "{n} attempts",
    "lineLegend": "Solid → delivered · dashed ⇢ waiting · dotted ↶ review",
    "unusedAttempts": "Up to {max} attempts available",
    "home": "To do and log",
    "graph": "Graph",
    "nothingTitle": "Nothing needs your answer",
    "doingNow": "In progress now",
    "idle": "Nothing is in progress. Work appears here when the leader session starts the next task.",
    "log": "What happened",
    "logEmpty": "Nothing has been recorded yet.",
    "filterEmpty": "No entries match.",
    "filterAll": "All",
    "filterMine": "Your turn",
    "filterReturned": "Came back",
    "onlyNode": "Showing only “{title}”",
    "showAll": "Show all",
    "evStarted": "The run record was created",
    "evPlanned": "Plan posted",
    "evReplanned": "Plan changed · revision {rev}",
    "evRunning": "attempt {n} in progress",
    "evSubmitted": "attempt {n} submitted · waiting to be checked",
    "evPassed": "attempt {n} passed",
    "evReturned": "attempt {n} came back",
    "evReplan": "attempt {n} came back · no attempts left, a new plan is needed",
    "evNeedsYou": "Attempt {n} · Your turn",
    "evHeld": "attempt {n} · put on hold",
    "evReopened": "reopened",
    "evAsked": "asked",
    "evAnswered": "Answered the question",
    "evFinalPassed": "Final check passed",
    "evFinalFailed": "Final check failed",
    "evLearned": "A lesson was recorded",
    "checksPassed": "{n} checks passed",
    "checksFailed": "✕ In attempt {n}, “{names}” did not pass",
    "rowDetails": "Checks and notes",
    "checkPassed": "passed",
    "checkFailed": "failed",
    "checkTimedOut": "timed out",
    "exitCode": "Command return value {n}",
    "seconds": "{n}s",
    "gateRun": "checked by the leader session",
    "workerRun": "checked by the worker session",
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
    "runOptionNeeds": "{run}",
    "since": "since {time}",
    "returnTimes": "Came back {n} times before",
    "allDone": "This flow is complete",
    "answerHere": "Decision {id} · Read and decide",
    "lineOpen": "handed over",
    "lineClosed": "not handed over yet",
    "lineWaiting": "Waiting for your turn",
    "lineReturned": "Waiting for handoff",
    "lineReview": "reviews",
    "tries": "attempt {n}/{max}",
    "closeDetails": "Close details",
    "mapDirection": "Left to right",
    "checkMet": "✓ {title}",
    "workingHere": "Worker session in progress",
    "offLeft": "← Left",
    "offRight": "Right →",
    "offTop": "↑ Above",
    "offBottom": "↓ Below",
    "offCount": "{direction}: {n}",
    "visibleCards": "{summary} · Visible: {n}",
    "graphEdges": "Go to work beyond this view",
    "history": "Attempts and checks for this work",
    "currentAttempt": "Current attempt",
    "earlierAttempt": "Earlier attempt",
    "gateReview": "Review this decision’s record before answering.",
    "noAttemptChecks": "No check results are recorded for this attempt yet.",
    "previousReason": "Earlier return reason: {reason}",
    "offWorking": " · working {n}",
    "offNeeds": " · Your turn {n}",
    "workerDetails": "Worker · inputs · outputs",
    "attemptRecord": "Checks and notes for attempt {n}",
    "earlierFailure": "✕ In attempt {n}, “{reason}” did not pass",
    "findDecisionHint": "{id} or work name",
    "scopeCheck": "Only assigned files were changed",
    "noCurrentChecks": "There are no check results for the current attempt yet.",
    "revisionHint": "Describe what to fix to send it back",
    "nodeRef": "Work {id}",
    "answeredApproval": "Answered: accept the result",
    "answeredRevision": "Answered: request changes",
    "answeredRejection": "Answered: reject the result",
    "lineSampleOpen": "Handoff",
    "lineSampleClosed": "Handoff pending",
    "lineSampleReview": "Review",
    "attemptShort": "Attempt {n}",
    "earlierHistory": "Earlier attempt history",
    "failureUnknownAttempt": "✕ In the recorded attempt, “{names}” did not pass",
    "modelName": "Model {model}",
    "blindApproval": "Ask the agent session in chat to show the result, or send it back with a note about what to change.",
    "showDiagram": "Show diagram",
    "showFlowList": "Show readable list",
    "mapDown": "Top to bottom",
    "pastReturn": "Earlier attempt {n} returned",
    "nothingToJudge": "There is nothing here to judge by",
    "nothingToJudgeBody": "No file or current check result is recorded. Send it back to request the result, or ask the agent session in chat.",
    "confirmBlind": "I choose to accept without a file or check result",
    "blindHint": "To accept without evidence, confirm the statement above.",
    "acceptBlind": "Accept without evidence",
    "minZoom": "Minimum zoom for readable text",
    "readGateHint": "Open a file or the evidence first",
    "approveEffect": "Your acceptance is sent to the leader session",
    "revisionEffect": "Your requested changes are sent to the leader session",
    "answerEffect": "Your answer is sent to the leader session",
    "retryEffect": "The next attempt is {n} of {max}",
    "decisionWork": "About · {title}",
    "fitAll": "Fit all",
    "readScale": "Readable size",
    "planSummary": "Work: {work} · Reviews: {review} · Decisions: {decision}",
    "planStart": "Start",
    "planStartEffect": "Start lets the coordinator begin this plan’s work.",
    "planBackEffect": "Send the changes to the coordinator.",
    "planSentBack": "The plan was sent back",
    "planWaiting": "Review the plan",
    "planSentNote": "Your requested changes",
    "planWaitingRevision": "Waiting for the coordinator’s revised plan.",
    "planChecks": "Planned checks",
    "plannedCommand": "Planned command",
    "planDeliverables": "Deliverables",
    "evSuperseded": "Replaced by a new plan",
    "purposePlan": "Review the plan before work starts.",
    "untitledCheck": "A check without a description",
    "ranCommand": "Command run",
    "returnedBy": "Returned by {who} · {reason} — did not pass",
    "returnedShort": "{reason} — did not pass",
    "returnLeader": "Leader",
    "returnReviewer": "Reviewer",
    "recordOrder": "Record {n}",
    "results": "View results",
    "resultLocations": "Result files",
    "checkingKey": "◷ Being checked",
    "reviewKey": "⌕ Review work",
    "returnedKey": "↩ Returned for changes",
    "pendingKey": "○ Not started",
    "planChecklist": "Review · Checks: {checks} · Planned questions: {decisions}",
    "planReturned": "Returned plan",
    "planUnverified": "Your answer could not be verified",
    "planUnverifiedHelp": "This answer cannot start work. Ask the coordinator to post the plan again, then answer the new question.",
    "planKeyMismatch": "This window’s verification key differs from the run’s original key. Reopen the dashboard in the original environment.",
    "planTampered": "The plan file differs from its record",
    "planTamperedHelp": "The plan and execution are locked. Ask the coordinator to restore the recorded original and post the plan again.",
    "planGoal": "Actual instruction",
    "planOwns": "Files allowed to change",
    "planNeeds": "Required inputs",
    "planReads": "Files to read",
    "labelOnly": "Names, summaries and check titles are labels only. Review the instructions, files and commands below.",
    "planIntegration": "Integration checks",
    "planPromoted": "Fixed checks in this plan",
    "planQuestions": "Planned questions: {decisions} · Where will you be asked?",
    "planCardChecks": "Checks: {n} · {first}",
    "planCardDelivery": "Delivers · {files}",
    "planCardQuestion": "? You will be asked here · {n}",
    "noPlannedChecks": "No separate checks",
    "supersededNotice": "Question {old} was replaced by a new plan’s question.",
    "supersededLink": "View current question {id}",
    "checkNotMet": "{title} — did not pass",
    "lineKinds": "Lines",
    "stateKinds": "Task states",
    "markKinds": "Marks",
    "fromTab": "Question opened from {tab}",
    "backToTab": "← Back to {tab}",
    "endedAttempt": "Completed attempt",
    "commandScope": "Directory · {cwd} / Time limit · {seconds}s",
    "checkPrompt": "Question for you",
    "checkHost": "Tool · {tool} / Expected result · {expect}",
    "planItems": "Items: {n}",
    "answeredPlan": "Agreed to start with this plan",
    "exitSuccess": "Completed successfully (value {n})",
    "exitFailure": "Needs checking (value {n})"
  }
};
// UI_STRINGS_END

export function sameRun(a, b) { return a?.project === b?.project && a?.run === b?.run; }
export function purposeWording(purpose, language = 'en') {
  const keys = {plan_approval:'purposePlan', human_check:'purposeReview', review:'purposeReview', lane3:'purposeAuthorization', authorization:'purposeAuthorization', trajectory:'purposeTrajectory', hold:'purposeHold', direction:'purposeDirection', information:'purposeInformation'};
  const key = Object.hasOwn(keys, purpose) ? keys[purpose] : 'purposeNeutral';
  return STRINGS[language][key];
}
export function purposeAction(purpose, language = 'en', failed = []) {
  if (purpose === 'hold' || failed.length) return STRINGS[language].acceptAnyway;
  const keys = {plan_approval:'planStart', lane3:'allow', authorization:'allow', human_check:'accept', review:'accept', trajectory:'accept', hold:'continue'};
  return STRINGS[language][Object.hasOwn(keys, purpose) ? keys[purpose] : 'confirmChoice'];
}
export function nothingToJudge(view, decision) {
  const node = view?.nodes?.find(n => n.id === decision.node);
  return decision.purpose !== 'plan_approval' && !['direction','information'].includes(decision.kind) && !decision.files?.length &&
    !view?.timeline?.some(r => r.kind === 'attempt' && r.node === decision.node && r.attempt === node?.attempts && r.checks?.length);
}
export function canApprove(session) {
  if (session?.purpose === 'plan_approval') return true;
  if (session?.nothingToJudge && !session.blindConfirmed) return false;
  return !!session && (!(session.purpose === 'lane3' || session.purpose === 'authorization' ||
    session.kind === 'authorization' || session.purpose === 'hold' || session.failed?.length || session.decision?.files?.length || session.decision?.has_evidence) || session.detailsOpened || (!(session.purpose === 'hold' || session.failed?.length) && session.fileOpened));
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
  const update = d => { const empty = nothingToJudge(view, d); if (empty !== session.nothingToJudge) session.blindConfirmed = false; session.nothingToJudge = empty; session.decision = d; session.purpose = d.purpose; session.kind = d.kind; session.failed = d.failed || []; };
  const controller = {
    get session() { return session; },
    get requiresDetails() { return !!session && !canApprove({...session, nothingToJudge:false, detailsOpened:false, fileOpened:false}); },
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
    confirmBlind(value) { if (current()) session.blindConfirmed = !!value; },
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
// Below this the words on a card stop being readable, so a larger graph scrolls instead of shrinking further.
export const MIN_FIT_SCALE = 2 / 3;
export function edgeRelationLabel(edge, language = 'en') {
  const words = STRINGS[language];
  if (edge.relation === 'toward_goal') return words.towardGoal;
  if (edge.relation === 'reviews') return words.reviews;
  if (edge.relation === 'waits_for_decision') return words.waitsForDecision;
  return words.handsOver + (edge.label ? ': ' + edge.label : '');
}
// Text on a line has one meaning: the name of what is handed over. Reviews and decisions are shown by the line itself.
export function edgeChipText(edge) {
  return (edge.relation || 'hands_over') === 'hands_over' && edge.label ? edge.label : '';
}
export function displayState(node, decisions = []) {
  if (decisions.some(d => d.node === node.id)) return 'awaiting';
  if (node.status === 'passed' || node.answered) return 'passed';
  if (node.status === 'running') return node.attempts > 1 ? 'retrying' : 'running';
  if (['submitted','unverified'].includes(node.status)) return 'submitted';
  if (['replan','exhausted'].includes(node.status)) return 'exhausted';
  if (node.status === 'rejected') return 'returned';
  if (['held','awaiting_approval'].includes(node.status)) return 'held';
  return 'notStarted';
}
export function statusGlyph(state) {
  return {passed:'✓', running:'▶', retrying:'↪', submitted:'◷', awaiting:'◆', returned:'↩', notStarted:'○', exhausted:'!', held:'Ⅱ'}[state];
}
export function checkTitle(check, language = 'en') {
  return (!check.title || check.title === check.id) && check.id === 'scope' ? STRINGS[language].scopeCheck : check.title || STRINGS[language].untitledCheck;
}
export function checkWording(check, language = 'en', attempt = check.attempt) {
  const key = check.result === 'passed' ? 'checkMet' : 'checkNotMet';
  return STRINGS[language][key].replace('{title}', checkTitle(check, language)).replace('{names}', checkTitle(check, language)).replace('{n}', attempt);
}
// Every clipped card belongs to one nearest boundary, including diagonal corners.
export function offscreenDirection(rect, width, height) {
  const outside = [['offLeft',-rect.x-rect.width],['offRight',rect.x-width],['offTop',-rect.y-rect.height],['offBottom',rect.y-height]].filter(([,gap])=>gap>=0);
  if(outside.length)return outside.sort((a,b)=>a[1]-b[1])[0][0];
  const gaps = [['offLeft', -rect.x], ['offRight', rect.x + rect.width - width], ['offTop', -rect.y], ['offBottom', rect.y + rect.height - height]].filter(([,gap]) => gap > .5);
  return gaps.sort((a,b) => a[1]-b[1])[0]?.[0] || null;
}
const textWidth = (text, wide, narrow) => Array.from(text || '').reduce((sum, c) => sum + (c.charCodeAt(0) > 0x2e80 ? wide : narrow), 0);
export function fitScale(bounds, width, height, mobile = false) {
  const available = Math.min(width / bounds.width, height / bounds.height);
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
export function forwardEdges(edges) {
  return edges.map(e => e.relation === 'reviews' ? {...e, from:e.to, to:e.from} : e);
}
export function layeredLayout(nodes, edges, decisions = [], sort = true, options = {}) {
  const byId = new Map(nodes.map(n => [n.id, n])), vertices = new Map(), links = [];
  const routes = forwardEdges(edges).filter(e => byId.has(e.from) && byId.has(e.to)).map((e,index) => {
    const waiting = decisions.find(d => d.node === e.from);
    return {...e,index,bundle:index,text:edgeChipText(e),chip:null,gateState:waiting?'waiting_for_you':e.gate==='returned'?'closed':e.gate||'closed',decision:waiting?.id};
  });
  const parents = id => routes.filter(e => e.to === id).map(e => e.from);
  const depths = new Map();
  const depth = (id, seen = new Set()) => {
    if (depths.has(id)) return depths.get(id);
    if (seen.has(id)) return 0;
    const next = new Set(seen); next.add(id);
    const d = Math.max(0,...parents(id).filter(p => !next.has(p)).map(p => depth(p,next)+1));
    depths.set(id,d); return d;
  };
  const layers = [];
  for (const n of nodes) {
    const d = depth(n.id); vertices.set(n.id,{id:n.id,layer:d,node:n}); (layers[d] ||= []).push(n.id);
  }
  // A long edge occupies a real slot in every intervening layer, not an outside detour.
  for (const r of routes) {
    r.chain = [r.from];
    for (let d=depth(r.from)+1; d<depth(r.to); d++) {
      const id = `\u0000${r.index}:${d}`; vertices.set(id,{id,layer:d,dummy:true,route:r.index}); layers[d].push(id); r.chain.push(id);
    }
    r.chain.push(r.to); r.skip = r.chain.length>2;
    r.chain.slice(1).forEach((id,i) => links.push({from:r.chain[i],to:id,route:r.index}));
  }
  const rank = () => new Map(layers.flatMap(ids => ids.map((id,i) => [id,i])));
  const crossings = () => {
    const ranks=rank(); let count=0;
    links.forEach((a,i)=>links.slice(i+1).forEach(b=>{
      if(vertices.get(a.from).layer===vertices.get(b.from).layer && (ranks.get(a.from)-ranks.get(b.from))*(ranks.get(a.to)-ranks.get(b.to))<0)count++;
    })); return count;
  };
  let best=layers.map(ids=>[...ids]),bestCost=crossings();
  if(sort)for(let sweep=0;sweep<12;sweep++) {
    const order=layers.map((_,i)=>i);if(sweep%2)order.reverse();
    for(const d of order) {
      const ranks=rank(), score=id=>{
        const near=links.filter(e=>sweep%2?e.from===id:e.to===id).map(e=>ranks.get(sweep%2?e.to:e.from));
        return near.length?near.reduce((a,b)=>a+b,0)/near.length:ranks.get(id);
      };
      layers[d].sort((a,b)=>score(a)-score(b)||ranks.get(a)-ranks.get(b));
    }
    const cost=crossings();if(cost<bestCost){bestCost=cost;best=layers.map(ids=>[...ids]);}
  }
  layers.splice(0,layers.length,...best);
  const widths=layers.map(ids=>Math.max(264,...ids.filter(id=>byId.has(id)).map(id=>Math.min(280,Math.ceil(textWidth(byId.get(id).title,18,9))+40))));
  for(const v of vertices.values()) {
    v.width=widths[v.layer];
    v.height=v.dummy?44:Math.max(v.node.planned_checks || v.node.deliverables ? 236 : 120,40+14*Math.max(links.filter(e=>e.from===v.id).length,links.filter(e=>e.to===v.id).length))+Math.max(0,Math.ceil(textWidth(v.node.title,18,9)/(v.width-40))-1)*26;
  }
  const gap=18,margin=20;
  const total=ids=>ids.reduce((s,id)=>s+vertices.get(id).height,0)+Math.max(0,ids.length-1)*gap;
  const tallest=Math.max(0,...layers.map(total));
  for(const ids of layers){let y=margin+(tallest-total(ids))/2;for(const id of ids){vertices.get(id).y=y;y+=vertices.get(id).height+gap;}}
  // Align connected rows while keeping the chosen order and each dummy's clearance.
  if(sort)for(let sweep=0;sweep<7;sweep++) {
    const order=layers.map((_,d)=>d);if(sweep%2)order.reverse();
    for(const d of order) {
      const ids=layers[d];let floor=margin;
      for(const id of ids){const v=vertices.get(id),near=links.filter(e=>sweep%2?e.from===id:e.to===id).map(e=>vertices.get(sweep%2?e.to:e.from));
        const centre=near.length?near.reduce((s,n)=>s+n.y+n.height/2,0)/near.length:v.y+v.height/2;
        v.y=Math.max(floor,centre-v.height/2);floor=v.y+v.height+gap;
      }
      let ceiling=margin+tallest;
      for(const id of [...ids].reverse()){const v=vertices.get(id);v.y=Math.min(v.y,ceiling-v.height);ceiling=v.y-gap;}
    }
  }
  const channels=layers.slice(1).map((_,d)=>links.filter(e=>vertices.get(e.from).layer===d));
  let x=margin;
  layers.forEach((ids,d)=>{for(const id of ids)vertices.get(id).x=x;x+=widths[d]+Math.max(108,52+(channels[d]?.length||0)*18);});
  // Distinct horizontal ordinates prevent a target lead from joining an unrelated source lead.
  const usedY=[];
  const ordinate=(ideal,low,high,edge,channels)=>{
    for(let step=0;step<10000;step++){
      const y=ideal+(step%2?1:-1)*Math.ceil(step/2)*14;
      if(y>=low && y<=high && usedY.every(n=>n.edge===edge||!n.channels.some(c=>channels.includes(c))||Math.abs(n.y-y)>=14)){usedY.push({y,edge,channels});return y;}
    }
    throw new Error('Graph ports exceed card capacity');
  };
  for(const ids of layers)for(const id of ids){
    const v=vertices.get(id);
    if(v.dummy){v.port=ordinate(v.y+v.height/2,v.y+2,v.y+v.height-2,v.route,[v.layer-1,v.layer]);continue;}
    for(const side of ['start','end']){
      const rs=routes.filter(r=>r[side==='start'?'from':'to']===id);
      const neighbour=r=>vertices.get(r.chain[side==='start'?1:r.chain.length-2]);
      rs.sort((a,b)=>{const p=neighbour(a),q=neighbour(b);return p.y+p.height/2-q.y-q.height/2||a.index-b.index;});
      rs.forEach((r,i)=>r[side]={x:v.x+(side==='start'?v.width:0),y:ordinate(v.y+v.height*(i+1)/(rs.length+1),v.y+12,v.y+v.height-12,r.index,[v.layer-(side==='end'?1:0)])});
    }
  }
  const segmentCross=(a,b,c,d)=>a.y===b.y&&c.x===d.x&&c.x>Math.min(a.x,b.x)&&c.x<Math.max(a.x,b.x)&&a.y>Math.min(c.y,d.y)&&a.y<Math.max(c.y,d.y);
  const parts=[];
  channels.forEach((channel,d)=>{
    const right=vertices.get(layers[d][0]).x+widths[d],next=vertices.get(layers[d+1][0]).x;
    const pieces=channel.map(e=>{const r=routes[e.route],a=vertices.get(e.from),b=vertices.get(e.to);return {route:r.index,a:a.dummy?{x:a.x+a.width,y:a.port}:r.start,b:b.dummy?{x:b.x,y:b.port}:r.end};});
    const points=(p,i)=>{const track=right+26+(next-right-52)*(i+1)/(pieces.length+1);return [p.a,{x:track,y:p.a.y},{x:track,y:p.b.y},p.b];};
    const cost=()=>{let n=0;pieces.forEach((p,i)=>pieces.slice(i+1).forEach((q,j)=>{const a=points(p,i),b=points(q,i+1+j);for(let k=1;k<4;k++)for(let l=1;l<4;l++)if(segmentCross(a[k-1],a[k],b[l-1],b[l])||segmentCross(b[l-1],b[l],a[k-1],a[k]))n++;}));return n;};
    pieces.sort((a,b)=>(a.b.y-a.a.y)-(b.b.y-b.a.y)||a.route-b.route);
    for(let sweep=0;sweep<6;sweep++)for(let i=0;i<pieces.length-1;i++){const before=cost();[pieces[i],pieces[i+1]]=[pieces[i+1],pieces[i]];if(cost()>=before)[pieces[i],pieces[i+1]]=[pieces[i+1],pieces[i]];}
    pieces.forEach((p,i)=>parts.push({...p,layer:d,points:points(p,i)}));
  });
  for(const r of routes){
    const points=parts.filter(p=>p.route===r.index).sort((a,b)=>a.layer-b.layer).flatMap(p=>p.points).filter((p,i,a)=>!i||p.x!==a[i-1].x||p.y!==a[i-1].y);
    r.points=points.filter((p,i,a)=>!i||i===a.length-1||!((a[i-1].x===p.x&&p.x===a[i+1].x)||(a[i-1].y===p.y&&p.y===a[i+1].y)));
  }
  const positions=Object.fromEntries([...vertices].filter(([,v])=>!v.dummy).map(([id,v])=>[id,{x:v.x,y:v.y,width:v.width,height:v.height,depth:v.layer,layer:v.layer}]));
  const cardRects=Object.entries(positions).map(([id,p])=>({id,...p})),chips=[];
  const overlaps=(a,b)=>a.x<b.x+b.width+8&&a.x+a.width+8>b.x&&a.y<b.y+b.height+8&&a.y+a.height+8>b.y;
  for(const r of routes){
    if(!r.text)continue;
    const width=Math.ceil(textWidth(r.text,14,7.5))+20,height=26;
    const segments=r.points.slice(1).map((b,i)=>[r.points[i],b]).filter(([a,b])=>a.y===b.y&&b.x-a.x>width+8).sort((a,b)=>(b[1].x-b[0].x)-(a[1].x-a[0].x));
    for(const [a,b] of segments){const chip={x:(a.x+b.x-width)/2,y:a.y-height/2,width,height,first:r.index,key:String(r.index)};
      if(cardRects.some(c=>overlaps(chip,c))||chips.some(c=>overlaps(chip,c)))continue;
      const blocked=routes.some(other=>other!==r&&other.points.slice(1).some((q,i)=>{const p=other.points[i];return Math.max(p.x,q.x)>chip.x-4&&Math.min(p.x,q.x)<chip.x+width+4&&Math.max(p.y,q.y)>chip.y-4&&Math.min(p.y,q.y)<chip.y+height+4;}));
      if(!blocked){r.chip=chip;chips.push(chip);break;}
    }
  }
  return {positions,layers:layers.map(ids=>ids.filter(id=>byId.has(id))),order:layers.flat().filter(id=>byId.has(id)),routes,chips,cardRects,
    terminals:nodes.filter(n=>!routes.some(r=>r.from===n.id)).map(n=>n.id),
    bounds:{width:Math.max(100,...cardRects.map(p=>p.x+p.width+margin)),height:tallest+margin*2},vertical:false};
}

export function roundedRoute(points, radius = 5) {
  const pts=points.filter((p,i)=>!i||p.x!==points[i-1].x||p.y!==points[i-1].y);
  if(!pts.length)return '';
  let path=`M${pts[0].x} ${pts[0].y}`;
  for(let i=1;i<pts.length-1;i++){
    const a=pts[i-1],b=pts[i],c=pts[i+1],before=Math.hypot(b.x-a.x,b.y-a.y),after=Math.hypot(c.x-b.x,c.y-b.y),r=Math.min(radius,before/2,after/2);
    if((a.x===b.x&&b.x===c.x)||(a.y===b.y&&b.y===c.y)){path+=` L${b.x} ${b.y}`;continue;}
    path+=` L${b.x+(a.x-b.x)*r/before} ${b.y+(a.y-b.y)*r/before} Q${b.x} ${b.y} ${b.x+(c.x-b.x)*r/after} ${b.y+(c.y-b.y)*r/after}`;
  }
  const end=pts.at(-1);return path+` L${end.x} ${end.y}`;
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
let chosen = null, projects = [], view = null, fingerprint = '', mode = 'flow', selected = null;
let queuedRefresh = false;
let timer = 0, loading = false, generation = 0, renderer = null;
const decisionController = createDecisionController();
let decisionUI = null, decisionNotice = '', cameFrom = 'flow';

async function api(path, body, text = false) {
  const response = await fetch(path, {method: body ? 'POST' : 'GET', headers: {'X-GF-Token': token, ...(body ? {'Content-Type':'application/json'} : {})}, ...(body ? {body:JSON.stringify(body)} : {})});
  if (!response.ok) { const err = new Error('request'); err.status = response.status; throw err; }
  return text ? response.text() : response.json();
}
function query(route, extra = {}, target = chosen) { return route + '?' + new URLSearchParams({project:target.project, run:target.run, ...extra}); }
let replacementDecision = null;
function notice(key, retry = false) { const box = $('notice'); clear(box); box.hidden = !key; if (key) box.append(el('span', STRINGS[language][key] === undefined ? key : t(key))); if (retry) box.append(button(t('retry'), () => refresh(true))); if(key && replacementDecision)box.append(button(t('supersededLink',{id:replacementDecision}),()=>openDecision(replacementDecision),'primary')); }
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
  return [...new Set([role ? t(role) : '', sessionName(actor?.session)].filter(Boolean))].join(' · ');
}
// The log groups dates separately so every timestamp has the same width.
function clock(stamp, seconds = false) {
  const time = stamp ? new Date(stamp) : null; if (!time || isNaN(time)) return '';
  return time.toLocaleTimeString(language, {hour:'2-digit', minute:'2-digit', ...(seconds?{second:'2-digit'}:{}), hour12:false});
}
// An id the agent also says. Pressing it copies the words to paste back into the chat.
function refChip(id, say, decision = false) {
  const chip = button(t(decision ? 'decisionRef' : 'nodeRef', {id}), async event => {
    event.stopPropagation();
    // Said once; the next refresh puts back whatever the page has to report.
    try { await navigator.clipboard.writeText(say); notice(t('copied', {text:say})); } catch { notice(t('copyFailed', {text:say})); }
  }, 'ref' + (decision ? ' decision-ref' : ''));
  chip.title = t('copyHint'); chip.setAttribute('aria-label', `${id}. ${t('copyHint')}`); return chip;
}
function workedBy(n) { return [n.worker?.model ? t('modelName',{model:n.worker.model}) : '', sessionName(n.session)].filter(Boolean).join(' · '); }
function decisionHeading(parent, d, tag) {
  const reference = el('p', undefined, 'ref-line'); reference.append(refChip(d.id, `${d.id} · ${decisionTitle(d)}`, true));
  if (d.node) reference.append(refChip(d.node, `${d.node} · ${decisionTitle(d)}`));
  const asker = who(d.asked_by);
  const origin=[asker?t('askedBy',{who:asker}):'',clock(d.asked)].filter(Boolean).join(' · ');
  if(origin)reference.append(el('span',origin));
  parent.append(reference, el('p', t('decisionWork',{title:decisionTitle(d)}), 'decision-work'));
  parent.append(el(tag, question(d) || purposeWording(d.purpose,language), 'decision-question'));
  if (d.purpose === 'trajectory') textList(parent, (d.trajectory_reasons || []).map(key => t(key)));
}
function needs(node) { return view.decisions.some(d => d.node === node.id); }
function status(node) { return t(displayState(node, view.decisions)); }
function attempts(node) { return node.status==='passed' && node.attempts ? t(node.attempts===1?'firstPass':'finishedAttempts',{n:node.attempts}) : t(node.attempts?'attempt':'unusedAttempts', {n:node.attempts||0, max:node.max_attempts||3}); }
function card(heading, body, paper = false) { const c = el('div', undefined, 'card' + (paper ? ' paper' : '')); c.append(el('p', heading, 'eyebrow')); if (body) c.append(el('p', body)); return c; }
function textList(parent, items, empty = 'notRecorded') { const list = el('ul'); if (!items.length) list.append(el('li', t(empty))); else items.forEach(text => list.append(el('li', text))); parent.append(list); }
function wording(text, tag = 'span') {
  const root=el(tag), split=text.indexOf('✕');
  if(split<0)root.textContent=text;
  else {if(split)root.append(el('span',text.slice(0,split)));root.append(el('span','✕','failure-mark'),el('span',text.slice(split+1)));}
  return root;
}
function failedBlock(parent, d) {
  if (!d.failed?.length) return;
  const failed = card(t('failed')); failed.classList.add('failed');
  textList(failed, d.failed.map(text => text === STRINGS.en.untitledFailure ? t('untitledFailure') : checkWording({title:text,result:'failed'}, language, view.nodes.find(n=>n.id===d.node)?.attempts))); parent.append(failed);
}
function decisionCard(d) {
  const c = el('div', undefined, 'card paper'); decisionHeading(c, d, 'h3'); failedBlock(c, d); if (d.context.why) c.append(el('p', d.context.why));
  c.append(button(t('read'), () => openDecision(d.id), 'primary')); return c;
}
function handoffsCard(key, rows, direction) {
  const c = card(t(key)); const list = el('ul');
  if (!rows.length) c.append(el('p', t('noHandoffs')));
  for (const row of rows) list.append(el('li', `${label(row.label)} · ${t(direction)} ${otherTitle(row.other_title)} · ${t(row.delivered ? 'delivered' : 'notDelivered')}`));
  c.append(list); return c;
}
function plannedChecks(parent, checks) {
  const list = el('ul', undefined, 'checks planned-checks');
  for (const c of checks || []) {
    const item = el('li'); item.append(el('strong', checkTitle(c, language)));
    if (c.command) { item.append(el('p', t('plannedCommand'), 'muted'), el('pre', c.command, 'planned-command'), el('p', t('commandScope', {cwd:c.cwd || '.', seconds:c.timeout_s || 600}), 'muted')); }
    if (c.prompt) item.append(el('p', t('checkPrompt') + ' · ' + c.prompt));
    if (c.type === 'host') item.append(el('p', t('checkHost', c)));
    list.append(item);
  }
  if (!list.children.length) list.append(el('li', t('noPlannedChecks')));
  parent.append(list);
}
function planFacts(parent, node) {
  parent.append(el('p', t('labelOnly'), 'muted'), el('h3', t('planGoal')), el('p', node.goal || node.summary || ''));
  for (const [key, rows] of [['planOwns',node.owns || []],['planReads',node.reads || []],['planDeliverables',node.deliverables || node.declared_outputs || []]]) {
    parent.append(el('h3', t(key))); textList(parent, rows);
  }
  parent.append(el('h3', t('planNeeds')));
  textList(parent, (node.needs || []).map(n => `${n.artifact} · ${t('from')} ${otherTitle(view.nodes.find(p => p.id === n.from)?.title || n.from)} (${n.from})`));
  parent.append(el('h3', t('planChecks'))); plannedChecks(parent, node.planned_checks);
}
let planBanner = null;
function planAttention(box) {
  const approval = view.plan_approval;
  const blocked = view.plan_error || view.key_mismatch || approval && !(approval.status === 'answered' && approval.verified && approval.outcome === 'approved');
  if (!blocked) { planBanner = null; return false; }
  box.hidden = false; box.classList.add('plan-banner');
  const key = JSON.stringify([chosen, approval?.id, approval?.status, view.plan_error, view.key_mismatch]);
  if (planBanner?.key === key && box.firstElementChild) {
    box.querySelector('.plan-summary').textContent = t('planSummary', view.plan_counts);
    return true;
  }
  clear(box);
  const unverified = view.key_mismatch || approval?.status === 'answered' && !approval.verified;
  const heading = el('h2', view.plan_error ? t('planTampered') : unverified ? t('planUnverified') : approval.status === 'open' ? approval.question : t('planSentBack'));
  heading.id = 'plan-question'; box.setAttribute('aria-labelledby', heading.id);
  box.append(heading, el('p', t('planSummary', view.plan_counts), 'plan-summary'));
  planBanner = {key};
  if (view.plan_error || unverified) {
    box.append(el('p', t(view.plan_error ? 'planTamperedHelp' : 'planUnverifiedHelp')));
    if (view.key_mismatch) box.append(el('p', t('planKeyMismatch')));
    return true;
  }
  if (approval.status !== 'open') {
    box.append(el('p', t('planSentNote'), 'eyebrow'), el('p', approval.answer || ''), el('p', t('planWaitingRevision'), 'muted'));
    return true;
  }
  const facts = el('div', undefined, 'plan-overview');
  facts.append(el('p', t('planChecklist', view.plan_counts), 'eyebrow'), el('p', view.goal), el('p', t('labelOnly'), 'muted'));
  if (view.planned_questions?.length) {
    const qs = el('details'); qs.open = !!rowOpen.get('plan-questions'); qs.addEventListener('toggle',()=>rowOpen.set('plan-questions',qs.open));
    qs.append(el('summary', t('planQuestions', view.plan_counts)));
    for (const q of view.planned_questions) {
      const line=el('p'); line.append(button(`${otherTitle(view.nodes.find(n=>n.id===q.node)?.title)} · ${purposeWording(q.kind,language)}`,()=>selectNode(q.node),'link'),el('span',' · '+q.question)); qs.append(line);
    }
    facts.append(qs);
  }
  const runChecks=el('div',undefined,'plan-run-checks');
  for (const [key, checks] of [['planIntegration',view.integration_checks],['planPromoted',view.promoted_checks]]) if (checks?.length) { const group=el('section'); group.append(el('h3',t(key))); plannedChecks(group,checks); runChecks.append(group); }
  if(runChecks.children.length) facts.append(runChecks);
  if (view.constraints?.length) textList(facts,view.constraints);
  box.append(facts);
  const session = decisionController.open(approval.id);
  const actions = el('div', undefined, 'plan-actions'), start = button(t('planStart'), () => send('approved'), 'primary');
  const startGroup = el('div'); startGroup.append(start, el('p', t('planStartEffect'), 'muted'));
  const backGroup = el('div'), changes = el('details',undefined,'plan-change-form'), label = el('label', t('backReason')), input = el('textarea');
  input.id = 'plan-changes'; label.htmlFor = input.id; input.rows = 2; input.value = session?.draft || '';
  const back = button(t('sendBack'), () => send('revision_requested'));
  const message = el('p', undefined, 'muted'); message.setAttribute('role', 'status');
  const update = () => { start.disabled = !decisionController.canSubmit('approved'); back.disabled = !decisionController.canSubmit('revision_requested'); input.disabled = !!session?.busy; $('picker').disabled = !!session?.busy; };
  input.addEventListener('input', () => { decisionController.setDraft(input.value); update(); });
  async function send(outcome) {
    const request = decisionController.buildRequest(outcome, input.value); if (!request) return;
    update(); let error = null;
    try { await api('/api/answer', request); } catch (e) { error = e; }
    const result = decisionController.onResult(request, error);
    message.textContent = t(result.notice); update();
    if (result.refresh) refresh(true);
  }
  changes.append(el('summary',t('sendBack')), label, input, back); backGroup.append(changes, el('p', t('planBackEffect'), 'muted'));
  actions.append(backGroup, startGroup); box.append(actions, message); heading.append(refChip(approval.id, approval.question, true)); update();
  return true;
}
function attention() {
  const planBox = $('attention');
  if (planAttention(planBox)) return;
  planBox.classList.remove('plan-banner'); planBox.removeAttribute('aria-labelledby');
  const box = $('attention'); clear(box); box.hidden = !view.decisions.length;
  box.setAttribute('aria-label', t('yourTurn'));
  if (box.hidden) return;
  const heading = el('div', undefined, 'attention-heading');
  heading.append(el('span', t('yourTurn')), el('strong', String(view.decisions.length)));
  const items = el('div', undefined, 'attention-items');
  for (const d of view.decisions) {
    const item = el('div', undefined, 'attention-item'), text = el('div'), reference = el('div', undefined, 'ref-line');
    reference.append(refChip(d.id, `${d.id} · ${d.node_title || question(d)}`, true));
    if (d.node) reference.append(refChip(d.node, `${d.node} · ${d.node_title}`));
    if (d.node_title) reference.append(el('span', d.node_title));
    text.append(reference, el('p', question(d) || purposeWording(d.purpose, language)));
    item.append(text, button(t('read'), () => openDecision(d.id), 'primary')); items.append(item);
  }
  box.append(heading, items);
}
let panelFingerprint='',panelNode=null;
function panel() {
  const p = $('panel');
  const signature=JSON.stringify([selected,view.nodes.find(n=>n.id===selected),view.decisions.filter(d=>d.node===selected),view.timeline.filter(r=>r.node===selected)]);
  if(signature===panelFingerprint)return;
  panelFingerprint=signature;
  const scroll=selected===panelNode?p.scrollTop:0;panelNode=selected;p.onscroll=null;clear(p);
  const node = view.nodes.find(n => n.id === selected);
  p.hidden = !node; $('flow').classList.toggle('has-selection', !!node);
  if (!node) return;
  p.setAttribute('aria-label', title(node));
  const close = button('×', () => {
    const id = selected; selectNode(id);
    [...document.querySelectorAll('.node-card')].find(e => e.dataset.node === id)?.querySelector('.node-header')?.focus({preventScroll:!matchMedia('(max-width:760px)').matches});
  }, 'panel-close'); close.setAttribute('aria-label', t('closeDetails'));
  const reference = el('p', undefined, 'ref-line'); reference.append(refChip(node.id, `${node.id} · ${title(node)}`));
  if(workedBy(node))reference.append(el('span',t('workedBy',{who:workedBy(node)})));
  const panelBar=el('div',undefined,'panel-bar'); panelBar.append(el('strong',t('aboutWork')),close); p.append(panelBar);
  for (const d of view.decisions.filter(d => d.node === node.id)) {
    const ask = card(t('yourTurn'), question(d) || purposeWording(d.purpose, language), true);
    ask.append(refChip(d.id, `${d.id} · ${title(node)}`, true), button(t('read'), () => openDecision(d.id), 'primary')); p.append(ask);
  }
  p.append(el('p', status(node), 'panel-status '+cardTone(node)), el('h2', title(node)));
  if (view.plan_approval && !(view.plan_approval.verified && view.plan_approval.outcome === 'approved')) {
    planFacts(p, node); p.append(reference); p.scrollTop=scroll; return;
  }
  if (displayState(node,view.decisions)==='returned') p.append(el('p',t('returnedBy',{who:t(node.returned_by?.role==='reviewer'?'roleReviewer':'roleLeader'),reason:node.returned_reason||t('noReason')})));
  p.append(reference, el('p', attempts(node)));
  const rows = view.timeline.filter(r => r.node === node.id && r.kind === 'attempt').sort((a,b)=>b.seq-a.seq);
  if (rows.length) p.append(el('p', t('attemptsOf'), 'eyebrow'));
  const list = el('ol', undefined, 'panel-history');
  let earlier=false;
  for (const r of rows) {
    const item = el('li'); item.className=r.attempt===node.attempts?'current-history':'earlier-history'; if(r.attempt===node.attempts || !earlier)item.append(el('strong',t(view.complete?'endedAttempt':r.attempt===node.attempts?'currentAttempt':'earlierAttempt')));if(r.attempt!==node.attempts)earlier=true;item.append(wording(rowSentence(r),'p'));
    const extra=el('details');extra.open=!!rowOpen.get('panel:'+r.id);extra.addEventListener('toggle',()=>rowOpen.set('panel:'+r.id,extra.open)); extra.append(el('summary',t('attemptRecord',{n:r.attempt})));
    const checks=el('ul',undefined,'checks');r.checks.forEach(c=>checks.append(checkLine(c, r.attempt)));extra.append(checks);
    for(const [key,values] of [['workerNote',r.notes?[r.notes]:[]],['changedFiles',r.files||[]],['findings',r.findings||[]],['unsure',r.unsure||[]]])if(values.length){extra.append(el('p',t(key),'eyebrow'));textList(extra,values);}
    if(r.checks.length||r.notes||r.files?.length||r.findings?.length||r.unsure?.length)item.append(extra);
    list.append(item);
  }
  p.append(list);
  const more=el('details');more.open=!!rowOpen.get('panel:'+node.id);more.addEventListener('toggle',()=>rowOpen.set('panel:'+node.id,more.open));more.append(el('summary',t('workerDetails')));
  planFacts(more, node);
    more.append(handoffsCard('received',node.inputs,'from'),handoffsCard('outputs',node.outputs,'to'));
  if(view.complete){const files=[...new Set(rows.flatMap(r=>r.state==='passed'?r.files||[]:[]))];if(files.length){p.append(el('h3',t('resultLocations')));textList(p,files);}}
  p.append(more,button(t('showInLog'),()=>showNode(node.id),'small'));
  p.scrollTop=scroll;


}
// One entry of the record. An attempt carries its real checks; the rest are single sentences.
const rowOpen = new Map(), logShown = new Map();
function rowSentence(r) {
  const n = r.attempt || 1;
  if (r.kind === 'superseded') return t('evSuperseded');
  if (r.kind === 'started') return t('evStarted');
  if (r.kind === 'planned') return (r.revision > 1 ? t('evReplanned', {rev:r.revision}) : t('evPlanned')) + ' · ' + (r.counts ? t('planSummary',r.counts) : t('planItems',{n:r.count}));
  if (r.kind === 'final') return r.result === 'passed' ? t('evFinalPassed') : [t('evFinalFailed'), ...(r.failed || [])].join(' · ');
  if (r.kind === 'learned') return `${t('evLearned')} · ${r.text}`;
  if (r.kind === 'reopened') return [t('evReopened'), r.reason].filter(Boolean).join(' · ');
  if (r.kind === 'asked') return [t('evAsked'), r.question].filter(Boolean).join(' · ');
  if (r.kind === 'answered' && r.purpose === 'plan_approval' && r.outcome === 'approved') return [t('answeredPlan'),r.answer].filter(Boolean).join(' · ');
  if (r.kind === 'answered') return [t(({approved:'answeredApproval', revision_requested:'answeredRevision', rejected:'answeredRejection'})[r.outcome] || 'evAnswered'), r.answer].filter(Boolean).join(' · ');
  const failed = (r.checks || []).filter(c => c.result === 'failed').map(c => checkTitle(c, language)), passed = (r.checks || []).filter(c => c.result === 'passed').length;
  const current = view.nodes.find(node => node.id === r.node && node.attempts === r.attempt);
  const key = current && needs(current) && !['returned','replan','passed'].includes(r.state) ? 'evNeedsYou' : {running:'evRunning', submitted:'evSubmitted', passed:'evPassed', returned:'evReturned', replan:'evReplan', needs_you:'evNeedsYou', held:'evHeld'}[r.state] || 'evRunning';
  const outcome = passed && !failed.length && r.state !== 'running' ? t('checksPassed', {n:passed}) : '';
  return [t(key, {n}), outcome].filter(Boolean).join(' · ');
}
function rowTone(r) {
  const current=view.nodes.find(n=>n.id===r.node && n.attempts===r.attempt);
  if(current && needs(current) && !['returned','replan','passed'].includes(r.state))return 'mine';
  if (r.kind === 'asked' || r.kind === 'answered' || r.state === 'needs_you') return 'mine';
  if (r.kind === 'reopened' || r.state === 'returned' || r.state === 'replan' || (r.kind === 'final' && r.result !== 'passed')) return 'returned';
  if (r.state === 'passed' || (r.kind === 'final' && r.result === 'passed')) return 'passed';
  return r.state === 'running' || r.state === 'submitted' ? 'running' : '';
}
function checkLine(c, attempt) {
  const item = el('li', undefined, c.result === 'failed' ? 'check-failed' : '');
  const result = c.timed_out ? t('checkTimedOut') : t(c.result === 'failed' ? 'checkFailed' : 'checkPassed');
  item.append(wording(checkWording(c, language, attempt),'strong'));
  if(c.timed_out)item.append(el('span', ' · '+result));
  if (c.command) { const run = el('p', undefined, 'muted'); run.append(el('span', t('ranCommand')+': '), el('code', c.command), el('span', [c.exit_code === null || c.exit_code === undefined ? '' : ' → ' + t(c.exit_code === 0 ? 'exitSuccess' : 'exitFailure', {n:c.exit_code}), typeof c.duration_ms === 'number' ? t('seconds', {n:(c.duration_ms / 1000).toFixed(2)}) : ''].filter(Boolean).join(' · '))); item.append(run); }
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
function logRow(r, anchor = true, inline = false) {
  const isEarlier=r.kind==='attempt' && view.timeline.some(row=>row.kind==='attempt'&&row.node===r.node&&row.seq>r.seq);
  const item = el('li', undefined, rowTone(r)+(isEarlier?' earlier-history':' current-history')); if (anchor) item.id = r.id;
  const head = el('div', undefined, 'row-head'), text = el('span', undefined, 'row-text');
  const stamp=el('span', clock(r.ts, true), 'row-time');
  if(view.timeline.filter(row=>row.ts===r.ts).length>1)stamp.append(el('span', ' · '+t('recordOrder',{n:r.seq})));
  head.append(stamp);
  if (r.decision) text.append(refChip(r.decision, `${r.decision} · ${r.node_title || r.question}`, true));
  if (r.node) text.append(el('strong', title({id:r.node, title:r.node_title})), refChip(r.node, `${r.node} · ${r.node_title}`));
  text.append(wording(rowSentence(r))); head.append(text);
  const by = [who(r.by), r.kind === 'attempt' && r.worker?.model ? t('modelName',{model:r.worker.model}) : ''].filter(Boolean).join(' · ');
  if (by) head.append(el('span', by, 'row-who'));
  if (r.kind === 'attempt' && !inline) item.append(el('p',t(view.complete?'endedAttempt':isEarlier?'earlierAttempt':'currentAttempt'),'eyebrow'));
  item.append(head);
  if (r.kind !== 'attempt') return item;
  const extra = [['reason', r.reason && !r.checks.some(c => c.result === 'failed') ? [r.reason] : []], ['findings', r.findings || []], ['workerNote', r.notes ? [r.notes] : []], ['unsure', r.unsure || []], ['changedFiles', r.files || []]].filter(([, values]) => values.length);
  if (!r.checks.length && !extra.length) return item;
  const details = el(inline ? 'div' : 'details'); details.open = rowOpen.has(r.id) ? rowOpen.get(r.id) : !isEarlier && (r.state === 'returned' || r.state === 'replan');
  details.addEventListener('toggle', () => rowOpen.set(r.id, details.open));
  if (!inline) details.append(el('summary', t('rowDetails')));
  if (r.checks.length) { const checks = el('ul', undefined, 'checks'); r.checks.forEach(c => checks.append(checkLine(c, r.attempt))); details.append(checks); }
  for (const [key, values] of extra) { details.append(el('p', t(key), 'eyebrow')); textList(details, values); }
  item.append(details); return item;
}
function logList(rows, empty, anchor = true) {
  const list = el('ol', undefined, 'log');
  if (!rows.length) list.append(el('li', t(empty)));
  let day='';
  [...rows].sort((a, b) => b.seq - a.seq).forEach(r => {
    const date = r.ts ? new Date(r.ts).toLocaleDateString(language, {year:'numeric',month:'long',day:'numeric'}) : '';
    if(date && date!==day){const heading=el('li',undefined,'log-day');heading.append(el('h3',date));list.append(heading);day=date;}
    list.append(logRow(r, anchor));
  });
  return list;
}
let logFilter = 'all', logNode = null, found = null, mark = null;
function home() {
  const box = $('home'); clear(box);
  const inbox = el('section'); inbox.append(el('h2', t(view.decisions.length ? 'needsYou' : 'nothingTitle')));
  view.decisions.forEach(d => inbox.append(decisionCard(d)));
  if (!view.decisions.length) inbox.append(el('p', t('nothing'), 'muted'));
  if(!view.complete || view.decisions.length)box.append(inbox);
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
  [...view.nodes].sort((a,b)=>order.indexOf(a.id)-order.indexOf(b.id)).forEach(n => { const item = el('li', undefined, 'card'); item.append(button(title(n), () => selectNode(n.id)), el('p', status(n)), el('p', attempts(n), 'muted'), el('p', n.summary)); if (n.returned_reasons.length) textList(item, n.returned_reasons.flatMap((reasons,i)=>reasons.map(reason=>t('earlierFailure',{n:i+1,reason}))), 'noReason'); $('node-list').append(item); });
  forwardEdges(view.edges).forEach(e => { const a = view.nodes.find(n => n.id === e.from), b = view.nodes.find(n => n.id === e.to); $('edge-list').append(el('li', `${title(a)} → ${title(b)} · ${relationText(e)} · ${t(e.delivered ? 'delivered' : 'notDelivered')}`)); });
  view.decisions.forEach(d => { const item = el('li'); item.append(button(t('read'), () => openDecision(d.id))); decisionHeading(item, d, 'h3'); failedBlock(item, d); if (d.context.why) item.append(el('p', d.context.why)); $('decision-list').append(item); });
  if (!view.decisions.length) $('decision-list').append(el('li', t('nothingTitle')));
  const phone=$('phone-flow');clear(phone);
  for(const id of order){
    const n=view.nodes.find(n=>n.id===id),item=el('li');item.append(nodeCard(n,n.id===selected));
    const edges=forwardEdges(view.edges).filter(e=>e.from===id);
    for(const e of edges){const handoff=el('p',undefined,'phone-handoff');handoff.append(el('span','↓','status-glyph'),el('span',`${title(n)} → ${title(view.nodes.find(n=>n.id===e.to))} · ${e.relation==='reviews'?t('review'):t(e.delivered?'delivered':'notDelivered')}`));item.append(handoff);}
    phone.append(item);
  }
}
function showMode(next) {
  if (next !== 'decision' && (mode === 'decision' || next === 'home') && !discardDecision()) return false;
  mode = next; $('home').hidden = next !== 'home'; $('flow').hidden = next !== 'flow'; $('decision').hidden = next !== 'decision'; $('accessible').hidden = next !== 'flow';
  $('home-tab').setAttribute('aria-pressed', String(next === 'home')); $('flow-tab').setAttribute('aria-pressed', String(next === 'flow'));
  // The map can only measure its cards while it is on screen.
  if (renderer && next === 'flow' && view) renderer.update(view, selected); return true;
}
function discardDecision() {
  if (!decisionController.close()) return false;
  decisionUI = null; planBanner = null; clear($('decision')); return true;
}
function closeInvalidDecision(run, decisions, nextView = {decisions}) {
  const reason = decisionController.refresh(nextView, run);
  if (!reason) return false;
  if (mode === 'decision') leaveDecision(); decisionNotice = reason; notice(decisionNotice); return true;
}
function goHome() { if (showMode('home') && view) home(); }
function showGraph() { if (!showMode('flow')) return; attention(); panel(); }
function selectNode(id) { const n=view.nodes.find(n=>n.id===id),d=view.decisions.find(d=>d.node===id); if(n?.kind==='decision'&&d){openDecision(d.id);return;} if (!showMode('flow')) return; selected = selected === id ? null : id; panel(); if (renderer) renderer.select(selected); if (selected && matchMedia('(max-width:760px)').matches) $('panel').scrollIntoView({block:'start',behavior:reduced.matches?'auto':'smooth'}); }
function focusHeading(heading) { heading.tabIndex = -1; heading.focus({preventScroll:true}); }
function openDecision(id, focus = true) {
  replacementDecision=null; decisionNotice=''; notice('');
  if (view.decisions.find(d => d.id === id)?.purpose === 'plan_approval') {
    showGraph(); attention(); if (focus) $('plan-question')?.focus({preventScroll:true}); return;
  }
  const session = decisionController.open(id); if (!session) return;
  const current = () => decisionController.session === session;
  const d = session.decision;
  if (decisionUI?.session === session) { decisionUI.update(); return; }
  decisionNotice = ''; notice('');
  if (mode !== 'decision') cameFrom = mode;
  showMode('decision'); const box = $('decision'); clear(box);
  const reading = card(t('yourTurn'), null, true); reading.firstElementChild.remove(); reading.classList.add('reading');
  reading.append(el('p',t('fromTab',{tab:t(cameFrom==='home'?'home':'graph')}),'muted'), button(t('backToTab',{tab:t(cameFrom==='home'?'home':'graph')}),leaveDecision,'link'));
  const introduction = el('div'); reading.append(introduction);
  const report = el('div', undefined, 'worker-report'), note = el('div', undefined, 'speech');
  report.append(el('p',t('workerNote'),'eyebrow'),note); reading.append(report);
  const isQuestion = ['direction','information'].includes(d.kind);
  const answerLabel = el('label', t(isQuestion ? 'answerLabel' : 'backReason')); answerLabel.htmlFor = 'answer-text';
  const phoneHistory=el('details',undefined,'phone-history');reading.append(phoneHistory);
  const input = el('textarea'); input.id = 'answer-text'; input.required = true; input.value = session.draft;
  input.addEventListener('input', () => { if (current()) { decisionController.setDraft(input.value); updateActions(); } }); reading.append(answerLabel, input);
  const message = el('p'); message.id = 'answer-message'; message.setAttribute('role','status'); reading.append(message);
  const blindBox=el('label',undefined,'blind-confirm');
  const blindCheck=el('input');blindCheck.type='checkbox';blindCheck.id='blind-confirm';
  blindBox.append(blindCheck,el('span',t('confirmBlind')));reading.append(blindBox);
  blindCheck.addEventListener('change',()=>{decisionController.confirmBlind(blindCheck.checked);updateActions();});
  const actions = el('div'); actions.id = 'answer-actions';
  const updateActions = () => {
    actions.querySelectorAll('button[data-outcome]').forEach(b => { b.disabled = !current() || !decisionController.canSubmit(b.dataset.outcome, input.value); });
    for(const b of actions.querySelectorAll('button[data-outcome]')) {
      const kind=b.dataset.outcome,hint=actions.querySelector(`[data-hint=${kind}]`);
      hint.textContent=!b.disabled?'':session.busy?t('sending'):kind==='approved'?(session.nothingToJudge&&!session.blindConfirmed?t('blindHint'):t('readGateHint')):t(isQuestion?'writeFirst':'revisionHint');
      hint.hidden=!hint.textContent;
    }
    const read=canApprove(session),empty=session.nothingToJudge;
    if(approveButton)approveButton.classList.toggle('primary',!empty&&read);
    if(revisionButton)revisionButton.classList.toggle('primary',empty);
    const fileButtons=[...fileChoices.querySelectorAll('button')];
    const fileCanUnlock=!session.failed.length&&session.purpose!=='hold';
    fileButtons.forEach((b,i)=>b.classList.toggle('primary',!isQuestion&&!empty&&!read&&fileCanUnlock&&i===0));
    reminder.querySelector('button').classList.toggle('primary',!isQuestion&&!empty&&!read&&(!fileButtons.length||!fileCanUnlock));
    backButton.disabled = !!decisionController.session?.busy;
    blindCheck.disabled = !!session.busy;
    if (current() && !session.busy) message.textContent = '';
    // Say why sending is unavailable instead of leaving a silent disabled button.
    // The action's own hint is the single explanation for a disabled button.
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
  let approveButton, revisionButton;
  const actionButton = (outcome, text, cls) => {
    const b = button(text, () => send(outcome), cls); b.dataset.outcome = outcome;
    const row=el('div',undefined,'answer-action'),copy=el('div'),effect=el('p',undefined,'action-effect'),hint=el('p',undefined,'action-hint');
    effect.dataset.effect=outcome;hint.dataset.hint=outcome;hint.id='hint-'+outcome;b.setAttribute('aria-describedby',hint.id);
    copy.append(effect,hint);row.append(b,copy);actions.append(row);return b;
  };
  if (isQuestion) actionButton('answered', t('answer'), 'primary');
  else { revisionButton=actionButton('revision_requested', t('sendBack')); approveButton = actionButton('approved', '', 'primary'); }
  const backButton = button(t('leaveUnanswered'), leaveDecision); actions.append(backButton); reading.append(actions);
  const right = el('div'), surrounding = el('div'), history = el('section', undefined, 'decision-history'); right.append(history, surrounding);
  const files = card(t('readThis'), null, true), fileChoices = el('div', undefined, 'file-choices'), reader = el('pre', undefined, 'file-reader');
  reader.hidden = true; reader.tabIndex = 0; reader.setAttribute('aria-label',t('readThis'));
  const fileStatus = el('p'); fileStatus.setAttribute('role','status');
  files.append(fileChoices, fileStatus, reader); right.prepend(files);
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
          reader.classList.toggle('code-file', /\.(?:py|js|ts|jsx|tsx|json|css|html|sh|swift|rs|go|c|h|cpp|yaml|yml|toml|xml)$/i.test(file.path));
          reader.textContent = text; reader.hidden = false; fileStatus.textContent = ''; reader.setAttribute('aria-label',file.name);
          decisionController.openFile(); updateActions();
        } catch { if (current() && request === fileRequest) fileStatus.textContent = t('fileFailed'); }
      })); if(file.path!==file.name)entry.append(el('small',file.path,'file-path')); fileChoices.append(entry);
    }
  };
  const details = el('details', undefined, 'evidence'); details.append(el('summary', t('details'))); const raw = el('pre');
  details.open = session.detailsOpened;
  const markDetailsOpened = () => { if (current() && details.open) { decisionController.openDetails(); updateActions(); } };
  details.addEventListener('toggle', markDetailsOpened);
  const reminder = el('p', t('evidenceReminder'));
  reminder.append(button(t('details'), () => { if (current()) { details.open = true; markDetailsOpened(); details.querySelector('summary').focus(); } })); right.prepend(reminder);
  const gateFacts = el('div'); details.append(gateFacts);
  const loadEvidence = button(t('loadEvidence'), async () => {
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
  }); details.append(loadEvidence, raw); right.append(details); box.append(reading, right);
  const update = () => {
    const decision = session.decision;
    clear(introduction); decisionHeading(introduction, decision, 'h2'); const heading = introduction.querySelector('h2'); heading.id = 'decision-title';
    const node = view.nodes.find(n => n.id === decision.node);
    introduction.append(card(t('why'), decision.context.why || purposeWording(decision.purpose, language)));
    updateFiles(decision);
    clear(history);
    const rows = node ? view.timeline.filter(r => r.node === node.id && r.kind === 'attempt') : [];
    const missing=el('div',undefined,'missing-records');
    const nothingToInspect=session.nothingToJudge;
    reading.classList.toggle('no-evidence',nothingToInspect);
    blindBox.hidden=!nothingToInspect;blindCheck.checked=!!session.blindConfirmed;
    if(nothingToInspect) {
      missing.append(el('h3',t('nothingToJudge')),el('p',t('nothingToJudgeBody')));
    } else {
      if (!decision.files?.length) missing.append(el('p',t('noFiles')));
      if (!rows.some(r=>r.attempt===node?.attempts && r.checks?.length)) missing.append(el('p',t('noCurrentChecks')));
    }
    if(approveButton){
      approveButton.classList.toggle('primary',!nothingToInspect);
      revisionButton.classList.toggle('primary',nothingToInspect);
      // Action order is stable; emphasis changes, position does not.
    }
    if(missing.children.length) introduction.append(missing);
    history.hidden = !rows.length;phoneHistory.hidden=!rows.length;clear(phoneHistory);
    const previous=rows.filter(r=>r.attempt<node?.attempts && r.checks?.some(c=>c.result==='failed')).sort((a,b)=>b.seq-a.seq)[0];
    phoneHistory.append(el('summary',t('history')));
    const phoneRows=el('ol',undefined,'log');[...rows].sort((a,b)=>b.seq-a.seq).forEach(r=>{const row=logRow({...r,notes:r.attempt===node.attempts?null:r.notes,files:r.attempt===node.attempts?(r.files||[]).filter(f=>!decision.files?.some(file=>file.path===f)):r.files},false,true);row.prepend(el('p',t(view.complete?'endedAttempt':r.attempt===node.attempts?'currentAttempt':'earlierAttempt'),'eyebrow'));phoneRows.append(row);});phoneHistory.append(phoneRows);
    phoneHistory.open=!!rowOpen.get('decision:'+decision.id);phoneHistory.ontoggle=()=>rowOpen.set('decision:'+decision.id,phoneHistory.open);
    if (rows.length) {
      history.append(el('h3', t('history')));
      const list = el('ol', undefined, 'log');
      let earlier=false;
      [...rows].sort((a,b) => b.seq-a.seq).forEach(r => {
        const item = logRow({...r,notes:r.attempt===node.attempts?null:r.notes,files:r.attempt===node.attempts?(r.files||[]).filter(f=>!decision.files?.some(file=>file.path===f)):r.files}, false, true);
        if(r.attempt===node.attempts || !earlier)item.prepend(el('p', t(r.attempt === node.attempts ? 'currentAttempt' : 'earlierAttempt'), 'eyebrow'));if(r.attempt!==node.attempts)earlier=true;
        if (!r.checks.length) item.append(el('p', t('noAttemptChecks'), 'muted'));
        list.append(item);
      }); history.append(list);
    }
    clear(gateFacts); gateFacts.append(el('p', t('gateReview')), el('p', question(decision) || purposeWording(decision.purpose, language)));
    failedBlock(gateFacts, decision);
    for(const [key,name] of [['if_approved','ifApproved'],['if_rejected','ifRejected'],['undo','undo']])if(decision.context[key])gateFacts.append(el('p',t(name)+': '+decision.context[key]));
    if (decision.context.why) gateFacts.append(el('p', decision.context.why));
    details.hidden = !decision.has_evidence && !decisionController.requiresDetails;
    loadEvidence.hidden = !decision.has_evidence;
    note.textContent = decision.worker_note || ''; report.hidden = !decision.worker_note;
    const effects = [['if_approved','ifApproved'],['if_rejected','ifRejected'],['undo','undo']].filter(([key]) => decision.context[key]);
    clear(surrounding);
    failedBlock(surrounding, decision);
    for (const key of ['verified','unverified']) { if (!decision[key]?.length) continue; const c = card(t(key)); textList(c, decision[key]); surrounding.append(c); }
    files.hidden = !decision.files?.length;
    const bare = !rows.length && !decision.worker_note && !effects.length && !decision.context.why && !decision.failed?.length && !decision.verified?.length && !decision.unverified?.length && !decision.files?.length;
    if (bare) surrounding.append(el('p', t('questionOnly'), 'muted'));
    reminder.hidden = (!decision.has_evidence && !decisionController.requiresDetails) || (!!decision.files?.length && !decision.failed?.length && decision.purpose!=='hold');
    if (approveButton) approveButton.textContent = nothingToInspect ? t('acceptBlind') : purposeAction(decision.purpose, language, decision.failed);
    for(const effect of actions.querySelectorAll('[data-effect]')) {
      const kind=effect.dataset.effect;
      effect.textContent=t(kind==='approved'?'approveEffect':kind==='answered'?'answerEffect':'revisionEffect');
      if(kind==='revision_requested'&&node?.attempts&&node.attempts<node.max_attempts)effect.textContent=t('retryEffect',{n:node.attempts+1,max:node.max_attempts});
    }
    updateActions();
  };
  decisionUI = {session, update}; update(); if (focus) focusHeading(introduction.querySelector('h2'));
}
function leaveDecision() { if (cameFrom === 'home') goHome(); else showGraph(); }
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
    const old=view.superseded?.find(d=>d.id===id);
    if(old?.replacement) { replacementDecision=old.replacement; decisionNotice=t('supersededNotice',{old:id}); showMode('home'); home(); notice(decisionNotice); return true; }
    if (view.decisions.some(d => d.id === id)) { openDecision(id); return true; }
    const row = [...view.timeline].reverse().find(r => r.decision === id); if (!row) return miss(target.decision);
    decisionNotice = ''; notice(''); if (!showMode('home')) return false;
    logNode = null; logFilter = 'all'; found = mark = row.id; home(); return true;
  }
  if (target.node) {
    const text = target.node.toLowerCase();
    const node = view.nodes.find(n => n.id.toLowerCase() === text) || view.nodes.find(n => (n.title || '').toLowerCase().includes(text));
    if (!node) return miss(target.node);
    decisionNotice = ''; notice(''); selected = null; selectNode(node.id); return true;
  }
  return true;
}
function find(text) {
  text = text.trim(); if (!text || !view) return false;
  return /^d\d+$/i.test(text) ? jump({decision:text}) : jump({node:text});
}
function applyView(next) {
  if (decisionController.session?.busy) return;
  closeInvalidDecision(chosen, next.decisions, next);
  const nextFingerprint = JSON.stringify(next); if (nextFingerprint === fingerprint) return;
  const active=document.activeElement,focusId=active?.id,focusLabel=active?.getAttribute?.('aria-label');
  const focusHeader=active?.className==='node-header',phoneFocus=!!active?.closest?.('#phone-flow'),focusNode=active?.closest?.('[data-node]')?.dataset.node;
  const pageScroll=typeof scrollY==='number'?{left:scrollX,top:scrollY}:null;
  const languageChanged=language!==viewLanguage(next,navigator.language);
  language = viewLanguage(next, navigator.language); translate();
  if(languageChanged && projects.length)chooseRuns({projects});
  view = next; fingerprint = nextFingerprint; if (!view.nodes.some(n => n.id === selected)) selected = null; if (!view.nodes.some(n => n.id === logNode)) logNode = null;
  const firstDecision=view.decisions[0]?.id || view.timeline.find(r=>r.decision)?.decision;
  $('find-text').placeholder=firstDecision?t('findDecisionHint',{id:firstDecision}):t('findHint');
  $('title').textContent = view.title || t('brand'); $('where').textContent = '';
  const sent = view.plan_approval?.verified && ['rejected','revision_requested'].includes(view.plan_approval.outcome);
  $('flow').classList.toggle('sent-plan',!!sent); $('flow').classList.toggle('plan-unavailable',!!view.plan_error);
  $('subtitle').textContent = view.plan_error ? '' : view.plan_approval && !(view.plan_approval.verified && view.plan_approval.outcome==='approved') ? (view.plan_approval.status==='open'?t('planWaiting'):'') : view.complete ? t('complete', {total:view.nodes.length})+' · '+t('planSummary',view.plan_counts || {work:0,review:0,decision:0}) : t('overview', {total:view.nodes.length, done:view.counts.done, doing:view.counts.doing, needs:view.counts.needs_you});
  if(view.complete){const resultNode=[...view.nodes].reverse().find(n=>n.kind==='work'&&view.timeline.some(r=>r.node===n.id&&r.files?.length));if(resultNode)$('subtitle').append(button(t('results'),()=>selectNode(resultNode.id),'link result-action'));}
  accessible(); attention(); panel(); home(); showMode(mode); if (renderer && mode === 'flow') renderer.update(view, selected);
  if (mode === 'decision' && decisionController.session) openDecision(decisionController.session.target.id, false);
  if(active && active.isConnected===false){
    const scope=phoneFocus?$('phone-flow'):document;
    const replacement=focusId?$(focusId):[...scope.querySelectorAll('button,summary')].find(e=>(focusHeader?e.className==='node-header':focusLabel?e.getAttribute('aria-label')===focusLabel:e.textContent===active.textContent)&&(!focusNode||e.closest('[data-node]')?.dataset.node===focusNode));
    replacement?.focus({preventScroll:true});
  }
  if(pageScroll && typeof scrollTo==='function')scrollTo(pageScroll);
}
function setChosen(next) {
  if (decisionController.session?.busy || sameRun(chosen, next)) return;
  closeInvalidDecision(next, []); chosen = next; generation++; resetView(); logNode = null; logFilter = 'all'; found = mark = null; rowOpen.clear(); logShown.clear(); showMode('flow');
}
function chooseRuns(data) {
  projects = data.projects;
  const runs = projects.flatMap(p => (p.runs || []).map((r, i) => ({...r, project:p.root, projectName:p.name, number:i + 1})));
  runs.sort((a,b) => Number(b.status === 'open') - Number(a.status === 'open') || (b.last_event || '').localeCompare(a.last_event || ''));
  if (!chosen || !runs.some(r => r.project === chosen.project && r.id === chosen.run)) { const first = runs.find(r => !r.error) || runs[0]; setChosen(first ? {project:first.project,run:first.id} : null); }
  const picker = $('picker'); picker.disabled = !!decisionController.session?.busy; clear(picker);
  runs.forEach((r, i) => { const option = el('option', t('runOption', {project:r.projectName, run:r.id, n:r.open_decisions})); option.value = String(i); option.selected = !!chosen && r.project === chosen.project && r.id === chosen.run; picker.append(option); });
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
    notice(decisionNotice || (data.view.plan_error ? '' : !data.plan ? 'noPlan' : '')); applyView(data.view);
    if (pendingJump && view && !decisionController.session?.busy) { const target = pendingJump; pendingJump = null; jump(target); }
  } catch (error) { if (currentGeneration === generation) notice(error.status === 401 ? 'unauthorized' : error.status === 400 || error.status === 404 || error.status === 500 ? 'unreadable' : 'lost', true); }
  finally { loading = false; if (queuedRefresh) { queuedRefresh = false; refresh(true); } else schedule(); }
}
function resetView() { $('panel').onscroll=null; $('panel').hidden=true; $('flow').classList.remove('has-selection'); panelFingerprint=''; panelNode=null; language = viewLanguage(null, navigator.language); translate(); closeInvalidDecision(chosen, []); view = null; selected = null; fingerprint = ''; ['node-list','edge-list','decision-list','panel','home','attention'].forEach(id => clear($(id))); if (renderer) renderer.update({nodes:[],edges:[],decisions:[],complete:false}, null); $('flow').hidden = true; $('home').hidden = true; $('accessible').hidden = true; $('decision').hidden = true; $('subtitle').textContent = ''; $('where').textContent = ''; }
function schedule() { clearTimeout(timer); if (!document.hidden) timer = setTimeout(refresh, 2000); }
$('phone-view-toggle').addEventListener('click',()=>{const diagram=$('flow').classList.toggle('phone-diagram');$('phone-view-toggle').dataset.i18n=diagram?'showFlowList':'showDiagram';$('phone-view-toggle').textContent=t(diagram?'showFlowList':'showDiagram');$('phone-view-toggle').setAttribute('aria-pressed',String(diagram));if(renderer&&view)renderer.update(view,selected);});
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
  const icon=svg('svg',{viewBox:'0 0 24 24','aria-hidden':'true',class:'type-icon'});
  const paths={work:'M5 4H19V20H5Z M8 8H16 M8 12H16 M8 16H12',review:'M10 3A7 7 0 1 0 10 17A7 7 0 1 0 10 3 M15 15L21 21 M7 10L9 12L13 8',decision:'M12 3L22 12L12 21L2 12Z M12 7V13 M12 16V17',goal:'M5 21V3 M5 4H20L16 9L20 14H5'};
  icon.append(svg('path',{d:paths[kind]||paths.work,fill:'none',stroke:'currentColor','stroke-width':1.6,'stroke-linejoin':'round','stroke-linecap':'round'}));
  return icon;
}
function cardTone(n) {if(n.status==='rejected')return 'returned-card';return needs(n)||['held','awaiting_approval'].includes(n.status)?'waiting_for_you':n.status==='passed'||n.answered?'passed':['running','submitted','unverified'].includes(n.status)?'current':'unused';}
// A stable play mark is legible in a still frame and without colour.
function walker() {
  const mark=el('span','▶','walker');mark.setAttribute('aria-hidden','true');return mark;
}
// A rebuilt element joins a looping animation at the phase it would have reached.
function inPhase(element, period) {element.style.animationDelay=-(performance.now()%period)+'ms';return element;}
function nodeDescription(n) {return `${t(n.kind||'work')}. ${title(n)}. ${status(n)}. ${attempts(n)}. ${t('returnTimes',{n:cometCount(n)})}`;}
function nodeCard(n, expanded = false) {
  const root=el('article',undefined,'node-card '+cardTone(n)+(['running','retrying'].includes(displayState(n,view.decisions))?' working':'')+(expanded?' expanded':''));root.dataset.node=n.id;
  const header=button('',()=>{
    const decision=view.decisions.find(d=>d.node===n.id);
    if(n.kind==='decision'){if(decision)openDecision(decision.id);else selectNode(n.id);}
    else selectNode(n.id);
  },'node-header');
  header.setAttribute('aria-label',nodeDescription(n));header.setAttribute('aria-expanded',String(expanded));
  const state = displayState(n, view.decisions), statusLine = el('span', status(n), 'node-status');
  statusLine.prepend(el('span', statusGlyph(state), 'status-glyph'));
  header.append(statusLine);
  const titleLine=el('span',undefined,'node-title-line');
  if(n.kind && n.kind!=='work')titleLine.append(typeIcon(n.kind));
  titleLine.append(el('strong',title(n),'node-title'));header.append(titleLine);
  const reference=el('div',undefined,'ref-line node-reference');
  reference.append(refChip(n.id, `${n.id} · ${title(n)}`));
  if(n.attempts)reference.append(el('span',t('attemptShort',{n:n.attempts}),'attempt-caption'));
  const decision=view.decisions.find(d=>d.node===n.id);
  const footer=el('div',undefined,'node-footer');
  if(decision)footer.append(button(t('answerHere',{id:decision.id}),()=>openDecision(decision.id),'node-decision'));
  else if(displayState(n,view.decisions)==='returned') {
    const reason=n.returned_reason || t('noReason');
    const line=el('span',t('returnedShort',{who:t(n.returned_by?.role==='reviewer'?'returnReviewer':'returnLeader'),reason}));line.title=line.textContent;footer.append(line);
  }
  const essentials=el('div',undefined,'node-essentials');
  const files=[...new Set(n.deliverables || [])];
  if(files.length)essentials.append(el('p',t('planCardDelivery',{files:files.join(', ')})));
  if(n.planned_checks?.length)essentials.append(el('p',t('planCardChecks',{n:n.planned_checks.length,first:checkTitle(n.planned_checks[0],language)})));
  const questions=(view.planned_questions || []).filter(q=>q.node===n.id);
  if(questions.length)essentials.append(el('p',t('planCardQuestion',{n:questions.length}),'planned-question'));
  root.append(header,essentials,footer,reference);
  return root;
}
function createMap() {
  const map=$('map');map.tabIndex=0;
  const toolbar=el('div',undefined,'map-toolbar'),viewport=el('div',undefined,'map-viewport'),spacer=el('div',undefined,'map-spacer'),stage=el('div',undefined,'map-stage');
  viewport.tabIndex=0;viewport.setAttribute('aria-label',t('mapHelp'));spacer.append(stage);viewport.append(spacer);map.append(toolbar);
  const key=el('div',undefined,'line-key'), overflow=el('div',undefined,'map-overflow'); overflow.setAttribute('aria-label',t('graphEdges'));overflow.dataset.i18nLabel='graphEdges';
  toolbar.append(key);map.append(viewport);
  const visibleCount=el('span',undefined,'map-visible'),overflowButtons=new Map();overflow.append(visibleCount);
  let data={nodes:[],edges:[],decisions:[]},chosenNode=null,layout=null,scale=1,automatic=true;
  const nodes=new Map(),chips=new Map(),seen=new Map();let drawing=null,placed=false,layoutKey='',origin={x:0,y:0};
  const zoomText=el('output');zoomText.setAttribute('aria-live','polite');
  const zoom=amount=>{automatic=false;scale=Math.max(2/3,Math.min(1.6,scale+amount));size();};
  const fit=()=>{scale=Math.max(2/3,Math.min(1,(viewport.clientWidth-24)/layout.bounds.width,(viewport.clientHeight-24)/layout.bounds.height));automatic=false;size();viewport.scrollLeft=0;viewport.scrollTop=0;};
  const zoomOut=button('−',()=>zoom(-.1)),zoomIn=button('+',()=>zoom(.1));
  toolbar.append(zoomOut,zoomIn,button(t('fit'),fit),zoomText,overflow);
  zoomOut.dataset.i18nLabel='zoomOut';zoomIn.dataset.i18nLabel='zoomIn';toolbar.children[3].dataset.i18n='fit';viewport.dataset.i18nLabel='mapHelp';
  const mapTitle=el('div',undefined,'map-title'), name=el('strong',t('graph')), direction=el('span',t('mapDirection'));
  name.dataset.i18n='graph';direction.dataset.i18n='mapDirection';mapTitle.append(name,direction);toolbar.prepend(mapTitle);translate();
  function outside() {
    if(!layout || !viewport.clientWidth)return;
    const w=viewport.clientWidth,h=viewport.clientHeight,ox=origin.x,oy=origin.y;
    const groups={offLeft:[],offRight:[],offTop:[],offBottom:[]}; let visible=0;
    for(const n of data.nodes) {
      const p=layout.positions[n.id],x=p.x*scale+ox-viewport.scrollLeft,y=p.y*scale+oy-viewport.scrollTop;
      const direction=offscreenDirection({x,y,width:p.width*scale,height:p.height*scale},w,h);
      if(direction)groups[direction].push(n);
      if(x<w && y<h && x+p.width*scale>0 && y+p.height*scale>0)visible++;
      const element=nodes.get(n.id); if(element)element.style.visibility='visible';
    }
    for(const c of layout.chips){const chip=chips.get(c.first);if(chip)chip.hidden=scale<1 || !!chip.dataset.tooWide || !!offscreenDirection({x:c.x*scale+ox-viewport.scrollLeft,y:c.y*scale+oy-viewport.scrollTop,width:c.width*scale,height:c.height*scale},w,h);}
    // The viewport clips routes naturally: an off-screen neighbour leaves a visible continuing stub.
    visibleCount.textContent=t('visibleCards',{n:visible,summary:t('planSummary',data.plan_counts || {work:0,review:0,decision:0})});
    for(const [direction,b] of overflowButtons)b.hidden=!groups[direction].length;
    for(const [direction,items] of Object.entries(groups))if(items.length) {
      let b=overflowButtons.get(direction);
      if(!b){b=button('',()=>{},'small');overflowButtons.set(direction,b);overflow.append(b);}
      overflow.append(b);
      b.textContent=t('offCount',{direction:t(direction),n:items.length}) + (items.some(n=>['running','retrying','submitted'].includes(displayState(n,data.decisions))) ? t('offWorking',{n:items.filter(n=>['running','retrying','submitted'].includes(displayState(n,data.decisions))).length}) : '') + (items.some(n=>data.decisions.some(d=>d.node===n.id)) ? t('offNeeds',{n:items.filter(n=>data.decisions.some(d=>d.node===n.id)).length}) : '');
      b.onclick=()=>{
        const horizontal=['offLeft','offRight'].includes(direction),back=['offLeft','offTop'].includes(direction);
        const sorted=[...items].sort((a,b)=>(layout.positions[a.id][horizontal?'x':'y']-layout.positions[b.id][horizontal?'x':'y'])*(back?-1:1));
        const p=layout.positions[sorted[0].id];
        viewport.scrollLeft=Math.max(0,p.x*scale-(w-p.width*scale)/2+ox);
        viewport.scrollTop=Math.max(0,p.y*scale-Math.max(12,(h-p.height*scale)/2)+oy);outside();viewport.focus({preventScroll:true});
      };
    }
  }
  viewport.addEventListener('scroll',outside);
  function size() {
    if(!layout)return;
    if(map.getBoundingClientRect){
      const available=Math.max(300,innerHeight-map.getBoundingClientRect().top-62);
      map.style.height=(data.complete?Math.min(available,layout.bounds.height*scale+100):available)+'px';
      $('panel').style.maxHeight=matchMedia('(max-width:760px)').matches?'none':parseFloat(map.style.height)+'px';
      $('panel').style.height=$('panel').style.maxHeight;
    }
    const w=viewport.clientWidth||900,h=viewport.clientHeight||600;
    if(!placed && automatic)scale=fitScale(layout.bounds,w-24,h-24);
    origin={x:Math.max(0,(w-layout.bounds.width*scale)/2),y:Math.max(0,(h-layout.bounds.height*scale)/2)};
    Object.assign(stage.style,{left:origin.x+'px',top:origin.y+'px',width:layout.bounds.width+'px',height:layout.bounds.height+'px',transform:`scale(${scale})`});
    stage.style.setProperty('--map-text',Math.max(14,12/scale)+'px');
    Object.assign(spacer.style,{width:layout.bounds.width*scale>w?layout.bounds.width*scale+'px':'100%',height:layout.bounds.height*scale>h?layout.bounds.height*scale+'px':'100%'});
    if(!$('panel').hidden && $('panel').onscroll)$('panel').onscroll();
    zoomText.textContent=Math.round(scale*100)+'%';zoomOut.disabled=scale<=2/3;zoomOut.title=zoomOut.disabled?t('minZoom'):t('zoomOut');zoomIn.disabled=scale>=1.6;outside();
  }
  const setRect=(element,rect)=>Object.assign(element.style,{left:rect.x+'px',top:rect.y+'px',width:rect.width+'px',height:rect.height+'px'});
  function update(next,id) {
    if(layout)size();
    const planKey=JSON.stringify([next.nodes.map(n=>[n.id,n.title,n.kind,n.target]),next.edges.map(e=>[e.from,e.to,e.relation,e.label])]);
    if(planKey!==layoutKey){layoutKey=planKey;placed=false;automatic=true;}
    const reveal=id&&id!==chosenNode;data=next;chosenNode=id;map.classList.toggle('has-expanded',!!id);
    const focused=document.activeElement?.closest?.('[data-node]')?.dataset.node,focusedChip=document.activeElement?.dataset?.chip;
    const activeIds=new Set(data.nodes.map(n=>n.id));
    for(const [key,element] of nodes)if(!activeIds.has(key)){element.remove();nodes.delete(key);}
    for(const n of data.nodes) {
      const expanded=n.id===chosenNode;
      const signature=JSON.stringify([n,data.decisions.filter(d=>d.node===n.id)]);
      let element=nodes.get(n.id);
      if(!element){element=el('div',undefined,'node-position');nodes.set(n.id,element);stage.append(element);}
      if(element.dataset.signature!==signature) {
        const card=nodeCard(n,expanded),before=seen.get(n.id),tone=cardTone(n);
        // One-shot motion only for a change observed while the page was open.
        if(before&&cometCount(n)>before.comets)card.classList.add('changed');
        else if(before&&before.tone!==tone&&['passed','current'].includes(tone))card.classList.add('changed');
        element.replaceChildren(card);element.dataset.signature=signature;
      }
      seen.set(n.id,{tone:cardTone(n),comets:cometCount(n)});
    }
    layout=layeredLayout(data.nodes,data.edges.map(e=>({...e,label:e.label?label(e.label):''})),data.decisions,true,{language});
    clear(key); key.append(el('strong',t('lineKinds')));
    name.textContent=$('flow').classList.contains('sent-plan')?t('planReturned'):t('graph');mapTitle.classList.toggle('returned-title',$('flow').classList.contains('sent-plan'));
    for(const [state,word] of [['open','lineSampleOpen'],['closed','lineSampleClosed'],['review','lineSampleReview']]){
      if(!layout.routes.some(r=>(r.relation==='reviews'?'review':r.gateState==='open'?'open':'closed')===state))continue;
      const sample=el('span',undefined,'line-sample '+state),caption=el('span',t(word));caption.dataset.i18n=word;sample.append(el('i'),caption);key.append(sample);
    }
    const states=el('div',undefined,'state-legend'); states.append(el('strong',t('stateKinds')));
    for(const state of [...new Set(data.nodes.map(n=>displayState(n,data.decisions)))]) states.append(el('span',`${statusGlyph(state)} ${t(state)}`,'state-key state-'+state));
    if(data.nodes.some(n=>n.kind==='review') || data.planned_questions?.length)states.append(el('strong',t('markKinds')));
    if(data.nodes.some(n=>n.kind==='review')) { const mark=el('span',undefined,'state-key review-key'); mark.append(typeIcon('review'),el('span',t('review')));states.append(mark); }
    if(data.planned_questions?.length)states.append(el('span','? '+t('planQuestions',data.plan_counts),'state-key'));
    key.append(states);
    // Reorder existing controls without replacing them: tab order follows the drawing.
    for(const id of layout.order){const e=nodes.get(id);setRect(e,layout.positions[id]);stage.append(e);}
    if(drawing)drawing.remove();drawing=svg('svg',{width:layout.bounds.width,height:layout.bounds.height,class:'edge-layer','aria-hidden':'true'});
    const defs=svg('defs');
    for(const state of ['open','closed','waiting_for_you']) {
      const marker=svg('marker',{id:'arrow-'+state,viewBox:'0 0 10 10',refX:10,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M0 0 10 5 0 10Z',class:state}));defs.append(marker);
    }
    drawing.append(defs);stage.prepend(drawing);
    for(const element of chips.values())element.remove();chips.clear();
    for(const route of layout.routes) {
      const {chip:c}=route;
      const d=roundedRoute(route.points);
      const flowing=route.gateState==='open'&&['running','retrying'].includes(displayState(data.nodes.find(n=>n.id===route.to)||{}, data.decisions));
      const line=svg('path',{d,'data-from':route.from,'data-to':route.to,class:'edge-path '+route.gateState+(route.relation==='reviews'?' review':'')+(flowing?' flowing':''),'marker-end':`url(#arrow-${route.gateState})`});
      drawing.append(svg('path',{d,class:'edge-underlay'}),flowing?inPhase(line,2000):line);
      if(!c||chips.has(c.first))continue;
      const chip=el('div',undefined,'edge-chip '+route.gateState);
      const source=data.nodes.find(n=>n.id===route.from),targets=layout.routes.filter(r=>r.chip===c).map(r=>title(data.nodes.find(n=>n.id===r.to))).join(', ');
      chip.setAttribute('aria-label',`${edgeRelationLabel(route,language)}. ${title(source)} → ${targets}`);
      chip.append(el('span',route.text));chip.dataset.chip=c.key;setRect(chip,c);stage.append(chip);if(chip.firstElementChild.offsetWidth>c.width-20)chip.dataset.tooWide='true';chips.set(c.first,chip);
    }
    // All focusable controls are ordered by column and then vertical position.
    [...nodes.values(),...chips.values()].sort((a,b)=>parseFloat(a.style.left)-parseFloat(b.style.left)||parseFloat(a.style.top)-parseFloat(b.style.top)).forEach(e=>stage.append(e));
    const directionKey='mapDirection';
    direction.textContent=t(directionKey);direction.dataset.i18n=directionKey;
    mapTitle.classList.remove('map-complete');
    size();
    // Start at the beginning, with no clipped labels from a preceding column.
    if(!data.nodes.length)placed=false;
    else if(!placed&&viewport.clientWidth){
      placed=true;viewport.scrollLeft=0;viewport.scrollTop=0;
      if(layout.bounds.width*scale>viewport.clientWidth||layout.bounds.height*scale>viewport.clientHeight){
        const first=layout.order.find(id=>!['passed'].includes(displayState(data.nodes.find(n=>n.id===id),data.decisions)));
        if(first){const p=layout.positions[first];viewport.scrollLeft=Math.max(0,p.x*scale-28);viewport.scrollTop=Math.max(0,p.y*scale-28);}
      }
    }
    if(reveal)revealSelection();
    outside();
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
  viewport.addEventListener('pointerdown',e=>{if(e.target.closest('button,summary,a'))return;drag={x:e.clientX,y:e.clientY,left:viewport.scrollLeft,top:viewport.scrollTop};if(e.pointerType==='touch'){drag=null;return;}viewport.setPointerCapture(e.pointerId);viewport.classList.add('panning');});
  viewport.addEventListener('pointermove',e=>{if(drag){viewport.scrollLeft=drag.left+drag.x-e.clientX;viewport.scrollTop=drag.top+drag.y-e.clientY;}});
  const release=()=>{drag=null;viewport.classList.remove('panning');};viewport.addEventListener('pointerup',release);viewport.addEventListener('pointercancel',release);
  new ResizeObserver(size).observe(viewport);
  function revealSelection() {
    const p=layout?.positions[chosenNode];if(!p || !viewport.clientWidth)return;
    const w=viewport.clientWidth,h=viewport.clientHeight,ox=origin.x,oy=origin.y;
    const neighbours=layout.routes.filter(r=>r.from===chosenNode||r.to===chosenNode).map(r=>layout.positions[r.from===chosenNode?r.to:r.from]);
    let left=p.x,right=p.x+p.width,top=p.y,bottom=p.y+p.height;
    for(const q of neighbours.sort((a,b)=>Math.abs(a.x-p.x)-Math.abs(b.x-p.x))){
      if((Math.max(right,q.x+q.width)-Math.min(left,q.x))*scale<w-32 && (Math.max(bottom,q.y+q.height)-Math.min(top,q.y))*scale<h-32){left=Math.min(left,q.x);right=Math.max(right,q.x+q.width);top=Math.min(top,q.y);bottom=Math.max(bottom,q.y+q.height);}
    }
    viewport.scrollTo({left:Math.max(0,(left+right)*scale/2+ox-w/2),top:Math.max(0,(top+bottom)*scale/2+oy-h/2),behavior:'auto'});
  }
  return {update,select:id=>{
    chosenNode=id;
    for(const [key,element] of nodes){element.firstElementChild.classList.toggle('expanded',key===id);element.querySelector('.node-header').setAttribute('aria-expanded',String(key===id));}
    size();if(id)revealSelection();
  },wake:size};
}
renderer = createMap(); if(view)renderer.update(view,selected);
}
