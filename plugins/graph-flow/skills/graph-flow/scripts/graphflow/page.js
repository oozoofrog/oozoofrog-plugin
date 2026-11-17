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
    "legend": "기호 안내",
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
    "submitted": "검토를 기다려요",
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
    "questionOnly": "이 질문에는 설명, 근거, 읽을 파일이 없어요.",
    "writeFirst": "답을 적으면 보낼 수 있어요.",
    "leaveUnanswered": "답하지 않고 돌아가기",
    "aboutWork": "일의 상세 내용",
    "decisionRef": "결정 {id}",
    "askedBy": "물어본 곳: {who}",
    "workedBy": "맡은 곳: {who}",
    "find": "찾기",
    "findHint": "결정·질문 번호 또는 일 이름",
    "findNone": "“{text}”에 맞는 결정, 질문, 일이 없어요. 다른 흐름이면 위에서 바꿔 주세요.",
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
    "answered": "답을 보냈어요. 진행 담당자가 다음 확인 때 반영해요. 세션이 멈춰 있으면 채팅에서 “답했어요”라고 알려 주세요.",
    "details": "자세한 근거 보기",
    "loadEvidence": "근거 읽기",
    "noEvidence": "읽을 근거 기록이 없어요.",
    "evidenceFailed": "근거를 읽지 못했어요. 다시 해 주세요.",
    "noProjects": "등록된 프로젝트가 없어요. 프로젝트에서 새 흐름을 시작한 뒤 다시 연결해 주세요.",
    "noRun": "아직 흐름이 없어요. 프로젝트에서 새 흐름을 시작한 뒤 다시 연결해 주세요.",
    "noPlan": "아직 계획이 없어요. 이 흐름에 계획을 넣으면 여기에 나타나요.",
    "unreadable": "이 흐름을 읽지 못했어요. 기록을 확인하거나 다른 흐름을 골라 주세요.",
    "lost": "연결이 끊겼어요. 서버가 켜져 있는지 확인한 뒤 다시 연결해 주세요.",
    "unauthorized": "이 창의 연결 정보가 없거나 바뀌었어요. 진행 담당자에게 대시보드를 다시 열어 달라고 해 주세요.",
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
    "purposeAuthorization": "이 일을 허락할지 정해 주세요.",
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
    "runChanged": "흐름이 바뀌어서 답변 창을 닫고 적던 답을 지웠어요.",
    "brand": "작업 흐름",
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
    "idle": "지금 진행 중인 일이 없어요. 진행 담당자가 다음 일을 시작하면 여기에 나타나요.",
    "log": "일어난 일",
    "logEmpty": "아직 기록된 일이 없어요.",
    "filterEmpty": "여기에 해당하는 기록이 없어요.",
    "filterAll": "전체",
    "filterMine": "내가 할 일",
    "filterReturned": "고치러 돌아옴",
    "onlyNode": "“{title}”의 기록만 보는 중",
    "showAll": "전체 보기",
    "evStarted": "실행 기록을 만들었어요",
    "evPlanned": "계획을 올렸어요",
    "evReplanned": "계획을 바꿨어요 · {rev}번째 계획",
    "evRunning": "{n}번째 시도 중",
    "evSubmitted": "{n}번째 시도 제출 · 검사를 기다려요",
    "evPassed": "{n}번째 시도 통과",
    "evReturned": "{n}번째 시도 · 고치러 돌아옴",
    "evReplan": "{n}번째 시도 · 고치러 돌아옴 · 새 계획이 필요해요",
    "evNeedsYou": "{n}번째 시도 · 내가 할 일",
    "evHeld": "{n}번째 시도 · 멈춰 두었어요",
    "evReopened": "다시 열었어요",
    "evAsked": "질문",
    "evAnswered": "질문에 답했어요",
    "evFinalPassed": "전체 결과 확인 통과",
    "evFinalFailed": "전체 결과 확인 실패",
    "evLearned": "배운 것을 기록했어요",
    "checksPassed": "자동 검사 {n}개 통과",
    "checksFailed": "✕ {n}번째 시도에서 “{names}” 확인이 통과하지 못했어요",
    "rowDetails": "검사와 메모 보기",
    "checkPassed": "통과",
    "checkFailed": "실패",
    "checkTimedOut": "시간 초과",
    "exitCode": "명령 반환값 {n}",
    "seconds": "{n}초",
    "gateRun": "진행 담당자가 확인했어요",
    "workerRun": "작업 담당자가 확인했어요",
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
    "sessionT3": "담당 대화",
    "sessionClaude": "담당 대화",
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
    "workingHere": "작업 담당자가 진행 중이에요",
    "offLeft": "← 왼쪽",
    "offRight": "오른쪽 →",
    "offTop": "↑ 위쪽",
    "offBottom": "↓ 아래쪽",
    "offCount": "{direction} {n}개",
    "visibleCards": "{summary} · 카드 {n}개가 보여요",
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
    "scopeCheck": "맡은 파일만 고쳤는지",
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
    "pastReturn": "이전 시도 {n}번 · 고치러 돌아옴",
    "nothingToJudge": "판단할 자료가 없어요",
    "nothingToJudgeBody": "읽을 파일도, 지금 시도의 검사 결과도 없어요. 결과를 보여 달라고 돌려보내거나 채팅에서 다시 물어봐 주세요.",
    "confirmBlind": "파일과 검사 결과 없이 받아들일게요",
    "blindHint": "자료 없이 받아들이려면 위 내용을 확인해 주세요.",
    "acceptBlind": "자료 없이 받아들이기",
    "minZoom": "글자를 읽을 수 있는 최소 크기예요",
    "readGateHint": "파일이나 근거를 먼저 열어 주세요",
    "approveEffect": "받아들이기로 한 답이 진행 담당자에게 전달돼요",
    "revisionEffect": "고칠 곳이 진행 담당자에게 전달돼요",
    "answerEffect": "답이 진행 담당자에게 전달돼요",
    "retryEffect": "다음은 최대 {max}번 중 {n}번째 시도예요",
    "decisionWork": "관련 일 · {title}",
    "fitAll": "전체 보기",
    "readScale": "읽기 크기",
    "planSummary": "일 {work}개 · 검토 {review}개 · 결정 {decision}개",
    "planStart": "시작",
    "planStartEffect": "담당자가 계획의 일을 시작해요.",
    "planBackEffect": "고칠 내용을 담당자에게 보내요.",
    "planSentBack": "계획을 돌려보냈어요",
    "planWaiting": "계획을 확인해 주세요",
    "planSentNote": "내가 보낸 내용",
    "planWaitingRevision": "담당자가 고친 새 계획을 기다리고 있어요.",
    "planChecks": "자동 검사와 내 확인",
    "plannedCommand": "실행할 명령",
    "planDeliverables": "만들 결과",
    "evSuperseded": "새 계획으로 바뀌었어요",
    "purposePlan": "시작하기 전에 계획을 확인해 주세요.",
    "untitledCheck": "설명이 아직 없는 검사예요",
    "ranCommand": "실행한 명령",
    "returnedBy": "{whoSubject} 돌려보냈어요 · {reason} — 통과하지 못했어요",
    "returnedShort": "{reason} · {whoSubject} 돌려보냈어요",
    "returnLeader": "리더",
    "returnReviewer": "검토자",
    "recordOrder": "기록 {n}",
    "results": "결과 보기",
    "resultLocations": "결과 파일",
    "checkingKey": "◷ 검사받는 중",
    "reviewKey": "⌕ 검토 작업",
    "returnedKey": "↩ 고치러 돌아옴",
    "pendingKey": "○ 시작 전",
    "planChecklist": "자동 검사 {checks}개 · 예정된 결정 {decisions}번",
    "planReturned": "돌려보낸 계획",
    "planUnverified": "답이 확인되지 않았어요",
    "planUnverifiedHelp": "이 답으로는 일을 시작할 수 없어요. 담당자가 계획을 다시 올리면 새 결정에 답해 주세요.",
    "planKeyMismatch": "승인을 확인할 수 없어요. 키 분실·교체, 프로젝트 이동, 기록 변조 중 무엇 때문인지는 알 수 없어요.",
    "planTampered": "계획 파일이 기록과 달라요",
    "planTamperedHelp": "진행 담당자가 계획을 다시 올려야 해요. 새 계획이 올라오면 여기서 승인해 주세요.",
    "planGoal": "실제 지시",
    "planOwns": "맡은 파일",
    "planNeeds": "받는 것",
    "planReads": "읽을 자료",
    "planIntegration": "전체 결과 검사",
    "planPromoted": "이 계획에 포함된 고정 검사",
    "planQuestions": "예정된 결정 {decisions}번 · 어디에서 물을까요?",
    "planCardChecks": "자동 검사 {n}개 · {first}",
    "planCardDelivery": "결과 · {files}",
    "planCardQuestion": "결정 {n}개 · {question}",
    "noPlannedChecks": "별도 검사가 없어요",
    "supersededNotice": "결정 {old}에서 {newParticle} 바뀌었어요. 현재 계획을 확인해 주세요.",
    "supersededLink": "현재 결정 {id} 보기",
    "checkNotMet": "통과 못 함 · {title}",
    "lineKinds": "선의 뜻",
    "stateKinds": "일의 상태",
    "markKinds": "표시",
    "fromTab": "{tab}에서 온 결정이에요",
    "backToTab": "← {tab}로 돌아가기",
    "endedAttempt": "완료된 시도",
    "commandScope": "제한 시간 · {seconds}초",
    "checkPrompt": "사람에게 물을 내용",
    "checkHost": "확인 도구 · {tool} / 기대 결과 · {expect}",
    "planItems": "전체 항목 {n}개",
    "answeredPlan": "이 계획대로 시작하기로 답했어요",
    "exitSuccess": "성공",
    "exitFailure": "실패 · 종료 코드 {n}",
    "planKeyHeading": "확인 키가 바뀌었어요",
    "oldRunApproval": "이전 버전(0.2.1)에서 시작한 실행이에요. 담당자가 계획을 다시 올리면 읽고 계속할 수 있어요.",
    "planMissing": "계획을 올려 주세요",
    "planMissingHelp": "진행 담당자가 현재 계획을 올리면 여기서 승인할 수 있어요.",
    "planReplaced": "확인할 수 없던 계획을 교체했어요. 모든 일을 다시 확인해 주세요.",
    "unverifiedAnswer": "확인되지 않은 답 · 승인으로 인정되지 않아요",
    "unverifiedAuthor": "내가 보낸 답인지 확인할 수 없어요",
    "planLens": "검토 관점",
    "planOutputs": "넘기는 것",
    "runChecksTitle": "전체 결과 확인",
    "runChecksAfter": "모든 일을 마친 뒤 확인해요",
    "runChecksGoal": "계획의 목표",
    "runConstraints": "지켜야 할 조건",
    "countWork": "일 {n}개",
    "countReview": "검토 {n}개",
    "countDecision": "결정 {n}개",
    "countChecks": "자동 검사 {n}개",
    "countQuestions": "질문 {n}개",
    "questionsMark": "? 여기서 물어요",
    "citesCheck": "인용한 파일과 줄이 실제로 있는지",
    "humanCheck": "사람이 결과를 확인해요",
    "hostCheck": "실행 환경에서 확인해요",
    "evRepinned": "확인 키를 새로 만들었어요. 계획을 한 번 더 승인해 주세요.",
    "overviewLevel": "간략 보기",
    "detailLevel": "상세 보기",
    "readableFit": "읽을 수 있는 크기",
    "overviewHelp": "제목만 보여요. 자세한 내용은 카드를 눌러 주세요.",
    "planContinue": "계속",
    "planContinueQuestion": "이 계획대로 계속할까요?",
    "planContinueEffect": "이미 한 일은 유지하고 이어서 진행해요.",
    "warning": "⚠ 진행이 멈춰 있어요",
    "keyRecoveryAfter": "예상하지 못한 변화라면 담당자와 기록부터 확인해 주세요.",
    "copyCommand": "명령 복사",
    "copiedCommand": "복사했어요",
    "projectMoved": "프로젝트 위치가 달라졌어요",
    "projectMovedHelp": "프로젝트나 실행 폴더를 옮기거나 이름을 바꾸면 승인이 무효가 돼요. 담당자가 현재 계획을 다시 올리면 한 번 더 승인해 주세요.",
    "workRecorded": "진행한 작업 기록이 있어요. 새 실행은 승인을 확인할 때까지 멈춰요.",
    "noWorkRecorded": "아직 실행한 작업 기록이 없어요. 승인 전에는 시작하지 않아요.",
    "planOpen": "계획 읽기",
    "futureDelivery": "{who}에서 받아요",
    "visiblePlan": "일 {total}개 + 전체 확인 · {n}개 제목이 보여요",
    "listAll": "목록으로 모두 읽기",
    "questionsForNode": "여기서 결정할 내용",
    "findingsOutput": "검토 의견",
    "approvalOutput": "결정 내용",
    "sessionOther": "작업 대화",
    "runNumber": "실행 {n}",
    "runResultSummary": "결과 · {files}",
    "approvedCommit": "확인할 커밋",
    "evidenceHashes": "파일 확인값 자세히 보기",
    "returnedActor": "{whoSubject} 돌려보냈어요",
    "planChanged": "계획이 바뀌었어요 — 다시 확인해 주세요",
    "decisionChanged": "결정 내용이나 근거가 바뀌었어요 — 다시 확인해 주세요",
    "acknowledgeChange": "바뀐 내용을 확인했어요",
    "changed": "바뀜",
    "added": "추가됨",
    "removed": "빠짐",
    "checkCwd": "검사를 실행할 폴더 · {value}",
    "checkTimeout": "시간 제한 · {value}초",
    "checkEnvironment": "환경 · 실행한 프로세스의 환경을 이어받아요",
    "checkShell": "셸 · {value}",
    "executionContract": "실행 조건 전체",
    "planBehaviour": "검사 단계 {lane} · 최대 {max}번 시도",
    "planIsolation": "작업 공간 · 배정할 때 공유 폴더 또는 별도 작업 폴더를 골라요",
    "planMerge": "커밋한 결과는 프로젝트에 병합한 뒤 통과시켜요",
    "planReviewers": "검토 담당 일 · {value}",
    "evidenceChanged": "결정을 요청한 뒤 파일이나 근거가 바뀌었어요. 이 결정에는 답할 수 없어요.",
    "legacyDecision": "이전 버전의 결정이에요. 담당자가 검사를 다시 요청하면 새 결정이 나타나요.",
    "preapprovalSubmitted": "승인 전에 제출됨",
    "preapprovalExplanation": "승인 전에 제출된 결과가 있어요 · 승인하면 이어서 검사해요",
    "keyRecover": "확인 키를 새로 만들어요",
    "keyConfirm": "이 컴퓨터에 새 확인 키를 만들어요. 열려 있는 모든 실행에서 계획 승인을 다시 받아요. 이미 실행한 일은 되돌리지 않아요. 승인 없이 새 일을 시작하는 기능은 아니에요.",
    "keyConfirmAction": "확인 키를 새로 만들어요",
    "attemptResult": "{n}번째 시도 · {result}",
    "decisionTab": "{tab}에서 연 결정",
    "reviewCorrection": "검토 의견을 고쳐야 해요",
    "reviewWaiting": "고친 검토 의견을 기다려요",
    "answerChannel": "답한 곳: {source}",
    "attemptPassed": "통과",
    "attemptReturned": "고치러 돌아옴",
    "reviewCorrectionShort": "검토자가 의견을 고쳐요",
    "reviewWaitingShort": "검토자 답을 기다려요",
    "waitForNewQuestion": "담당자가 다시 물어볼 때까지 기다려 주세요.",
    "keyRepinned": "확인 키를 새로 만들었어요. 계획을 한 번 더 승인해 주세요.",
    "oldResults": "승인 전에 제출된 결과예요. 모두 읽고 계속하면 다음 단계에서 검사해요.",
    "whenAfterWork": "일을 마친 뒤, 받아들이기 전에 물어요.",
    "whenDecision": "앞선 일이 끝난 뒤, 다음 일을 시작하기 전에 물어요.",
    "decisionAccept": "허락하면 다음 일이 차례로 시작될 수 있어요: {tasks}.",
    "decisionReject": "허락하지 않으면 계획을 고쳐서 다시 받을 때까지 다음 일을 시작하지 않아요.",
    "ownCheck": "이 검사는 이 일이 직접 쓰는 파일을 실행해요.",
    "plannedCheck": "확인할 것 · {title}",
    "planChangeIds": "결정 {old}에서 {newParticle} 바뀌었어요. 바뀐 항목을 모두 열어 주세요.",
    "beforeAfter": "이전 → 이후",
    "changesRead": "바뀐 항목을 모두 읽었어요.",
    "roleTool": "작업 흐름 프로그램",
    "checkDetails": "실행 설정 자세히",
    "repeatedSteps": "{n}단계가 같은 검사 형식이에요. 각 일의 이름과 파일을 확인해 주세요.",
    "field_run": "명령",
    "field_cwd": "실행 폴더",
    "field_timeout_s": "시간 제한",
    "field_goal": "할 일",
    "field_title": "이름",
    "field_owns": "맡은 파일",
    "field_question": "물을 내용",
    "field_prompt": "물을 내용",
    "field_lens": "검토 관점",
    "field_needs": "앞선 일",
    "field_lane": "검사 단계",
    "scopeCheckResult": "맡은 파일만 고쳤어요",
    "citesCheckResult": "인용한 파일과 줄이 있어요",
    "sourceTerminal": "터미널",
    "sourceDashboard": "대시보드",
    "oldRunReposted": "이전 버전(0.2.1)에서 시작한 실행이에요. 이전 결과를 읽고 계속할 수 있어요.",
    "keyQuestionReplaced": "확인 키를 새로 만들어 이 질문을 교체했어요.",
    "evidenceQuestionReplaced": "근거가 바뀌어 이 질문을 교체했어요.",
    "planChangesRead": "결정 {old}에서 {newParticle} 바뀌었어요. 바뀐 항목을 모두 확인했어요.",
    "authorNote": "계획에 적힌 설명",
    "freeQuestion": "질문 · 통과와 무관",
    "freeEffect": "답은 질문한 쪽에게 전달돼요. 이 답만으로는 아무것도 통과되지 않아요.",
    "answeredQuestion": "답한 결정 · {question} · {outcome} · {answer}",
    "whenTrajectory": "수정이 세 번 이상이거나 시간 초과, 범위 이탈, 되돌림이 있으면 결과를 받기 전에 물어요.",
    "crossFamily": "결과를 받기 전에 작업한 쪽과 다른 모델 계열의 검토가 필요해요.",
    "alsoNodeChecks": "이 검사는 {tasks}의 결과를 받을 때와 전체 결과를 확인할 때 실행돼요.",
    "requirements": "요청한 내용",
    "viewPlan": "계획 보기",
    "ownCheckMark": "⚠ 검사 파일도 수정 가능",
    "ownCheckEffect": "이 일을 하는 쪽이 검사 내용도 바꿀 수 있어요.",
    "holdExact": "통과하지 못한 검사·검토 의견 {n}개가 있어요: {items}. 그래도 받아들일까요?",
    "holdAccept": "이 일을 받아들여요. {tasks} 일을 시작할 수 있어요.",
    "holdReject": "고쳐서 다시 받을 때까지 다음 일을 시작하지 않아요: {tasks}.",
    "returnTrace": "↩ {n}번",
    "inputsReady": "앞선 일은 끝났어요 · 시작을 기다려요",
    "commandDefault": "검사 명령이 성공해요",
    "whos_notStarted": "작업 담당자가 시작해요",
    "whos_running": "작업 담당자가 만들고 있어요",
    "whos_retrying": "작업 담당자가 고치고 있어요",
    "whos_submitted": "진행 담당자가 검사와 검토를 확인해요",
    "whos_passed": "이 일은 끝났어요",
    "whos_awaiting": "내 답을 기다려요",
    "whos_returned": "작업 담당자가 고쳐요",
    "whos_exhausted": "진행 담당자가 계획을 고쳐요",
    "whos_held": "진행 담당자가 남은 확인을 진행해요",
    "whos_preapprovalSubmitted": "계획 승인 뒤 진행 담당자가 확인해요",
    "durationSeconds": "{value}초",
    "visibleTitles": "{n}개 제목이 보여요",
    "moreDetails": "자세히 보기",
    "holdReviewExact": "사람 검토 의견 {n}개가 통과하지 못했어요: {items}. 그래도 받아들일까요?",
    "questionRef": "질문 {id}",
    "freeRead": "읽고 답하기",
    "evDecisionAsked": "결정 요청",
    "questionClosed": "이 질문은 닫혔어요. 최신 내용을 읽어 주세요.",
    "questionsAnswered": "여기서 답한 내용",
    "newPlanDecision": "새 결정 {new}을 확인해 주세요. 바뀐 항목을 모두 열어 주세요.",
    "newPlanRead": "새 결정 {new}의 바뀐 항목을 모두 확인했어요.",
    "planRevisionState": "계획을 고치기를 기다려요",
    "whos_planRevisionState": "담당자가 계획을 고쳐요",
    "refuse": "허락하지 않기",
    "optionalNote": "덧붙일 말이 있으면 적어 주세요",
    "fileUnread": "열기 · {file}",
    "fileRead": "✓ 읽었어요 · {file}",
    "ownCheckCount": "⚠ 검사 {n}개는 자신이 검사하는 파일을 바꿀 수 있어요.",
    "planGraphReason": "그래프의 모든 카드를 읽은 뒤 시작할 수 있어요. 목록이나 상세 창을 닫고 흐름을 살펴봐 주세요.",
    "planRemainingReason": "그래프에서 아직 읽지 않은 카드가 {n}개예요. 스크롤해서 모두 살펴봐 주세요.",
    "checkProgress": "자동 검사 {total}개 중 {passed}개 통과",
    "humanCheckCount": "{n}개는 내가 확인",
    "executionSettings": "시도 횟수와 실행 방식",
    "nodeReference": "일 번호 보기",
    "commitDetails": "제출한 버전 보기",
    "filePath": "파일 위치 보기",
    "freeTab": "{tab}에서 연 질문",
    "freeAnswerHere": "질문 {id} · 읽고 답하기",
    "decisionOnly": "이 결정에는 설명, 근거, 읽을 파일이 없어요.",
    "countPlannedDecision": "내가 결정할 것 {n}개",
    "freeChanged": "질문 내용이나 근거가 바뀌었어요 — 다시 읽어 주세요",
    "keyDecisionReplaced": "확인 키를 새로 만들어 이 결정을 교체했어요.",
    "evidenceDecisionReplaced": "근거가 바뀌어 이 결정을 교체했어요.",
    "freeEvidenceChanged": "질문한 뒤 파일이나 근거가 바뀌었어요. 이 질문에는 답할 수 없어요.",
    "answeredPermission": "허락하기로 답했어요",
    "onlyFinalChecks": "이 검사는 전체 결과를 확인할 때 실행돼요.",
    "permissionNoEvidence": "허락할 내용을 확인할 자료가 없어요. 담당자에게 자료를 요청하거나 허락하지 않을 수 있어요.",
    "permissionConfirmBlind": "자료 없이 이 일을 허락할게요",
    "permissionAcceptBlind": "자료 없이 허락하기",
    "permissionBlindHint": "자료 없이 허락하려면 위 내용을 확인해 주세요."
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
    "returned": "Returned for changes",
    "legend": "Legend",
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
    "submitted": "Waiting for review",
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
    "questionOnly": "This question has no explanation, evidence, or attached files.",
    "writeFirst": "Write an answer to send it.",
    "leaveUnanswered": "Go back without answering",
    "aboutWork": "Work details",
    "decisionRef": "Decision {id}",
    "askedBy": "Asked by: {who}",
    "workedBy": "Worked by: {who}",
    "find": "Find",
    "findHint": "Decision, question, or step name",
    "findNone": "No decision, question, or step matches “{text}”. Select another flow if needed.",
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
    "purposeAuthorization": "Choose whether to permit this work.",
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
    "runChanged": "The flow changed. The answer form and draft were closed.",
    "brand": "Work flow",
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
    "filterReturned": "Returned for changes",
    "onlyNode": "Showing only “{title}”",
    "showAll": "Show all",
    "evStarted": "The run record was created",
    "evPlanned": "Plan posted",
    "evReplanned": "Plan changed · revision {rev}",
    "evRunning": "attempt {n} in progress",
    "evSubmitted": "attempt {n} submitted · waiting to be checked",
    "evPassed": "attempt {n} passed",
    "evReturned": "Attempt {n} · Returned for changes",
    "evReplan": "Attempt {n} · Returned for changes · A revised plan is needed",
    "evNeedsYou": "Attempt {n} · Your turn",
    "evHeld": "attempt {n} · put on hold",
    "evReopened": "reopened",
    "evAsked": "asked",
    "evAnswered": "Answered the question",
    "evFinalPassed": "Whole-result check passed",
    "evFinalFailed": "Whole-result check failed",
    "evLearned": "A lesson was recorded",
    "checksPassed": "{n} automated checks passed",
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
    "sessionT3": "Linked conversation",
    "sessionClaude": "Linked conversation",
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
    "scopeCheck": "whether only assigned files changed",
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
    "planStartEffect": "Let the coordinator start this work.",
    "planBackEffect": "Send changes to the coordinator.",
    "planSentBack": "The plan was sent back",
    "planWaiting": "Review the plan",
    "planSentNote": "Your requested changes",
    "planWaitingRevision": "Waiting for the coordinator’s revised plan.",
    "planChecks": "Automated checks and your review",
    "plannedCommand": "Planned command",
    "planDeliverables": "Deliverables",
    "evSuperseded": "Replaced by a new plan",
    "purposePlan": "Review the plan before work starts.",
    "untitledCheck": "A check without a description",
    "ranCommand": "Command run",
    "returnedBy": "Returned by {who} · {reason} — did not pass",
    "returnedShort": "{reason} · Sent back by {who}",
    "returnLeader": "Leader",
    "returnReviewer": "Reviewer",
    "recordOrder": "Record {n}",
    "results": "View results",
    "resultLocations": "Result files",
    "checkingKey": "◷ Being checked",
    "reviewKey": "⌕ Review work",
    "returnedKey": "↩ Returned for changes",
    "pendingKey": "○ Not started",
    "planChecklist": "{checks} automated checks · {decisions} planned decisions",
    "planReturned": "Returned plan",
    "planUnverified": "Your answer could not be verified",
    "planUnverifiedHelp": "This answer cannot start work. Ask the coordinator to post the plan again, then answer the new decision.",
    "planKeyMismatch": "Approval cannot be verified. This could be a lost/replaced key, a moved project, or altered records; we cannot tell which.",
    "planTampered": "The plan file differs from its record",
    "planTamperedHelp": "The coordinator must post the plan again. Then approve the replacement here.",
    "planGoal": "Actual instruction",
    "planOwns": "Owned files",
    "planNeeds": "Inputs",
    "planReads": "Files to read",
    "planIntegration": "Integration checks",
    "planPromoted": "Fixed checks in this plan",
    "planQuestions": "{decisions} planned decisions · Where will you be asked?",
    "planCardChecks": "{n} automated checks · {first}",
    "planCardDelivery": "Delivers · {files}",
    "planCardQuestion": "{n} decisions · {question}",
    "noPlannedChecks": "No separate checks",
    "supersededNotice": "Decision {old} was replaced by {new}. Read the current plan.",
    "supersededLink": "Read current decision {id}",
    "checkNotMet": "Did not pass · {title}",
    "lineKinds": "Lines",
    "stateKinds": "Task states",
    "markKinds": "Marks",
    "fromTab": "Decision from {tab}",
    "backToTab": "← Back to {tab}",
    "endedAttempt": "Completed attempt",
    "commandScope": "Time limit · {seconds}s",
    "checkPrompt": "Question for you",
    "checkHost": "Tool · {tool} / Expected result · {expect}",
    "planItems": "Items: {n}",
    "answeredPlan": "Agreed to start with this plan",
    "exitSuccess": "Succeeded",
    "exitFailure": "Failed · exit code {n}",
    "planKeyHeading": "The verification key has changed",
    "oldRunApproval": "This run started in an earlier version (0.2.1). Read the reposted plan to continue.",
    "planMissing": "Post a plan first",
    "planMissingHelp": "The coordinator must post the current plan before you can approve it here.",
    "planReplaced": "An unverifiable plan was replaced. Review all work again.",
    "unverifiedAnswer": "Unverified answer · does not count as approval",
    "unverifiedAuthor": "Cannot verify that this answer came from you",
    "planLens": "Review lens",
    "planOutputs": "Outputs",
    "runChecksTitle": "Check the whole result",
    "runChecksAfter": "After all work is finished",
    "runChecksGoal": "Plan goal",
    "runConstraints": "Constraints",
    "countWork": "Work: {n}",
    "countReview": "Reviews: {n}",
    "countDecision": "Decisions: {n}",
    "countChecks": "{n} automated checks",
    "countQuestions": "Questions: {n}",
    "questionsMark": "? A question here",
    "citesCheck": "whether cited files and lines exist",
    "humanCheck": "A person checks the result",
    "hostCheck": "Check in the execution environment",
    "evRepinned": "A new verification key was created. Please approve the plan again.",
    "overviewLevel": "Compact",
    "detailLevel": "Show details",
    "readableFit": "Readable size",
    "overviewHelp": "Titles only. Select a card for details.",
    "planContinue": "Continue",
    "planContinueQuestion": "Continue with this plan?",
    "planContinueEffect": "Keep completed work and continue.",
    "warning": "⚠ Work is paused",
    "keyRecoveryAfter": "If this change was unexpected, check the record with the coordinator first.",
    "copyCommand": "Copy command",
    "copiedCommand": "Copied",
    "projectMoved": "Project location changed",
    "projectMovedHelp": "Moving or renaming a project or run folder invalidates approvals. Ask the coordinator to re-post the current plan, then approve once more.",
    "workRecorded": "Work is recorded. New execution waits until approval is verified.",
    "noWorkRecorded": "No work has been recorded. Execution waits for approval.",
    "planOpen": "Read plan",
    "futureDelivery": "To be received by {who}",
    "visiblePlan": "{total} tasks + final check · {n} titles visible",
    "listAll": "Read the complete list",
    "questionsForNode": "Decisions at this step",
    "findingsOutput": "Review notes",
    "approvalOutput": "Decision",
    "sessionOther": "Work conversation",
    "runNumber": "Run {n}",
    "runResultSummary": "Results · {files}",
    "approvedCommit": "Commit to approve",
    "evidenceHashes": "File verification details",
    "returnedActor": "Sent back by {who}",
    "planChanged": "The plan changed — please review it again",
    "decisionChanged": "The decision or evidence changed — read it again",
    "acknowledgeChange": "I reviewed the changes",
    "changed": "Changed",
    "added": "Added",
    "removed": "Removed",
    "checkCwd": "Run check in · {value}",
    "checkTimeout": "Time limit · {value} seconds",
    "checkEnvironment": "Environment · inherited from the invoking process",
    "checkShell": "Shell · {value}",
    "executionContract": "Full execution contract",
    "planBehaviour": "Lane {lane} · at most {max} attempts",
    "planIsolation": "Workspace · shared tree or Git worktree, selected at assignment",
    "planMerge": "Committed results must be merged into the project before passing",
    "planReviewers": "Review tasks · {value}",
    "evidenceChanged": "Files or evidence changed after this decision was requested. You cannot answer it.",
    "legacyDecision": "This decision is from an older version. Running the gate requests it again.",
    "preapprovalSubmitted": "Submitted before approval",
    "preapprovalExplanation": "A result was submitted before approval · checks resume after approval",
    "keyRecover": "Make a new verification key",
    "keyConfirm": "Creates a new key on this computer. Every open run needs plan approval again. It does not undo completed actions.",
    "keyConfirmAction": "Make a new verification key",
    "attemptResult": "Attempt {n} · {result}",
    "decisionTab": "Decision opened from {tab}",
    "reviewCorrection": "Review findings need correction",
    "reviewWaiting": "Waiting for corrected review findings",
    "answerChannel": "Answered from: {source}",
    "attemptPassed": "Passed",
    "attemptReturned": "Returned for changes",
    "reviewCorrectionShort": "Reviewer corrects findings",
    "reviewWaitingShort": "Waiting for reviewer corrections",
    "waitForNewQuestion": "Please wait for the leader to ask again.",
    "keyRepinned": "A new verification key was created. Please approve the plan again.",
    "oldResults": "These results were submitted before approval. Read each result; continuing allows them to be checked next.",
    "whenAfterWork": "Asked after the work is submitted, before accepting it.",
    "whenDecision": "Asked after prerequisites finish, before dependent work starts.",
    "decisionAccept": "Permitting this releases these steps in order: {tasks}.",
    "decisionReject": "If you decline, downstream work waits until a revised plan is received.",
    "ownCheck": "This check runs files this task may write.",
    "plannedCheck": "Will check · {title}",
    "planChangeIds": "Decision {old} was replaced by {new}. Open each change.",
    "beforeAfter": "Before → after",
    "changesRead": "All changed items have been opened.",
    "roleTool": "Workflow app",
    "checkDetails": "Execution details",
    "repeatedSteps": "{n} steps share a check format. Review each task name and its files.",
    "field_run": "Command",
    "field_cwd": "Working directory",
    "field_timeout_s": "Timeout",
    "field_goal": "Instructions",
    "field_title": "Title",
    "field_owns": "Owned files",
    "field_question": "Prompt",
    "field_prompt": "Prompt",
    "field_lens": "Review lens",
    "field_needs": "Prerequisites",
    "field_lane": "Gate lane",
    "scopeCheckResult": "Only assigned files changed",
    "citesCheckResult": "Cited files and lines exist",
    "sourceTerminal": "Terminal",
    "sourceDashboard": "Dashboard",
    "oldRunReposted": "This run started in an earlier version (0.2.1). Read the earlier results to continue.",
    "keyQuestionReplaced": "A new verification key replaced this question.",
    "evidenceQuestionReplaced": "Changed evidence replaced this question.",
    "planChangesRead": "Decision {old} was replaced by {new}. All changes read.",
    "authorNote": "Plan author’s note",
    "freeQuestion": "Question · Does not approve work",
    "freeEffect": "The answer goes to the asker. This answer alone accepts or releases nothing.",
    "answeredQuestion": "Answered decision · {question} · {outcome} · {answer}",
    "whenTrajectory": "Asked before acceptance after three attempts, a timeout, a scope violation, or a rollback.",
    "crossFamily": "Acceptance requires a review from a different model family than the worker.",
    "alsoNodeChecks": "These checks run when accepting {tasks} and when checking the whole result.",
    "requirements": "Requirements",
    "viewPlan": "View plan",
    "ownCheckMark": "⚠ Check file can also change",
    "ownCheckEffect": "The worker doing this task can also change the check.",
    "holdExact": "{n} checks or review findings did not pass: {items}. Accept anyway?",
    "holdAccept": "This piece is accepted and {tasks} can start.",
    "holdReject": "These steps wait until corrected work is received: {tasks}.",
    "returnTrace": "↩ {n} returns",
    "inputsReady": "Inputs are delivered · waiting to start",
    "commandDefault": "The check command succeeds",
    "whos_notStarted": "The worker starts next",
    "whos_running": "The worker is producing the result",
    "whos_retrying": "The worker is correcting the result",
    "whos_submitted": "The coordinator checks results and reviews",
    "whos_passed": "This piece is finished",
    "whos_awaiting": "Waiting for your answer",
    "whos_returned": "The worker corrects it next",
    "whos_exhausted": "The coordinator revises the plan",
    "whos_held": "The coordinator resolves remaining checks",
    "whos_preapprovalSubmitted": "The coordinator checks it after plan approval",
    "durationSeconds": "{value} seconds",
    "visibleTitles": "{n} titles visible",
    "moreDetails": "Details",
    "holdReviewExact": "{n} human review findings did not pass: {items}. Accept anyway?",
    "questionRef": "Question {id}",
    "freeRead": "Read and answer",
    "evDecisionAsked": "Decision requested",
    "questionClosed": "This question is closed. Read the current question.",
    "questionsAnswered": "Answers given here",
    "newPlanDecision": "Read new decision {new}. Open each change.",
    "newPlanRead": "All changes for new decision {new} have been read.",
    "planRevisionState": "Waiting for a revised plan",
    "whos_planRevisionState": "The coordinator revises the plan",
    "refuse": "Do not permit",
    "optionalNote": "Add a note if you wish",
    "fileUnread": "Open · {file}",
    "fileRead": "✓ Read · {file}",
    "ownCheckCount": "⚠ {n} checks can change the files they check.",
    "planGraphReason": "Read every graph card before starting. Close the list or detail overlay and inspect the flow.",
    "planRemainingReason": "{n} graph cards remain unread. Scroll through the whole flow.",
    "checkProgress": "{passed} of {total} automated checks passed",
    "humanCheckCount": "{n} for you to review",
    "executionSettings": "Attempts and execution",
    "nodeReference": "Step reference",
    "commitDetails": "Submitted version",
    "filePath": "File location",
    "freeTab": "Question opened from {tab}",
    "freeAnswerHere": "Question {id} · Read and answer",
    "decisionOnly": "This decision has no explanation, evidence, or attached files.",
    "countPlannedDecision": "{n} decisions for you",
    "freeChanged": "The question or evidence changed — read it again",
    "keyDecisionReplaced": "A new verification key replaced this decision.",
    "evidenceDecisionReplaced": "Changed evidence replaced this decision.",
    "freeEvidenceChanged": "Files or evidence changed after this question. You cannot answer it.",
    "answeredPermission": "Answered: allow this work",
    "onlyFinalChecks": "These checks run when checking the whole result.",
    "permissionNoEvidence": "There is no evidence for this permission. Ask the coordinator for evidence, or decline permission.",
    "permissionConfirmBlind": "I will allow this work without evidence",
    "permissionAcceptBlind": "Allow without evidence",
    "permissionBlindHint": "To allow without evidence, confirm the statement above."
  }
};
// UI_STRINGS_END

export function contractDiff(before,after,path='') {
  if(JSON.stringify(before)===JSON.stringify(after))return [];
  if(before && after && typeof before==='object' && typeof after==='object')return [...new Set([...Object.keys(before),...Object.keys(after)])].flatMap(k=>contractDiff(before[k],after[k],path?path+'.'+k:k));
  return [{field:path,before:before??'—',after:after??'—'}];
}
export function releasedNodes(nodes,id) {
  const reached=new Set([id]);let changed=true;
  while(changed){changed=false;for(const n of nodes)if(!reached.has(n.id)&&(n.needs?.some(x=>reached.has(x.from))||n.target&&reached.has(n.target))){reached.add(n.id);changed=true;}}
  return nodes.filter(n=>n.id!==id&&reached.has(n.id));
}
export function stateCounts(nodes,decisions){const counts={};for(const n of nodes){const key=displayState(n,decisions);counts[key]=(counts[key]||0)+1;}return counts;}
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
export function decisionHasEvidence(view, decision) {
  const node=view?.nodes?.find(n=>n.id===decision.node);
  return !!(decision.files?.length || decision.has_evidence || decision.failed?.length || decision.verified?.length || decision.unverified?.length || decision.worker_note || Object.values(decision.context||{}).some(Boolean) || Object.values(decision.author_context||{}).some(Boolean) || (!decision.free && view?.timeline?.some(r=>r.kind==='attempt'&&r.node===decision.node&&r.attempt===node?.attempts&&r.checks?.length)));
}
export function nothingToJudge(view, decision) {
  return decision.purpose !== 'plan_approval' && !decision.free && !['direction','information'].includes(decision.kind) && !decisionHasEvidence(view,decision);
}
export function canApprove(session) {
  if (session?.purpose === 'plan_approval') return true;
  if(session?.decision?.free)return true;
  if (session?.nothingToJudge) return !!session.blindConfirmed;
  return !!session && (!(session.purpose === 'lane3' || session.purpose === 'authorization' ||
    session.kind === 'authorization' || session.purpose === 'hold' || session.failed?.length || session.decision?.files?.length || session.decision?.has_evidence) || session.detailsOpened || (!(session.purpose === 'hold' || session.failed?.length) && session.fileOpened));
}
export function decisionQuestion(d, language="en") {
  if(d.node&&d.purpose==='hold'&&!d.free&&d.failed?.length)return STRINGS[language][d.failed_reviews===d.failed.length?'holdReviewExact':'holdExact'].replace('{n}',d.failed.length).replace('{items}',d.failed.join('; '));
  const generated = `Approve ${d.record_purpose ?? d.purpose} for ${d.node}?`;
  const made = ['human_check', 'trajectory', 'lane3'].includes(d.record_purpose ?? d.purpose);
  return made && d.node && d.question === generated ? '' : d.question;
}
export function renderCheckInputs(parent,check,language,create) {
  let more;
  for(const [key,value] of Object.entries(checkExecutionFields(check,language))) {
    const row=create(key==='run'?'pre':'p',value,key==='run'?'planned-command':'check-input');
    row.dataset.input=key;if(key==='run')parent.append(row);else{if(!more){more=create('details',undefined,'execution-details');more.append(create('summary',STRINGS[language].checkDetails));parent.append(more);}more.append(row);}
  }
}
export function checkExecutionFields(c,language='en') {
  const words=STRINGS[language], format=(key,value)=>words[key].replace('{value}',String(value));
  return {run:c.run ?? c.command,cwd:format('checkCwd',c.cwd),timeout_s:format('checkTimeout',c.timeout_s),
    environment:words.checkEnvironment,shell:format('checkShell',c.shell)};
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
      if(!session.changed)update(decision); return session;
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
      const reason = !sameRun(session.target, chosen) ? 'runChanged' : !current() ? (session.decision.free?'questionClosed':'decisionClosed') : '';
      if (reason) session = null;
      else { const next=view.decisions.find(d => d.id === session.target.id);
        if(JSON.stringify(next.identity)!==JSON.stringify(session.decision.identity)){session.changed=true;session.nextDecision=next;}
        else update(next);
      }
      return reason;
    },
    acknowledge() { if(session?.changed){session.changed=false;session.detailsOpened=false;session.fileOpened=false;session.blindConfirmed=false;update(session.nextDecision);} },
    setDraft(text) { if (session && !session.busy) session.draft = text; },
    openDetails() { if (current()) session.detailsOpened = true; },
    openFile() { if (current()) session.fileOpened = true; },
    confirmBlind(value) { if (current()) session.blindConfirmed = !!value; },
    canSubmit(outcome, text = session?.draft || '') {
      if (!current() || session.busy || session.changed) return false;
      const question = ['direction','information'].includes(session.kind);
      if (question ? outcome !== 'answered' : !['approved','revision_requested','rejected'].includes(outcome)) return false;
      return outcome === 'approved' ? canApprove(session) : outcome === 'rejected' && session.decision.record_purpose === 'node' ? true : !!text.trim();
    },
    buildRequest(outcome, text = session?.draft || '') {
      if (!controller.canSubmit(outcome, text)) return null;
      session.draft = text; session.busy = true;
      const request = {...session.target, outcome, answer:text.trim(), displayed:session.decision.identity};
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
// Both levels use at least 14px text; 6/7 keeps it at least 12px on screen.
export const MIN_FIT_SCALE = 6 / 7;
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
export const STATE_VOCABULARY = Object.fromEntries(['notStarted','running','retrying','submitted','passed','awaiting','returned','exhausted','held','preapprovalSubmitted','planRevisionState'].map(state=>[state,{name:state,whoseMove:'whos_'+state}]));
export function stateWords(state, language='en') {
  const entry=STATE_VOCABULARY[state] || STATE_VOCABULARY.notStarted;
  return {name:STRINGS[language][entry.name],whoseMove:STRINGS[language][entry.whoseMove]};
}
export function particle(value, pair='이/가') {
  const text=String(value), last=text.at(-1)||'', digit='영일이삼사오육칠팔구';
  const char=/[0-9]/.test(last)?digit[Number(last)]:last, code=char.charCodeAt(0)-0xac00;
  const final=code>=0&&code<11172?code%28: /[bcdfghjklmnpqrstvwxyz]/i.test(char)?1:0;
  const [closed,open]=pair.split('/'); return text+(final && !(pair==='으로/로'&&final===8)?closed:open);
}
export function durationDiff(field, language='en') {
  const format=value=>field.field.split('.').at(-1)==='timeout_s'&&typeof value==='number'?STRINGS[language].durationSeconds.replace('{value}',value):String(value);
  return format(field.before)+' → '+format(field.after);
}
export function displayState(node, decisions = []) {
  if(node.plan_revision_wait)return 'planRevisionState';
  if(node.preapproval_submission)return 'preapprovalSubmitted';
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
  return {planRevisionState:'Ⅱ',preapprovalSubmitted:'⇥', passed:'✓', running:'▶', retrying:'↪', submitted:'◷', awaiting:'◆', returned:'↩', notStarted:'○', exhausted:'!', held:'Ⅱ'}[state];
}
export function commandTitle(check) {
  const command = check.command || check.run;
  return !!command && (!check.title || check.title === check.id || check.title === command || [STRINGS.ko.commandDefault, STRINGS.en.commandDefault].includes(check.title));
}
export function snapTitleOffset(position,size,maximum,titles){
  const intervals=titles.flatMap(([a,b])=>[[a,b],[a-size,b-size]]).sort((a,b)=>a[0]-b[0]);
  const merged=[];
  for(const [a,b] of intervals){const last=merged.at(-1);if(last&&a<last[1]-.01)last[1]=Math.max(last[1],b);else merged.push([a,b]);}
  const hit=merged.find(([a,b])=>position>a+.01&&position<b-.01);if(!hit)return position;
  const candidates=hit.filter(v=>v>=0&&v<=maximum);
  return candidates.sort((a,b)=>Math.abs(a-position)-Math.abs(b-position))[0]??position;
}
export function checkTitle(check, language = 'en') {
  if(!check.title&&['scope','cites'].includes(check.type||check.id)&&check.result==='passed')return STRINGS[language][(check.type||check.id)+'CheckResult'];
  return commandTitle(check) ? check.command || check.run : check.title && check.title !== check.id ? check.title : check.command || check.run || check.prompt || STRINGS[language][{scope:'scopeCheck',cites:'citesCheck',human:'humanCheck',host:'hostCheck'}[check.type || check.id]] || check.id;
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
export function intersectsViewport(rect, width, height) {
  return rect.x < width && rect.y < height && rect.x + rect.width > 0 && rect.y + rect.height > 0;
}
const textWidth = (text, wide, narrow) => Array.from(text || '').reduce((sum, c) => sum + (c.charCodeAt(0) > 0x2e80 ? wide : narrow), 0);
export function overviewMarkText(marks) {
  const text=marks.join(' · ');
  return textWidth(text,14,8)>134 ? marks.map(mark=>Array.from(mark)[0]).join(' · ') : text;
}
export function fitScale(bounds, width, height, mobile = false) {
  const available = Math.min(width / bounds.width, height / bounds.height);
  return Math.max(MIN_FIT_SCALE, Math.min(1, available));
}
// A fixed level is used for selection resizing; only opening and Fit choose a richer level.
export function fitGraph(layouts, width, height, fixedLevel = null) {
  for (const level of fixedLevel ? [fixedLevel] : ['detail', 'overview']) {
    const layout = layouts[level], scale = fitScale(layout.bounds, width, height);
    const fits = layout.bounds.width * scale <= width && layout.bounds.height * scale <= height;
    if (fits || level === (fixedLevel || 'overview')) return {level, scale, fits};
  }
}
export function zoomLevel(level, scale, amount) {
  const next = scale + amount;
  if (level === 'overview' && next > 1) return {level:'detail', scale:1};
  if (level === 'detail' && next < MIN_FIT_SCALE) return {level:'overview', scale:1};
  return {level, scale:Math.max(MIN_FIT_SCALE, Math.min(level === 'overview' ? 1 : 1.6, next))};
}
// Preserve the nearest card's local point when its layout changes size.
export function mapAnchor(before, after, point) {
  const rects = before.cardRects;
  const distance = r => Math.hypot(Math.max(r.x-point.x,0,point.x-r.x-r.width), Math.max(r.y-point.y,0,point.y-r.y-r.height));
  const rect = [...rects].sort((a,b)=>distance(a)-distance(b))[0];
  if (!rect || !after.positions[rect.id]) return point;
  const next = after.positions[rect.id];
  return {x:next.x+(point.x-rect.x)*next.width/rect.width, y:next.y+(point.y-rect.y)*next.height/rect.height};
}
export function planCounts(counts = {}, language = 'en', details = false) {
  const keys = [['work','countWork'],['review','countReview'],['decision','countDecision']];
  if (details) keys.push(['checks','countChecks'],['decisions','countPlannedDecision']);
  return keys.filter(([key]) => counts[key] > 0).map(([key,word]) => STRINGS[language][word].replace('{n}',counts[key])).join(' · ');
}
export function planFlow(data, language = 'en') {
  if (!data.nodes.length || data.plan_error) return data;
  const id = '_run_checks', strings = STRINGS[language];
  const checks = [...(data.integration_checks || []), ...(data.promoted_checks || [])];
  const node = {id, kind:'goal', title:strings.runChecksTitle, summary:strings.runChecksAfter,
    goal:data.goal, runLevel:true, plan_revision_wait:data.nodes.some(n=>n.plan_revision_wait), status:data.complete?'passed':'pending', attempts:0,
    owns:[], needs:[], reads:[], declared_outputs:[], inputs:[], outputs:[], deliverables:[],
    planned_checks:checks, returned_reasons:[], laps:[]};
  const forward = forwardEdges(data.edges), terminal = data.nodes.filter(n => !forward.some(e => e.from === n.id));
  return {...data, nodes:[...data.nodes,node], edges:[...data.edges,...terminal.map(n=>({
    from:n.id,to:id,relation:'hands_over',label:'',gate:n.status==='passed'?'open':'closed',delivered:n.status==='passed'}))]};
}

export function fitStart(layout, width, height, scale, nodes = [], plan = true) {
  if (layout.bounds.width*scale<=width && layout.bounds.height*scale<=height) return {left:0,top:0};
  const id = !plan && layout.order.find(id => nodes.some(n => n.id === id && !n.runLevel && n.status !== 'passed' && !n.answered));
  const first=layout.positions[id || layout.order[0]];
  return first?{left:Math.max(0,first.x*scale-28),top:Math.max(0,first.y*scale-28)}:{left:0,top:0};
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
export function detailCardHeight(node) {
  const facts=(node.deliverables?.length?1:0)+(node.planned_checks?.length?1:0)+(node.runLevel?1:0);
  return 112+facts*27+(node.kind==='review'||node.reviewers?.length?28:0)+(node.planned_checks?.some(c=>c.type==='human')||node.kind==='decision'?27:0);
}
export function layeredLayout(nodes, edges, decisions = [], sort = true, options = {}) {
  const overview = options.level === 'overview', portGap = 20, inset = overview ? 12 : 26;
  const byId = new Map(nodes.map(n => [n.id, n])), vertices = new Map(), links = [];
  const routes = forwardEdges(edges).filter(e => byId.has(e.from) && byId.has(e.to)).map((e,index) => {
    const waiting = decisions.find(d => d.node === e.from);
    return {...e,index,bundle:index,text:overview?'':edgeChipText(e),chip:null,gateState:waiting?'waiting_for_you':e.gate==='returned'?'closed':e.gate||'closed',decision:waiting?.id};
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
  const widths=layers.map(ids=>overview?156:Math.max(264,...ids.filter(id=>byId.has(id)).map(id=>Math.min(280,Math.ceil(textWidth(byId.get(id).title,18,9))+40))));
  for(const v of vertices.values()) {
    v.width=widths[v.layer];
    const degree=Math.max(links.filter(e=>e.from===v.id).length,links.filter(e=>e.to===v.id).length);
    const portHeight=(options.clearance||0)+40+portGap*(degree+2*Math.max(0,degree-3));
    v.height=overview ? (v.dummy ? 28 : Math.max(64,portHeight)) : v.dummy?44:Math.max(detailCardHeight(v.node),portHeight)+Math.max(0,Math.ceil(textWidth(v.node.title,18,9)/(v.width-40))-1)*26;
  }
  const gap=overview?16:18,margin=20;
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
  layers.forEach((ids,d)=>{for(const id of ids)vertices.get(id).x=x;x+=widths[d]+Math.max(overview?56:108,inset*2+((channels[d]?.length||0)+1)*20);});
  // Distinct horizontal ordinates prevent a target lead from joining an unrelated source lead.
  const usedY=[];
  const ordinate=(ideal,low,high,edge,channels)=>{
    for(let step=0;step<10000;step++){
      const y=ideal+(step%2?1:-1)*Math.ceil(step/2)*portGap;
      if(y>=low && y<=high && usedY.every(n=>n.edge===edge||!n.channels.some(c=>channels.includes(c))||Math.abs(n.y-y)>=portGap)){usedY.push({y,edge,channels});return y;}
    }
    // Dense fans can leave free ports between the regular spacing grid.
    const free=Array.from({length:Math.max(0,Math.floor(high)-Math.ceil(low)+1)},(_,i)=>Math.ceil(low)+i).sort((a,b)=>Math.abs(a-ideal)-Math.abs(b-ideal));
    for(const y of free)if(usedY.every(n=>n.edge===edge||!n.channels.some(c=>channels.includes(c))||Math.abs(n.y-y)>=portGap)){usedY.push({y,edge,channels});return y;}
    throw new Error('Graph ports exceed card capacity');
  };
  try {
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
  } catch(error) {
    if((options.clearance||0)>routes.length*80)throw error;
    return layeredLayout(nodes,edges,decisions,sort,{...options,clearance:(options.clearance||0)+40});
  }
  const segmentCross=(a,b,c,d)=>a.y===b.y&&c.x===d.x&&c.x>Math.min(a.x,b.x)&&c.x<Math.max(a.x,b.x)&&a.y>Math.min(c.y,d.y)&&a.y<Math.max(c.y,d.y);
  const parts=[];
  channels.forEach((channel,d)=>{
    const right=vertices.get(layers[d][0]).x+widths[d],next=vertices.get(layers[d+1][0]).x;
    const pieces=channel.map(e=>{const r=routes[e.route],a=vertices.get(e.from),b=vertices.get(e.to);return {route:r.index,a:a.dummy?{x:a.x+a.width,y:a.port}:r.start,b:b.dummy?{x:b.x,y:b.port}:r.end};});
    const points=(p,i)=>{const track=right+inset+(next-right-inset*2)*(i+1)/(pieces.length+1);return [p.a,{x:track,y:p.a.y},{x:track,y:p.b.y},p.b];};
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
  if(overview && options.wrapLongChains && layers.length>8 && layers.every(ids=>ids.length===1 && byId.has(ids[0]))) {
    const columns=7, rowHeight=120;
    layers.forEach((ids,i)=>{Object.assign(positions[ids[0]],{x:margin+(i%columns)*212,y:margin+Math.floor(i/columns)*rowHeight});});
    for(const r of routes){const a=positions[r.from],b=positions[r.to],start={x:a.x+a.width,y:a.y+a.height/2},end={x:b.x,y:b.y+b.height/2};
      r.start=start;r.end=end;r.chip=null;
      r.points=a.y===b.y?[start,end]:[start,{x:start.x+18,y:start.y},{x:start.x+18,y:b.y-24},{x:b.x-12,y:b.y-24},{x:b.x-12,y:end.y},end];}
    cardRects.splice(0,cardRects.length,...Object.entries(positions).map(([id,p])=>({id,...p})));
    return {positions,layers:layers.map(ids=>ids.filter(id=>byId.has(id))),order:layers.flat(),routes,chips:[],cardRects,
      terminals:nodes.filter(n=>!routes.some(r=>r.from===n.id)).map(n=>n.id),
      bounds:{width:Math.max(...cardRects.map(p=>p.x+p.width))+margin+20,height:Math.max(...cardRects.map(p=>p.y+p.height))+margin},vertical:false};
  }
  return {positions,layers:layers.map(ids=>ids.filter(id=>byId.has(id))),order:layers.flat().filter(id=>byId.has(id)),routes,chips,cardRects,
    terminals:nodes.filter(n=>!routes.some(r=>r.from===n.id)).map(n=>n.id),
    bounds:{width:Math.max(100,...cardRects.map(p=>p.x+p.width+margin)),height:tallest+margin*2},vertical:false};
}

export function compactOverview(layout,width) {
  if(layout.bounds.width*MIN_FIT_SCALE<=width)return layout;
  const margin=20,gap=36,cardWidth=156,columns=Math.max(1,Math.floor((width/MIN_FIT_SCALE-margin*2+gap)/(cardWidth+gap)));
  const height=80,rowHeight=height+36;
  const positions={};layout.order.forEach((id,i)=>{positions[id]={...layout.positions[id],x:margin+(i%columns)*(cardWidth+gap),y:margin+Math.floor(i/columns)*rowHeight,width:cardWidth,height};});
  const routes=layout.routes.map((r,i)=>{
    const a=positions[r.from],b=positions[r.to],start={x:a.x+a.width,y:a.y+a.height/2},end={x:b.x,y:b.y+b.height/2};
    const lead=8+(i%4)*3;
    const points=a.y===b.y&&b.x===a.x+cardWidth+gap?[start,end]:[start,{x:start.x+lead,y:start.y},{x:start.x+lead,y:a.y+a.height+24},{x:end.x-lead,y:a.y+a.height+24},{x:end.x-lead,y:end.y},end];
    return {...r,start,end,points,chip:null};
  });
  const cardRects=layout.order.map(id=>({id,...positions[id]}));
  return {...layout,positions,routes,chips:[],cardRects,bounds:{width:Math.max(...cardRects.map(r=>r.x+r.width))+margin,height:Math.max(...cardRects.map(r=>r.y+r.height))+margin}};
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
const t = (key, values = {}) => Object.entries({...values,...(values.new?{newParticle:particle(values.new,'으로/로')}:{}),...(values.who?{whoSubject:particle(values.who)}:{})}).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, String(value)), STRINGS[language][key]);
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
function flowNode(id) { return planFlow(view,language).nodes.find(n => n.id === id); }
let queuedRefresh = false;
let timer = 0, loading = false, generation = 0, renderer = null;
const decisionController = createDecisionController();
let decisionUI = null, decisionNotice = '', cameFrom = 'flow';

async function api(path, body, text = false) {
  const response = await fetch(path, {method: body ? 'POST' : 'GET', headers: {'X-GF-Token': token, ...(body ? {'Content-Type':'application/json'} : {})}, ...(body ? {body:JSON.stringify(body)} : {})});
  if (!response.ok) { const err = new Error('request'); err.status = response.status; try{err.code=(await response.json()).code;}catch{} throw err; }
  return text ? response.text() : response.json();
}
function query(route, extra = {}, target = chosen) { return route + '?' + new URLSearchParams({project:target.project, run:target.run, ...extra}); }
let replacementDecision = null;
function notice(key, retry = false) { const box = $('notice'); clear(box); box.hidden = !key; if (key) box.append(el('span', STRINGS[language][key] === undefined ? key : t(key))); if (retry) box.append(button(t('retry'), () => refresh(true))); if(key && replacementDecision && !planBlocked())box.append(button(t('supersededLink',{id:replacementDecision}),()=>openDecision(replacementDecision),'primary')); }
function title(node) { return node && node.title && node.title !== node.id ? node.title : t('unnamed'); }
function otherTitle(value) { return view.nodes.some(n => n.id === value && n.title === value) ? t('unnamed') : value || t('unnamed'); }
// Legacy plans may have only an artifact path; keep that technical fallback out of normal views.
function outputLabel(value) { return ({findings:t('findingsOutput'),approval:t('approvalOutput')})[value] || value; }
function label(value) { value=outputLabel(value); return !value || /[\/\\]|\.[a-z0-9]{1,8}$/.test(value) || view.nodes.some(n => n.id === value) ? t('handoff') : value; }
function relationText(edge) { return edgeRelationLabel({...edge,label:edge.label?label(edge.label):''},language); }
function question(d) { return decisionQuestion(d, language); }
function decisionTitle(d) { return title(view.nodes.find(n => n.id === d.node)); }
// The same words an agent session uses for this decision, so either side can find the other.
function sessionName(session) {
  const host = /^(t3|claude):(.+)$/.exec(session || '');
  if (host) return t(host[1] === 't3' ? 'sessionT3' : 'sessionClaude', {id:host[2].slice(0, 8)});
  return session === 'dashboard' ? t('sessionDashboard') : session ? t('sessionOther') : '';
}
function who(actor) {
  const role = {leader:'roleLeader', worker:'roleWorker', reviewer:'roleReviewer', human:'roleHuman', tool:'roleTool'}[actor?.role];
  return [...new Set([role ? t(role) : sessionName(actor?.session)].filter(Boolean))].join(' · ');
}
// The log groups dates separately so every timestamp has the same width.
function clock(stamp, seconds = false) {
  const time = stamp ? new Date(stamp) : null; if (!time || isNaN(time)) return '';
  return time.toLocaleTimeString(language, {hour:'2-digit', minute:'2-digit', ...(seconds?{second:'2-digit'}:{}), hour12:false});
}
// An id the agent also says. Pressing it copies the words to paste back into the chat.
function refChip(id, say, decision = false, free = false) {
  const chip = button(t(free ? 'questionRef' : decision ? 'decisionRef' : 'nodeRef', {id}), async event => {
    event.stopPropagation();
    // Said once; the next refresh puts back whatever the page has to report.
    try { await navigator.clipboard.writeText(say); notice(t('copied', {text:say})); } catch { notice(t('copyFailed', {text:say})); }
  }, 'ref' + (free ? ' question-ref' : decision ? ' decision-ref' : ''));
  chip.title = t('copyHint'); chip.setAttribute('aria-label', `${id}. ${t('copyHint')}`); return chip;
}
function workedBy(n) { return [n.worker?.model&&![STRINGS.ko.roleWorker,STRINGS.ko.roleLeader,STRINGS.en.roleWorker,STRINGS.en.roleLeader].includes(n.worker.model) ? t('modelName',{model:n.worker.model}) : t('roleWorker')].filter(Boolean).join(' · '); }
function decisionHeading(parent, d, tag) {
  const reference = el('p', undefined, 'ref-line'); reference.append(refChip(d.id, `${d.id} · ${decisionTitle(d)}`, true, d.free));

  const asker = who(d.asked_by?{role:d.asked_by.role}:null);
  const origin=asker?t('askedBy',{who:asker}):'';
  if(origin)reference.append(el('span',origin));
  if(d.free)parent.append(el('p',t('freeQuestion',{who:who(d.asked_by)}),'free-question'),el('p',t('freeEffect')));
  parent.append(reference, el('p', t('decisionWork',{title:decisionTitle(d)}), 'decision-work'));
  parent.append(el(tag, question(d) || purposeWording(d.purpose,language), 'decision-question'));
  if (!d.free && d.purpose === 'trajectory') textList(parent, (d.trajectory_reasons || []).map(key => t(key)));
}
function needs(node) { return view.decisions.some(d => d.node === node.id); }
function status(node) { return stateWords(displayState(node,view.decisions),language).name; }
function attempts(node) { if(['decision','goal'].includes(node.kind))return ''; return node.status==='passed' && node.attempts ? t(node.attempts===1?'firstPass':'finishedAttempts',{n:node.attempts}) : t(node.attempts?'attempt':'unusedAttempts', {n:node.attempts||0, max:node.max_attempts||3}); }
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
  c.append(button(t(d.free?'freeRead':'read'), () => openDecision(d.id), d.free?'':'primary')); return c;
}
function handoffsCard(key, rows, direction) {
  const c = card(t(key)); const list = el('ul');
  if (!rows.length) c.append(el('p', t('noHandoffs')));
  for (const row of rows) list.append(el('li', `${label(row.label)} · ${t(direction)} ${otherTitle(row.other_title)} · ${t(row.delivered ? 'delivered' : 'notDelivered')}`));
  c.append(list); return c;
}
function contractDetails(parent,contract) {
  const details=el('details');details.append(el('summary',t('executionContract')),el('pre',JSON.stringify(contract,null,2)));parent.append(details);
}
function plannedChecks(parent, checks) {
  const list = el('ul', undefined, 'checks planned-checks');
  for (const c of checks || []) {
    const item = el('li'); if(!commandTitle(c))item.append(el('strong',t('plannedCheck',{title:checkTitle(c,language)}))); if(c.runs_own_files)item.append(el('p',t('ownCheckMark'),'own-check-note'),el('p',t('ownCheckEffect')));
    if ((!c.type || c.type === 'cmd') && c.command) {
      item.append(el('p',t('plannedCommand'),'muted'));
      renderCheckInputs(item,c,language,el);
    }
    if (c.type === 'human' && c.prompt) item.append(el('p', t('whenAfterWork') + ' ' + t('checkPrompt') + ' · ' + c.prompt));
    if (c.type === 'host') item.append(el('p', t('checkHost', c)));
    list.append(item);
  }
  if (!list.children.length) list.append(el('li', t('noPlannedChecks')));
  parent.append(list);
}
function authorNote(parent,context) {
  if(!Object.values(context||{}).some(Boolean))return;
  const note=card(t('authorNote'));for(const [key,value] of Object.entries(context))if(value)note.append(el('p',t({why:'why',if_approved:'ifApproved',if_rejected:'ifRejected',undo:'undo'}[key])+' · '+value));parent.append(note);
}
function plannedQuestion(q) {
  return q.answered?t('answeredQuestion',{...q,outcome:t(q.outcome==='approved'?(q.kind==='authorization'?'answeredPermission':'answeredApproval'):q.outcome==='answered'?'evAnswered':'answeredRevision'),answer:q.answer||''}):t(q.when==='node'?'whenDecision':q.when==='trajectory'?'whenTrajectory':'whenAfterWork')+' '+q.question;
}
function runFacts(parent) {
  contractDetails(parent,view.run_contract);
  if(view.summary)parent.append(el('p',view.summary));authorNote(parent,view.context);
  if(view.requirements?.length){parent.append(el('h3',t('requirements')));textList(parent,view.requirements.map(r=>r.id+' · '+r.text));}
  if(view.integration_checks?.length||view.promoted_checks?.length)parent.append(el('p',t(view.nodes.some(n=>n.kind==='work'&&n.lane>=2)?'alsoNodeChecks':'onlyFinalChecks',{tasks:view.nodes.filter(n=>n.kind==='work'&&n.lane>=2).map(title).join(', ')})));
  parent.append(el('h3',t('runChecksGoal')),el('p',view.goal));
  for (const [key, checks] of [['planIntegration',view.integration_checks],['planPromoted',view.promoted_checks]]) {
    if (checks?.length) { parent.append(el('h3',t(key))); plannedChecks(parent,checks); }
  }
  if (view.constraints?.length) { parent.append(el('h3',t('runConstraints'))); textList(parent,view.constraints); }
  if (view.planned_questions?.length) {
    parent.append(el('h3',t('planQuestions',view.plan_counts)));
    for (const q of view.planned_questions) { const row=el('p'); row.append(button(otherTitle(flowNode(q.node)?.title),()=>selectNode(q.node),'link'),el('span',' · '+plannedQuestion(q))); parent.append(row); }
  }
}
function planFacts(parent, node) {
  if (node.runLevel) { runFacts(parent); return; }
  if(node.goal && node.goal!==title(node))parent.append(el('h3', t('planGoal')), el('p', node.goal));
  authorNote(parent,node.context);if(node.requirement)parent.append(el('h3',t('requirements')),el('p',node.requirement));
  const questions=(view.planned_questions||[]).filter(q=>q.node===node.id);
  if(questions.length){parent.append(el('h3',t(questions.every(q=>q.answered)?'questionsAnswered':'questionsForNode')));textList(parent,questions.map(q=>plannedQuestion(q)));}
  if(!questions.some(q=>q.answered)&&node.kind==='decision' && ['review','authorization'].includes(node.contract.decision_kind)){parent.append(el('p',t('decisionAccept',{tasks:dependentTitles(node.id)})),el('p',t('decisionReject')));}
  renderPlanDiff(parent,node.id);
  parent.append(el('h3', t('planOwns'))); textList(parent,node.owns || []);
  parent.append(el('h3', t('planNeeds')));
  const inputs=(node.needs || []).map(n => `${n.artifact} · ${t('from')} ${otherTitle(flowNode(n.from)?.title || n.from)}`);
  if(node.target && !node.needs?.some(n=>n.from===node.target)) inputs.push(otherTitle(flowNode(node.target)?.title));
  textList(parent,[...inputs,...(node.reads || [])]);
  parent.append(el('h3', t('planOutputs')));
  textList(parent,[...new Set([...(node.declared_outputs || []),...(node.outputs || []).map(n=>n.label).filter(Boolean)].map(outputLabel))]);
  parent.append(el('h3', t('planChecks'))); plannedChecks(parent, node.planned_checks);
  if(node.kind==='work'&&node.lane>=2){parent.append(el('p',t('crossFamily')));if(view.integration_checks?.length||view.promoted_checks?.length){parent.append(el('p',t(view.nodes.some(n=>n.kind==='work'&&n.lane>=2)?'alsoNodeChecks':'onlyFinalChecks',{tasks:view.nodes.filter(n=>n.kind==='work'&&n.lane>=2).map(title).join(', ')})));plannedChecks(parent,[...(view.integration_checks||[]),...(view.promoted_checks||[])]);}}
  if (node.lens) parent.append(el('h3',t('planLens')),el('p',node.lens));
  if(node.kind!=='decision'){const settings=el('details');settings.append(el('summary',t('executionSettings')),el('p',t('planBehaviour',{lane:node.lane,max:node.max_attempts})),el('p',t('planIsolation')),el('p',t('planMerge')));parent.append(settings);}
  if(node.reviewers?.length)parent.append(el('p',t('planReviewers',{value:node.reviewers.map(id=>otherTitle(flowNode(id)?.title||id)).join(', ')})));
  contractDetails(parent,node.contract);
}
function planBlocked() { if(!view)return false; const a=view.plan_approval; return !!(view.plan_error || view.key_mismatch || view.location_mismatch || a && !(a.status==='answered' && a.verified && a.outcome==='approved')); }
function problemTitle() { const a=view.plan_approval; return t(view.location_mismatch?'projectMoved':view.key_mismatch?'planKeyHeading':view.plan_error?'planTampered':!a?.id?'planMissing':a.status==='answered'&&!a.verified?'planUnverified':a.status==='open'?(view.has_work?'planContinueQuestion':'planWaiting'):'planSentBack'); }
function returnedLine(n) {
  const row=[...view.timeline].reverse().find(r=>r.node===n.id&&r.kind==='attempt'&&r.attempt===n.attempts);
  const failure=row?.checks?.find(c=>c.result==='failed');
  return checkWording(failure || {title:n.returned_reason || t('noReason'),result:'failed'},language);
}
let planBanner = null, planSeen=null, planChanges=null, planChangeIds=null;
const planRead = new Set();
const graphRead = new Set();let graphReadIdentity='';
function graphReadReason() {
  if(mode!=='flow'||$('accessible').open||(matchMedia('(max-width:760px)').matches&&selected))return t('planGraphReason');
  const remaining=planFlow(view,language).nodes.filter(n=>!graphRead.has(n.id)).length;
  return remaining?t('planRemainingReason',{n:remaining}):'';
}
function recordGraphRead() {
  if(!view||!planBlocked()||mode!=='flow'||$('accessible').open||(matchMedia('(max-width:760px)').matches&&selected))return;
  const identity=JSON.stringify(view.plan_approval?.identity);
  if(identity!==graphReadIdentity){graphRead.clear();graphReadIdentity=identity;}
  const phone=matchMedia('(max-width:760px)').matches&&!$('flow').classList.contains('phone-diagram');
  const viewport=phone?{left:0,top:0,right:innerWidth,bottom:innerHeight-(document.querySelector('.plan-actions')?.offsetHeight||0)}:document.querySelector('.map-viewport')?.getBoundingClientRect();
  if(!viewport)return;
  const top=Math.max(viewport.top,document.querySelector('#attention.plan-banner')?.getBoundingClientRect().bottom||0);
  for(const card of document.querySelectorAll(phone?'#phone-flow .node-card':'#map .node-card')){
    const r=card.getBoundingClientRect();
    if(r.width&&r.left>=viewport.left-.5&&r.right<=viewport.right+.5&&r.top>=top-.5&&r.bottom<=viewport.bottom+.5)graphRead.add(card.dataset.node);
  }
  planBanner?.update?.();
}
addEventListener('scroll',recordGraphRead,{passive:true});
$('accessible').addEventListener('toggle',()=>{planBanner?.update?.();recordGraphRead();});
function dependentTitles(id){return releasedNodes(view.nodes,id).map(title).join(', ') || t('runChecksTitle');}
function diffText(field){const key='field_'+field.field.split('.').at(-1);return (STRINGS[language][key]||field.field)+' · '+durationDiff(field,language);}
function renderPlanDiff(parent,id){
  const change=planChanges?.find(c=>c.id===id);if(!change)return;
  const box=el('section',undefined,'plan-diff');box.append(el('h3',t('beforeAfter')));
  for(const field of change.fields||[])box.append(el('p',diffText(field)));parent.append(box);
}
function unreadPlanChanges(){return !!planChanges?.some(c=>!planRead.has(c.id));}
function readPlanChange(id){planRead.add(id);planBanner?.update?.();}


function planAttention(box) {
  const approval = view.plan_approval;
  const blocked = planBlocked();
  if (!blocked) { planBanner = null; return false; }
  box.hidden = false; box.classList.add('plan-banner');
  const key = JSON.stringify([mode, chosen, approval?.id, approval?.status, approval?.verified, approval?.outcome, approval?.answer, view.plan_error, view.key_mismatch, view.location_mismatch, view.has_work, approval?.identity, planChanges]);
  if (planBanner?.key === key && box.firstElementChild) {
    box.querySelector('.plan-summary').textContent = planCounts(view.plan_counts,language,true);
    return true;
  }
  clear(box);
  const unverified = approval?.status === 'answered' && !approval.verified;
  const heading = el('h2', view.location_mismatch ? t('projectMoved') : view.key_mismatch ? t('planKeyHeading') : view.plan_error ? t('planTampered') : !approval?.id ? t('planMissing') : unverified ? t('planUnverified') : approval.status === 'open' ? (view.has_work?t('planContinueQuestion'):approval.question) : t('planSentBack'));
  heading.id = 'plan-question'; box.setAttribute('aria-labelledby', heading.id);
  box.append(heading, el('p', planCounts(view.plan_counts,language,true), 'plan-summary'));
  planBanner = {key};
  const problem=view.plan_error || view.key_mismatch || view.location_mismatch || unverified;
  box.classList.toggle('problem',!!problem);
  if(problem){heading.prepend(el('span',t('warning'),'problem-word'));box.append(el('p',t(view.has_work?'workRecorded':'noWorkRecorded'),'plan-notice'));}
  if(view.location_mismatch){box.append(el('p',t('projectMovedHelp')));return true;}
  if (view.key_mismatch) {
    box.append(el('p',t('planKeyMismatch')),el('p',t('keyRecoveryAfter')),button(t('log'),()=>{showMode('home');home();$('home').scrollIntoView({block:'start'});},'link'));
    const recovery=el('details',undefined,'key-recovery');recovery.append(el('summary',t('keyRecover')),el('p',t('keyConfirm')));
    const displayed=structuredClone(view.recovery_identity),message=el('p');
    recovery.append(button(t('keyConfirmAction'),async event=>{
      const target=event.currentTarget;target.disabled=true;
      try{await api('/api/key/repin',{...chosen,displayed,confirm:true});planBanner=null;await refresh(true);}
      catch(error){message.textContent=t(error.code==='stale_decision'?'decisionChanged':'connectionFailed');target.disabled=false;}
    },'primary'),message);box.append(recovery);return true;
  }
  if (!approval?.id && !view.plan_error) { box.append(el('p',t(view.legacy?'oldRunApproval':'planMissingHelp'))); return true; }
  if (view.plan_error || unverified) {
    box.append(el('p', t(view.plan_error ? 'planTamperedHelp' : 'planUnverifiedHelp')));
    if (view.key_mismatch) box.append(el('p', t('planKeyMismatch')));
    return true;
  }
  if (approval.status !== 'open') {
    const note=el('div',undefined,'plan-return-note');
    note.append(el('p',t('planSentNote'),'eyebrow'),el('p',approval.answer || ''));
    box.append(note,el('p',t('planWaitingRevision'),'muted plan-waiting'));
    return true;
  }
  if(mode!=='flow'){box.append(button(t('viewPlan'),showGraph,'primary'));return true;}
  const ownChecks=view.nodes.flatMap(n=>n.planned_checks||[]).filter(c=>c.runs_own_files).length;if(ownChecks)box.append(el('p',t('ownCheckCount',{n:ownChecks}),'own-check-note'));
  if (view.legacy) box.append(el('p',t('oldRunReposted'),'plan-notice'));
  const oldResults=view.legacy?view.nodes.filter(n=>n.preapproval_submission):[];
  if(oldResults.length){
    const list=el('div',undefined,'old-results');list.append(el('p',t('oldResults')));
    for(const n of oldResults){const details=el('details');details.append(el('summary',title(n)));
      for(const row of view.timeline.filter(r=>r.kind==='attempt'&&r.node===n.id))details.append(logRow(row,false,true));
      const required=n.submitted_files||[],read=new Set();
      const mark=()=>{if(required.every(path=>read.has(path)))planRead.add('result:'+n.id);planBanner?.update?.();};
      for(const path of required){const output=el('pre',undefined,'file-reader');output.hidden=true;details.append(button(path,async()=>{try{output.textContent=await api(query('/api/file',{decision:approval.id,path}),null,true);output.hidden=false;read.add(path);decisionController.openFile();mark();}catch{output.textContent=t('fileFailed');output.hidden=false;}}),output);}
      details.addEventListener('toggle',()=>{if(details.open)mark();});list.append(details);}
    box.append(list);
  }
  if(approval.reason==='key_repinned')box.append(el('p',t('keyRepinned'),'plan-notice'));
  if (view.replaced_unverifiable) box.append(el('p',t('planReplaced'),'plan-notice'));
  if(planChanges){
    box.append(el('p',t(planChangeIds?.old?'planChangeIds':'newPlanDecision',planChangeIds||{}),'change-notice'));
    const changes=el('div',undefined,'plan-change-list');
    for(const change of planChanges){const item=el('details');item.append(el('summary',t(change.kind)+' · '+change.title));renderPlanDiff(item,change.id);item.addEventListener('toggle',()=>{if(item.open)readPlanChange(change.id);});changes.append(item);}
    box.append(changes);
  }
  const session = decisionController.open(approval.id);
  const actions = el('div', undefined, 'plan-actions'), start = button(t(view.has_work?'planContinue':'planStart'), () => send('approved'), 'primary');
  const startGroup = el('div'), graphReason=el('p',undefined,'action-hint'); startGroup.append(start,graphReason, el('p', t(view.has_work?'planContinueEffect':'planStartEffect'), 'muted'));
  const backGroup = el('div'), changes = el('details',undefined,'plan-change-form'), label = el('label', t('backReason')), input = el('textarea');
  input.id = 'plan-changes'; label.htmlFor = input.id; input.rows = 2; input.value = session?.draft || '';
  const back = button(t('sendBack'), () => send('revision_requested'));
  const message = el('p', undefined, 'muted'); message.setAttribute('role', 'status');
  const update = () => { const changed=box.querySelector('.change-notice');if(changed)changed.textContent=t(planChangeIds?.old?(unreadPlanChanges()?'planChangeIds':'planChangesRead'):(unreadPlanChanges()?'newPlanDecision':'newPlanRead'),planChangeIds||{}); graphReason.textContent=graphReadReason();graphReason.hidden=!graphReason.textContent;start.disabled = !!graphReason.textContent || unreadPlanChanges() || !oldResults.every(n=>planRead.has('result:'+n.id)) || !decisionController.canSubmit('approved'); back.disabled = unreadPlanChanges() || !decisionController.canSubmit('revision_requested'); input.disabled = !!session?.busy; $('picker').disabled = !!session?.busy; };
  planBanner.update=update;
  input.addEventListener('input', () => { decisionController.setDraft(input.value); update(); });
  async function send(outcome) {
    if(unreadPlanChanges() || outcome==='approved'&&!!graphReadReason() || outcome==='approved'&&!oldResults.every(n=>planRead.has('result:'+n.id)))return;
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
  planBox.classList.remove('plan-banner','problem'); planBox.removeAttribute('aria-labelledby');
  const box = $('attention'); clear(box); box.hidden = !view.decisions.length;
  box.setAttribute('aria-label', t('yourTurn'));
  if (box.hidden) return;
  const heading = el('div', undefined, 'attention-heading');
  heading.append(el('span', t('yourTurn')), el('strong', String(view.decisions.length)));
  const items = el('div', undefined, 'attention-items');
  for (const d of view.decisions) {
    const item = el('div', undefined, 'attention-item'), text = el('div'), reference = el('div', undefined, 'ref-line');
    reference.append(refChip(d.id, `${d.id} · ${d.node_title || question(d)}`, true, d.free));
    if (d.node_title) reference.append(el('span', d.node_title));
    if(d.free)text.append(el('p',t('freeQuestion',{who:who(d.asked_by)}),'free-question'),el('p',t('freeEffect')));
    text.append(reference, el('p', question(d) || purposeWording(d.purpose, language)));
    item.append(text, button(t(d.free?'freeRead':'read'), () => openDecision(d.id), d.free?'':'primary')); items.append(item);
  }
  box.append(heading, items);
}
let panelFingerprint='',panelNode=null;
function panel() {
  const p = $('panel');
  const signature=JSON.stringify([selected,flowNode(selected),view.decisions.filter(d=>d.node===selected),view.timeline.filter(r=>r.node===selected)]);
  if(signature===panelFingerprint)return;
  panelFingerprint=signature;
  const scroll=selected===panelNode?p.scrollTop:0;panelNode=selected;p.onscroll=null;clear(p);
  const node = flowNode(selected);
  p.hidden = !node; $('flow').classList.toggle('has-selection', !!node);
  if (!node) return;
  p.setAttribute('aria-label', title(node));
  const close = button('×', () => {
    const id = selected; selectNode(id);
    [...document.querySelectorAll('.node-card')].find(e => e.dataset.node === id)?.querySelector('.node-header')?.focus({preventScroll:!matchMedia('(max-width:760px)').matches});
  }, 'panel-close'); close.setAttribute('aria-label', t('closeDetails'));
  const reference = el('p', undefined, 'ref-line'); reference.append(refChip(node.id, `${node.id} · ${title(node)}`));
  if(workedBy(node))reference.append(el('span',t('workedBy',{who:workedBy(node)})));
  const referenceDetails=el('details');referenceDetails.append(el('summary',t('nodeReference')),reference);
  const panelBar=el('div',undefined,'panel-bar'); panelBar.append(el('strong',t(node.runLevel?'runChecksTitle':'aboutWork')),close); p.append(panelBar);
  for (const d of view.decisions.filter(d => d.node === node.id)) {
    const ask = card(t('yourTurn'), question(d) || purposeWording(d.purpose, language), true);
    ask.append(refChip(d.id, `${d.id} · ${title(node)}`, true, d.free)); p.append(ask);
  }
  p.append(el('p', node.runLevel?t('runChecksAfter'):status(node), 'panel-status '+cardTone(node)), el('h2', title(node)));
  p.append(el('p',stateWords(displayState(node,view.decisions),language).whoseMove,'whose-move'));
  if(node.waiting_for_review_correction)p.append(el('p',t('reviewWaiting')));
  if(node.review_needs_correction)p.append(el('p',t('reviewCorrection')));
  if (node.runLevel || view.plan_approval && !(view.plan_approval.verified && view.plan_approval.outcome === 'approved')) {
    planFacts(p, node); if(!node.runLevel)p.append(referenceDetails); p.scrollTop=scroll; return;
  }
  if (displayState(node,view.decisions)==='returned') p.append(el('p',t('returnedShort',{who:node.returned_by?.session || t(node.returned_by?.role==='reviewer'?'roleReviewer':'roleLeader'),reason:returnedLine(node)})));
  p.append(referenceDetails, el('p', attempts(node)));
  const rows = view.timeline.filter(r => r.node === node.id && r.kind === 'attempt').sort((a,b)=>b.seq-a.seq);
  if (rows.length) p.append(el('p', t('attemptsOf'), 'eyebrow'));
  const list = el('ol', undefined, 'panel-history');
  let earlier=false;
  for (const r of rows) {
    const item = el('li'); item.className=r.attempt===node.attempts?'current-history':'earlier-history'; if(r.attempt===node.attempts || !earlier)item.append(el('strong',view.complete?t('attemptShort',{n:r.attempt}):attemptHeading(r,r.attempt!==node.attempts)));if(r.attempt!==node.attempts)earlier=true;item.append(wording(rowSentence(r),'p'));
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
function attemptHeading(r,earlier){return view.complete?t('attemptResult',{n:r.attempt,result:stateWords(displayState({status:r.state==='returned'?'rejected':r.state}),language).name}):t(earlier?'earlierAttempt':'currentAttempt');}
function rowSentence(r) {
  const n = r.attempt || 1;
  if (r.kind === 'superseded') return t(r.reason==='key_repinned'?(r.purpose==='free'?'keyQuestionReplaced':'keyDecisionReplaced'):r.reason==='evidence_changed'?(r.purpose==='free'?'evidenceQuestionReplaced':'evidenceDecisionReplaced'):'evSuperseded');
  if (r.kind === 'started') return t('evStarted');
  if (r.kind === 'repinned') return t(r.verified?'evRepinned':'unverifiedAnswer');
  if (r.kind === 'planned' && r.replaced_unverifiable) return t('planReplaced');
  if (r.kind === 'planned') return (r.replaced_unverifiable ? t('planReplaced') : r.revision > 1 ? t('evReplanned', {rev:r.revision}) : t('evPlanned')) + ' · ' + (r.counts ? planCounts(r.counts,language) : t('planItems',{n:r.count}));
  if (r.kind === 'final') return r.result === 'passed' ? t('evFinalPassed') : [t('evFinalFailed'), ...(r.failed || [])].join(' · ');
  if (r.kind === 'learned') return `${t('evLearned')} · ${r.text}`;
  if (r.kind === 'reopened') return [t('evReopened'), r.reason].filter(Boolean).join(' · ');
  if (r.kind === 'asked') return [t(r.purpose==='free'?'evAsked':'evDecisionAsked'), r.question].filter(Boolean).join(' · ');
  if (r.kind === 'answered' && !r.verified) return [t('unverifiedAnswer'),r.source?t('answerChannel',{source:t(r.source==='terminal'?'sourceTerminal':'sourceDashboard')}):''].filter(Boolean).join(' · ');
  if (r.kind === 'answered' && r.purpose === 'plan_approval' && r.outcome === 'approved') return [t('answeredPlan'),r.answer].filter(Boolean).join(' · ');
  if (r.kind === 'answered') return [t(({approved:'answeredApproval', revision_requested:'answeredRevision', rejected:'answeredRejection'})[r.outcome] || 'evAnswered'), r.answer].filter(Boolean).join(' · ');
  const failed = (r.checks || []).filter(c => c.result === 'failed').map(c => checkTitle(c, language)), passed = (r.checks || []).filter(c => c.result === 'passed').length;
  const current = view.nodes.find(node => node.id === r.node && node.attempts === r.attempt);
  if(current?.preapproval_submission)return stateWords('preapprovalSubmitted',language).name+' · '+t('preapprovalExplanation');
  const checks=current?.planned_checks||[],total=Math.max((r.checks||[]).length,checks.filter(c=>c.type!=='human').length),human=checks.filter(c=>c.type==='human').length;
  const outcome = total && r.state !== 'running' ? t('checkProgress',{total,passed})+(human?' · '+t('humanCheckCount',{n:human}):'') : '';
  const stateKey=displayState({status:({returned:'rejected',needs_you:'awaiting_approval'}[r.state]||r.state),attempts:n},current&&needs(current)&&!['returned','replan','passed'].includes(r.state)?[{node:undefined}]:[]);
  return [stateWords(stateKey,language).name,outcome,r.returned_by?t('returnedActor',{who:r.returned_by.session||who(r.returned_by)}):''].filter(Boolean).join(' · ');
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
  item.append(wording(checkWording(c, language, attempt),commandTitle(c)?'code':'strong'));
  if(c.timed_out)item.append(el('span', ' · '+result));
  if ((!c.type || c.type === 'cmd') && c.command) { const run = el('p', undefined, 'muted'); run.append(el('span', t('ranCommand')+': '), el('code', c.command), el('span', [c.exit_code === null || c.exit_code === undefined ? '' : ' → ' + t(c.exit_code === 0 ? 'exitSuccess' : 'exitFailure', {n:c.exit_code}), typeof c.duration_ms === 'number' ? t('seconds', {n:(c.duration_ms / 1000).toFixed(2)}) : ''].filter(Boolean).join(' · '))); item.append(run); }
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
  if(view.timeline.filter(row=>row.ts===r.ts).length>1)stamp.append(el('span', ' · '+t('recordOrder',{n:view.timeline.findIndex(row=>row.id===r.id)+1})));
  head.append(stamp);
  if (r.decision) text.append(refChip(r.decision, `${r.decision} · ${r.node_title || r.question}`, true, r.purpose==='free'));
  if (r.node) text.append(el('strong', title({id:r.node, title:r.node_title})));
  text.append(wording(rowSentence(r))); head.append(text);
  const by = [['answered','repinned'].includes(r.kind) && !r.verified ? t('unverifiedAuthor') : who(r.by), r.kind === 'attempt' && r.worker?.model&&![STRINGS.ko.roleWorker,STRINGS.ko.roleLeader,STRINGS.en.roleWorker,STRINGS.en.roleLeader].includes(r.worker.model) ? t('modelName',{model:r.worker.model}) : ''].filter(Boolean).join(' · ');
  if (by) head.append(el('span', by, 'row-who'));

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
  const pending=view.decisions.filter(d=>d.purpose!=='plan_approval');
  const blocked=planBlocked(),inbox = el('section'); inbox.append(el('h2', t(pending.length||blocked ? 'needsYou' : 'nothingTitle')));

  pending.forEach(d => inbox.append(decisionCard(d)));
  if (!pending.length&&!blocked) inbox.append(el('p', t('nothing'), 'muted'));
  if(pending.length || !blocked && !view.complete)box.append(inbox);
  if (!view.complete) {
    const now = el('section'), list = el('ul', undefined, 'now'); now.append(el('h2', t('doingNow')));
    const active = view.nodes.filter(n => !needs(n) && !['passed','pending','ready','blocked'].includes(n.status) && n.attempts);
    for (const n of active) {
      const item = el('li'); if (n.status === 'running') item.append(walker());
      item.append(el('strong', title(n)), el('span', `${status(n)} · ${attempts(n)}`));
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
    const line = el('tr'), name = el('td'); name.append(button(title(n), () => showNode(n.id), 'link'));
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
function wholePhoneCards() {
  if(!matchMedia('(max-width:760px)').matches || $('flow').hidden)return;
  for(const card of $('phone-flow').querySelectorAll('.node-card')) {
    const rect=card.getBoundingClientRect();
    card.style.visibility='visible';
  }
}
addEventListener('scroll',wholePhoneCards,{passive:true});
addEventListener('resize',wholePhoneCards);
function accessible() {
  $('accessible').hidden=!!view.plan_error;
  clear($('node-list')); clear($('edge-list')); clear($('decision-list'));
  const flow=planFlow(view,language);
  const work=flow.nodes.filter(n=>!n.runLevel);
  const templates=work.map(n=>JSON.stringify((n.planned_checks||[]).map(c=>[c.type,c.title,(c.command||'').split(n.owns?.[0]||'\u0000').join('{file}')] )));
  const repeated=work.length>20&&new Set(templates).size===1;
  if(repeated){const note=el('li',t('repeatedSteps',{n:work.length}),'repeated-note');note.style.counterIncrement='list-item 0';$('node-list').append(note);}
  const order = layeredLayout(flow.nodes,flow.edges,flow.decisions).order;
  [...flow.nodes].sort((a,b)=>order.indexOf(a.id)-order.indexOf(b.id)).forEach(n => { const item = el('li', undefined, 'card'); item.append(button(title(n), () => selectNode(n.id)), el('p', n.runLevel?t('runChecksAfter'):status(n))); if(!n.runLevel)item.append(el('p', attempts(n), 'muted')); if(planBlocked()){if(flow.nodes.length>20){const more=el('details');more.open=$('node-list').children.length===(repeated?1:0);more.append(el('summary',t('moreDetails')));planFacts(more,n);item.append(more);}else planFacts(item,n);} else item.append(el('p', n.runLevel?view.goal:n.summary)); if (n.returned_reasons.length) textList(item, n.returned_reasons.flatMap((reasons,i)=>reasons.map(reason=>t('earlierFailure',{n:i+1,reason}))), 'noReason'); $('node-list').append(item); });
  forwardEdges(flow.edges).forEach(e => { const a = flow.nodes.find(n => n.id === e.from), b = flow.nodes.find(n => n.id === e.to); $('edge-list').append(el('li', `${title(a)} → ${title(b)} · ${relationText(e)} · ${t(e.delivered ? 'delivered' : 'notDelivered')}`)); });
  view.decisions.forEach(d => { const item = el('li'); decisionHeading(item, d, 'h3'); failedBlock(item, d); if (d.context.why) item.append(el('p', d.context.why)); $('decision-list').append(item); });
  if (!view.decisions.length) $('decision-list').append(el('li', t('nothingTitle')));
  const listHeading=$('accessible').querySelector('h2');if(listHeading)listHeading.textContent=planCounts(view.plan_counts,language);
  const phone=$('phone-flow');clear(phone);
  for(const id of order){
    const n=flow.nodes.find(n=>n.id===id),item=el('li');item.append(nodeCard(n,n.id===selected));
    const edges=forwardEdges(flow.edges).filter(e=>e.from===id);
    for(const e of edges){const handoff=el('p',undefined,'phone-handoff');handoff.append(el('span',`${title(n)} → ${title(flow.nodes.find(n=>n.id===e.to))}`));item.append(handoff);}
    phone.append(item);
  }
  wholePhoneCards();setTimeout(recordGraphRead,0);
}
function showMode(next) {
  if (next !== 'decision' && (mode === 'decision' || next === 'home') && !discardDecision()) return false;
  mode = next; if(view&&planBlocked())planAttention($('attention')); $('attention').hidden = !planBlocked() && (next!=='flow' || !view?.decisions.length); $('home').hidden = next !== 'home'; $('flow').hidden = next !== 'flow'; $('decision').hidden = next !== 'decision'; $('accessible').hidden = next !== 'flow' || !!view?.plan_error;
  $('home-tab').setAttribute('aria-pressed', String(next === 'home')); $('flow-tab').setAttribute('aria-pressed', String(next === 'flow'));
  // The map can only measure its cards while it is on screen.
  if (renderer && next === 'flow' && view) renderer.update(view, selected); wholePhoneCards(); return true;
}
function discardDecision() {
  if (!decisionController.close()) return false;
  decisionUI = null; planBanner = null; clear($('decision')); return true;
}
function closeInvalidDecision(run, decisions, nextView = {decisions}) {
  const old=decisionController.session?.target.id;
  if(planChanges && old===planChangeIds?.old){decisionController.close();decisionController.refresh(nextView,run);decisionNotice='';notice('');return false;}
  let reason = decisionController.refresh(nextView, run);
  const stale=nextView.stale_decisions?.find(d=>d.id===old);
  if(stale && reason){if(stale.reason==='evidence_changed' && mode==='decision'){showChangedDecision();return true;}reason='legacyDecision';}
  if (!reason) return false;
  if (mode === 'decision') leaveDecision(); decisionNotice = reason; notice(decisionNotice); return true;
}
function showChangedDecision(){const free=!!decisionController.session?.decision.free;decisionController.close();decisionUI=null;const box=$('decision');clear(box);box.classList.add('decision-changed');box.append(el('h2',t(free?'freeEvidenceChanged':'evidenceChanged')),el('p',t('waitForNewQuestion'),'change-notice'));$('picker').disabled=false;}
function goHome() { if (showMode('home') && view) home(); }
function showGraph() { if (!showMode('flow')) return; attention(); panel(); }
function selectNode(id) { const n=flowNode(id),d=view.decisions.find(d=>d.node===id); if(n?.kind==='decision'&&d){openDecision(d.id);return;} if (!showMode('flow')) return; selected = selected === id ? null : id; panel(); if(selected)readPlanChange(selected); if (renderer) renderer.select(selected);planBanner?.update?.(); if (selected && matchMedia('(max-width:760px)').matches) $('panel').scrollIntoView({block:'start',behavior:reduced.matches?'auto':'smooth'}); }
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
  showMode('decision'); const box = $('decision'); clear(box);box.classList.remove('decision-changed');
  const reading = card(t('yourTurn'), null, true); reading.firstElementChild.remove(); reading.classList.add('reading');
  const backButton=button(t('backToTab',{tab:t(cameFrom==='home'?'home':'graph')}),leaveDecision,'link'); reading.append(backButton);
  const introduction = el('div'); reading.append(introduction);
  const report = el('div', undefined, 'worker-report'), note = el('div', undefined, 'speech');
  report.append(el('p',t('workerNote'),'eyebrow'),note); reading.append(report);
  const isQuestion = ['direction','information'].includes(d.kind), permission = d.record_purpose==='node'&&d.kind==='authorization';
  const answerLabel = el('label', t(isQuestion ? 'answerLabel' : permission ? 'optionalNote' : 'backReason')); answerLabel.htmlFor = 'answer-text';
  const phoneHistory=el('details',undefined,'phone-history');reading.append(phoneHistory);
  const input = el('textarea'); input.id = 'answer-text'; input.required = true; input.value = session.draft;
  input.addEventListener('input', () => { if (current()) { decisionController.setDraft(input.value); updateActions(); } }); reading.append(answerLabel, input);
  const message = el('p'); message.id = 'answer-message'; message.setAttribute('role','status'); reading.append(message);
  const blindBox=el('label',undefined,'blind-confirm');
  const blindCheck=el('input');blindCheck.type='checkbox';blindCheck.id='blind-confirm';
  blindBox.append(blindCheck,el('span',t(permission?'permissionConfirmBlind':'confirmBlind')));reading.append(blindBox);
  blindCheck.addEventListener('change',()=>{decisionController.confirmBlind(blindCheck.checked);updateActions();});
  const actions = el('div'); actions.id = 'answer-actions';
  const updateActions = () => {
    actions.querySelectorAll('button[data-outcome]').forEach(b => { b.disabled = !current() || !decisionController.canSubmit(b.dataset.outcome, input.value); });
    for(const b of actions.querySelectorAll('button[data-outcome]')) {
      const kind=b.dataset.outcome,hint=actions.querySelector(`[data-hint=${kind}]`);
      hint.textContent=!b.disabled?'':session.busy?t('sending'):kind==='approved'?(session.nothingToJudge&&!session.blindConfirmed?t(permission?'permissionBlindHint':'blindHint'):t('readGateHint')):t(isQuestion?'writeFirst':'revisionHint');
      hint.hidden=!hint.textContent;
    }
    const read=canApprove(session),empty=session.nothingToJudge;
    if(approveButton)approveButton.classList.toggle('primary',!empty&&read);
    if(revisionButton)revisionButton.classList.toggle('primary',!permission&&empty);
    const fileButtons=[...fileChoices.querySelectorAll('button')];
    const fileCanUnlock=!session.failed.length&&session.purpose!=='hold';
    fileButtons.forEach(b=>{b.classList.remove('primary');b.classList.toggle('file-opened',b.dataset.opened==='true');});
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
  if (isQuestion) actionButton('answered', t('answer'));
  else { revisionButton=actionButton(permission?'rejected':'revision_requested', t(permission?'refuse':'sendBack')); approveButton = actionButton('approved', '', 'primary'); }
  reading.append(actions);
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
      const entry = el('div'); entry.append(button(t('fileUnread',{file:file.name}), async event => {
        if (!current()) return;
        const fileButton=event.currentTarget; const request = ++fileRequest; fileStatus.textContent = t('loading'); reader.hidden = true;
        try {
          const text = await api(query('/api/file', {decision:session.target.id,path:file.path}, session.target), null, true);
          if (!current() || request !== fileRequest) return;
          reader.classList.toggle('code-file', /\.(?:py|js|ts|jsx|tsx|json|css|html|sh|swift|rs|go|c|h|cpp|yaml|yml|toml|xml)$/i.test(file.path));
          reader.textContent = text; reader.hidden = false; fileStatus.textContent = ''; reader.setAttribute('aria-label',file.name);
          fileButton.dataset.opened='true';fileButton.textContent=t('fileRead',{file:file.name});decisionController.openFile(); updateActions();
        } catch(error) { if (current() && request === fileRequest) {if(error.code==='evidence_changed'){showChangedDecision();}else{fileStatus.textContent=t('fileFailed');session.fileOpened=false;updateActions();}} }
      })); if(file.path!==file.name){const path=el('details');path.append(el('summary',t('filePath')),el('small',file.path,'file-path'));entry.append(path);} fileChoices.append(entry);
    }
  };
  const details = el('details', undefined, 'evidence'); details.append(el('summary', t('details'))); const raw = el('pre');
  details.open = session.detailsOpened;
  const markDetailsOpened = () => { if (current() && details.open) { decisionController.openDetails(); updateActions(); } };
  details.addEventListener('toggle', markDetailsOpened);
  const reminder = el('p', t('evidenceReminder')); reminder.hidden=true;
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
    clear(introduction);
    if(session.changed){introduction.append(el('p',t(decision.free?'freeChanged':'decisionChanged'),'change-notice'),button(t('acknowledgeChange'),()=>{decisionController.acknowledge();update();}));}
    introduction.append(el('p',t(decision.free?'freeTab':'decisionTab',{tab:t(cameFrom==='home'?'home':'graph')}),'eyebrow'));
    decisionHeading(introduction, decision, 'h2'); const heading = introduction.querySelector('h2'); heading.id = 'decision-title';
    const node = view.nodes.find(n => n.id === decision.node);
    introduction.append(card(t('why'), decision.free?t('freeEffect'):decision.context.why || purposeWording(decision.purpose, language)));authorNote(introduction,decision.author_context);
    updateFiles(decision);
    if(decision.commit){const commit=el('details');commit.append(el('summary',t('commitDetails')),el('p',t('approvedCommit')+' · '+decision.commit,'muted'));introduction.append(commit);}
    if(decision.files?.length&&Object.keys(decision.artifact_hashes||{}).length){const hashes=el('details');hashes.append(el('summary',t('evidenceHashes')),el('pre',Object.entries(decision.artifact_hashes).map(([path,hash])=>path+' · '+(hash||'—')).join('\n')));introduction.append(hashes);}
    clear(history);
    const rows = node && !decision.free ? view.timeline.filter(r => r.node === node.id && r.kind === 'attempt') : [];
    const missing=el('div',undefined,'missing-records');
    const nothingToInspect=session.nothingToJudge;
    reading.classList.toggle('no-evidence',nothingToInspect);
    blindBox.hidden=!nothingToInspect;blindCheck.checked=!!session.blindConfirmed;
    if(nothingToInspect) {
      missing.append(el('h3',t('nothingToJudge')),el('p',t(permission?'permissionNoEvidence':'nothingToJudgeBody')));
    } else if(!decision.free) {
      if (!decision.files?.length) missing.append(el('p',t('noFiles')));
      if (!rows.some(r=>r.attempt===node?.attempts && r.checks?.length)) missing.append(el('p',t('noCurrentChecks')));
    }
    if(approveButton){
      approveButton.classList.toggle('primary',!nothingToInspect);
      revisionButton.classList.toggle('primary',!permission&&nothingToInspect);
      // Action order is stable; emphasis changes, position does not.
    }
    if(missing.children.length) introduction.append(missing);
    history.hidden = !rows.length;phoneHistory.hidden=!rows.length;clear(phoneHistory);
    const previous=rows.filter(r=>r.attempt<node?.attempts && r.checks?.some(c=>c.result==='failed')).sort((a,b)=>b.seq-a.seq)[0];
    phoneHistory.append(el('summary',t('history')));
    const phoneRows=el('ol',undefined,'log');[...rows].sort((a,b)=>b.seq-a.seq).forEach(r=>{const row=logRow({...r,notes:r.attempt===node.attempts?null:r.notes,files:r.attempt===node.attempts?(r.files||[]).filter(f=>!decision.files?.some(file=>file.path===f)):r.files},false,true);row.prepend(el('p',attemptHeading(r,r.attempt!==node.attempts),'eyebrow'));phoneRows.append(row);});phoneHistory.append(phoneRows);
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
    clear(gateFacts); gateFacts.append(el('p', t(decision.free?'freeEffect':'gateReview')), el('p', question(decision) || purposeWording(decision.purpose, language)));
    failedBlock(gateFacts, decision);
    if(node&&!decision.free){plannedChecks(gateFacts,node.planned_checks);contractDetails(gateFacts,node.contract);}
    for(const [key,name] of [['if_approved','ifApproved'],['if_rejected','ifRejected'],['undo','undo']])if((key!=='if_rejected'||!isQuestion)&&decision.context[key])gateFacts.append(el('p',t(name)+': '+decision.context[key]));
    if (decision.context.why) gateFacts.append(el('p', decision.context.why));
    details.hidden = !decisionHasEvidence(view,decision);details.classList.toggle('evidence',!decision.free);
    loadEvidence.hidden = !decision.has_evidence;
    note.textContent = decision.worker_note || ''; report.hidden = !decision.worker_note;
    const effects = [['if_approved','ifApproved'],['if_rejected','ifRejected'],['undo','undo']].filter(([key]) => (key!=='if_rejected'||!isQuestion)&&decision.context[key]);
    clear(surrounding);
    failedBlock(surrounding, decision);
    for (const key of ['verified','unverified']) { if (!decision[key]?.length) continue; const c = card(t(key)); textList(c, decision[key]); surrounding.append(c); }
    files.hidden = !decision.files?.length;
    if(matchMedia('(max-width:760px)').matches)reading.insertBefore(files,phoneHistory);else right.insertBefore(files,history);
    if (!decisionHasEvidence(view,decision)) surrounding.append(el('p', t(decision.free?'questionOnly':'decisionOnly'), 'muted'));
    reminder.hidden = isQuestion || !decisionHasEvidence(view,decision) || (decision.files?.length&&!session.failed.length&&session.purpose!=='hold');
    if (approveButton) approveButton.textContent = nothingToInspect ? t(permission?'permissionAcceptBlind':'acceptBlind') : purposeAction(decision.purpose, language, decision.failed);
    for(const effect of actions.querySelectorAll('[data-effect]')) {
      const kind=effect.dataset.effect;
      effect.textContent=t(kind==='approved'?'approveEffect':kind==='answered'?'answerEffect':'revisionEffect');
      if(decision.free)effect.textContent=t('freeEffect');
      else if(node&&decision.purpose==='hold')effect.textContent=t(kind==='approved'?'holdAccept':'holdReject',{tasks:dependentTitles(node.id)});
      else if(node?.kind==='decision'&&!isQuestion)effect.textContent=t(kind==='approved'?'decisionAccept':'holdReject',{tasks:dependentTitles(node.id)});
      if(!decision.free&&decision.purpose!=='hold'&&kind==='revision_requested'&&node?.attempts&&node.attempts<node.max_attempts)effect.textContent=t('retryEffect',{n:node.attempts+1,max:node.max_attempts});
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
    const stale=view.stale_decisions?.find(d=>d.id===id);
    if(stale){decisionNotice=t(stale.reason==='legacy_decision'?'legacyDecision':stale.purpose==='free'?'freeEvidenceChanged':'evidenceChanged');showMode('home');home();notice(decisionNotice);return true;}
    const old=view.superseded?.find(d=>d.id===id);
    if(old?.replacement) { replacementDecision=old.replacement; decisionNotice=t('supersededNotice',{old:id,new:old.replacement}); showMode('home'); home(); notice(decisionNotice); return true; }
    if (view.decisions.some(d => d.id === id)) { openDecision(id); return true; }
    const row = [...view.timeline].reverse().find(r => r.decision === id); if (!row) return miss(target.decision);
    decisionNotice = ''; notice(''); if (!showMode('home')) return false;
    logNode = null; logFilter = 'all'; found = mark = row.id; home(); return true;
  }
  if (target.node) {
    const text = target.node.toLowerCase();
    const nodes=planFlow(view,language).nodes;
    const node = nodes.find(n => n.id.toLowerCase() === text) || nodes.find(n => (n.title || '').toLowerCase().includes(text));
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
  if(next.plan_approval?.status==='open'){
    const identity=JSON.stringify(next.plan_approval.identity);
    if(planSeen && planSeen.identity!==identity){
      const before=new Map(planSeen.nodes.map(n=>[n.id,n])),after=new Map(next.nodes.map(n=>[n.id,n]));
      planChanges=[];planRead.clear();planChangeIds={old:planSeen.id,new:next.plan_approval.id};
      for(const n of next.nodes)if(!before.has(n.id)||JSON.stringify(n.contract)!==JSON.stringify(before.get(n.id).contract))planChanges.push({id:n.id,title:n.title,kind:before.has(n.id)?'changed':'added',fields:contractDiff(before.get(n.id)?.contract||{},n.contract)});
      for(const n of planSeen.nodes)if(!after.has(n.id))planChanges.push({id:n.id,title:n.title,kind:'removed',fields:contractDiff(n.contract,{})});
      const runDiff=contractDiff(planSeen.contract,next.run_contract);
      if(runDiff.length)planChanges.push({id:'_run_checks',title:next.title,kind:'changed',fields:runDiff});if(!planChanges.length)planChanges=null;
    }
    if(next.replaced_unverifiable && (!planSeen || planSeen.identity!==identity)){planRead.clear();planChanges=[...next.nodes.map(n=>({id:n.id,title:n.title,kind:'changed',fields:[]})),{id:'_run_checks',title:next.title,kind:'changed',fields:[]}];planChangeIds={old:null,new:next.plan_approval.id};}
    planSeen={identity,id:next.plan_approval.id,nodes:next.nodes,contract:next.run_contract};
  }
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
  const sentBack=view.plan_approval?.status==='answered'&&['rejected','revision_requested'].includes(view.plan_approval.outcome);
  view.nodes.forEach(n=>n.plan_revision_wait=sentBack);
  const actionCounts=[t('countDecision',{n:view.decisions.filter(d=>!d.free).length}),t('countQuestions',{n:view.decisions.filter(d=>d.free).length})].join(' · ');
  const states=Object.entries(stateCounts(planFlow(view,language).nodes,view.decisions)).map(([key,n])=>stateWords(key,language).name+' '+n).join(' · ');
  $('subtitle').textContent=view.plan_error?'':view.complete?t('complete'):actionCounts+' · '+states;
  if(view.complete){const resultNode=[...view.nodes].reverse().find(n=>n.kind==='work'&&view.timeline.some(r=>r.node===n.id&&r.files?.length));if(resultNode){const files=[...new Set(view.timeline.filter(r=>r.node===resultNode.id).flatMap(r=>r.files||[]))];$('subtitle').append(button(t('results'),()=>selectNode(resultNode.id),'primary result-action'),el('span',t('runResultSummary',{files:files.join(', ')}),'result-summary'));}}
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
  runs.forEach((r, i) => { const option = el('option', r.title || t('runNumber',{n:r.number})); option.value = String(i); option.dataset.run=r.id; option.selected = !!chosen && r.project === chosen.project && r.id === chosen.run; picker.append(option); });
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
function resetView() { planSeen=null;planChanges=null;planRead.clear(); $('panel').onscroll=null; $('panel').hidden=true; $('flow').classList.remove('has-selection'); panelFingerprint=''; panelNode=null; language = viewLanguage(null, navigator.language); translate(); closeInvalidDecision(chosen, []); view = null; selected = null; fingerprint = ''; ['node-list','edge-list','decision-list','panel','home','attention'].forEach(id => clear($(id))); if (renderer) renderer.update({nodes:[],edges:[],decisions:[],complete:false}, null); $('flow').hidden = true; $('home').hidden = true; $('accessible').hidden = true; $('decision').hidden = true; $('subtitle').textContent = ''; $('where').textContent = ''; }
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
function nodeDescription(n) {return n.runLevel?`${t('runChecksTitle')}. ${t('runChecksAfter')}`:`${t(n.kind||'work')}. ${title(n)}. ${status(n)}. ${attempts(n)}. ${t('returnTimes',{n:cometCount(n)})}`;}
function nodeCard(n, expanded = false, level = 'detail') {
  const root=el('article',undefined,'node-card '+cardTone(n)+(['running','retrying'].includes(displayState(n,view.decisions))?' working':'')+(expanded?' expanded':''));root.dataset.node=n.id;
  const change=planChanges?.find(c=>c.id===n.id);if(change)root.append(el('p',t(change.kind),'change-mark'));
  const header=button('',()=>{
    const decision=view.decisions.find(d=>d.node===n.id);
    if(n.kind==='decision'){if(decision)openDecision(decision.id);else selectNode(n.id);}
    else selectNode(n.id);
  },'node-header');
  header.setAttribute('aria-label',nodeDescription(n));header.setAttribute('aria-expanded',String(expanded));
  if (level === 'overview') {
    root.classList.add('overview-card');
    const state = displayState(n, view.decisions), marks = [];
    if (n.kind === 'review') marks.push('⌕ '+t('review'));
    if (cometCount(n) || state === 'returned') marks.push('↩');
    if (view.decisions.some(d=>d.node===n.id)) marks.push('◆ '+t('yourTurn'));
    if ((view.planned_questions || []).some(q=>q.node===n.id)) marks.push(t('questionsMark'));
    header.title = title(n)+' · '+status(n)+(marks.length?' · '+marks.join(' · '):'')+(cometCount(n)&&n.returned_by?' · '+t('returnedActor',{who:n.returned_by.session||who(n.returned_by)}):'');
    header.append(el('span',statusGlyph(state),'status-glyph'),el('strong',title(n),'node-title'));
    header.append(el('span',status(n)+(cometCount(n)?' · '+t('returnTrace',{n:cometCount(n)}):''),'overview-marks'));
    if(n.planned_checks?.some(c=>c.runs_own_files)){const mark=el('span',t('ownCheckMark'),'own-check-mark');mark.title=t('ownCheckEffect');header.append(mark);}
    root.append(header); return root;
  }
  const state = displayState(n, view.decisions), statusLine = el('span', status(n), 'node-status');
  statusLine.prepend(el('span', statusGlyph(state), 'status-glyph'));
  header.append(statusLine);
  const titleLine=el('span',undefined,'node-title-line');
  if(n.kind && n.kind!=='work')titleLine.append(typeIcon(n.kind));
  titleLine.append(el('strong',title(n),'node-title'));header.append(titleLine);
  const reference=el('div',undefined,'ref-line node-reference');
  if(n.planned_checks?.some(c=>c.runs_own_files)){const mark=el('span',t('ownCheckMark'),'own-check-mark');mark.title=t('ownCheckEffect');reference.append(mark);}
  if(n.status==='passed'&&cometCount(n))reference.append(el('span',t('returnTrace',{n:cometCount(n)})));

  if(n.attempts)reference.append(el('span',t('attemptShort',{n:n.attempts}),'attempt-caption'));
  const decision=view.decisions.find(d=>d.node===n.id);
  const footer=el('div',undefined,'node-footer');
  if(!decision && displayState(n,view.decisions)==='returned') {
    const reason=returnedLine(n);
    const line=el('span',reason);line.title=line.textContent;footer.append(line);
    clear(reference);reference.append(el('span',t('returnedActor',{who:n.returned_by?.session || t(n.returned_by?.role==='reviewer'?'returnReviewer':'returnLeader')})));
  }
  const essentials=el('div',undefined,'node-essentials');
  if(change?.fields?.length){const diff=el('p',diffText(change.fields[0]),'change-preview');diff.title=change.fields.map(diffText).join('\n');essentials.append(diff);}
  const files=[...new Set(n.deliverables || [])];
  if(n.preapproval_submission)essentials.append(el('p',t('preapprovalExplanation'),'preapproval-note'));


  if(state==='notStarted'&&n.inputs?.length&&n.inputs.every(i=>i.delivered))essentials.append(el('p',t('inputsReady')));
  if(n.runLevel) essentials.append(el('p',view.goal,'run-goal-preview'));
  if(files.length&&!n.preapproval_submission)essentials.append(el('p',t('planCardDelivery',{files:files.map(outputLabel).join(', ')})));
  if(n.planned_checks?.length && state!=='returned'&&!n.preapproval_submission) {
    const automated=n.planned_checks.filter(c=>c.type!=='human'),human=n.planned_checks.length-automated.length,check=automated[0]||n.planned_checks[0],preview=el('p');
    if(commandTitle(check))preview.append(el('span',t('planCardChecks',{n:automated.length,first:''})),el('code',checkTitle(check,language)));
    else preview.textContent=t('planCardChecks',{n:automated.length,first:state==='notStarted'?t('plannedCheck',{title:checkTitle(check,language)}):checkTitle(check,language)});
    if(human)preview.append(el('span',' · '+t('humanCheckCount',{n:human})));essentials.append(preview);
  }
  const questions=(view.planned_questions || []).filter(q=>q.node===n.id);
  if(questions.length)essentials.append(el('p',t('planCardQuestion',{n:questions.length,question:questions.map(q=>plannedQuestion(q)).join(' · ')}),'planned-question'));
  root.append(header,essentials,footer,reference);
  return root;
}
function createMap() {
  const map=$('map');map.tabIndex=0;
  const toolbar=el('div',undefined,'map-toolbar'),viewport=el('div',undefined,'map-viewport'),spacer=el('div',undefined,'map-spacer'),stage=el('div',undefined,'map-stage');
  viewport.tabIndex=0;viewport.setAttribute('aria-label',t('mapHelp'));spacer.append(stage);viewport.append(spacer);map.append(toolbar);
  const key=el('div',undefined,'line-key'), overflow=el('div',undefined,'map-overflow'); overflow.setAttribute('aria-label',t('graphEdges'));overflow.dataset.i18nLabel='graphEdges';
  const legend=el('details',undefined,'map-key');legend.append(el('summary',t('legend')),key);toolbar.append(legend);map.append(viewport);
  legend.addEventListener('toggle',()=>{toolbar.style.marginBottom=legend.open?key.offsetHeight+'px':'0px';size();if(automatic)fit();else{panIntent=true;snapTitles();}});
  const visibleCount=el('span',undefined,'map-visible'),overflowButtons=new Map();overflow.append(visibleCount);
  let data={nodes:[],edges:[],decisions:[]},chosenNode=null,layout=null,scale=1,automatic=true,level='detail',layouts=null,rawData=null;
  const nodes=new Map(),chips=new Map(),seen=new Map();let drawing=null,placed=false,initialFitPending=false,layoutKey='',origin={x:0,y:0};
  const zoomText=el('output');zoomText.setAttribute('aria-live','polite');
  const rememberScroll=()=>{scrollPosition={left:viewport.scrollLeft,top:viewport.scrollTop};};
  let scrollPosition={left:0,top:0};
  const zoom=(amount,point=null)=>{
    if(!layout)return;
    automatic=false;
    const rect=viewport.getBoundingClientRect(),screenPoint=point?{x:rect.x+point.x,y:rect.y+point.y}:null;
    point ||= {x:viewport.clientWidth/2,y:viewport.clientHeight/2};
    const before=layout, anchor={x:(viewport.scrollLeft+point.x-origin.x)/scale,y:(viewport.scrollTop+point.y-origin.y)/scale};
    const next=zoomLevel(level,scale,amount), changed=level!==next.level;
    level=next.level;scale=next.scale;
    if(changed)update(rawData,chosenNode);else size();
    const mapped=changed?mapAnchor(before,layout,anchor):anchor;
    const after=viewport.getBoundingClientRect();
    point=screenPoint?{x:screenPoint.x-after.x,y:screenPoint.y-after.y}:{x:viewport.clientWidth/2,y:viewport.clientHeight/2};
    viewport.scrollLeft=mapped.x*scale+origin.x-point.x;viewport.scrollTop=mapped.y*scale+origin.y-point.y;
    rememberScroll();outside();panIntent=true;clearTimeout(snapTimer);snapTimer=setTimeout(snapTitles,160);
  };
  const start=()=>{
    const plan=!!data.plan_approval && !(data.plan_approval.verified && data.plan_approval.outcome==='approved');
    const position=fitStart(layout,viewport.clientWidth,viewport.clientHeight,scale,data.nodes,plan);
    viewport.scrollLeft=position.left;viewport.scrollTop=position.top;rememberScroll();panIntent=true;snapTitles();outside();
  };
  const fit=()=>{
    const next=fitGraph(layouts,viewport.clientWidth-24,viewport.clientHeight-24);
    level=next.level;scale=next.scale;automatic=true;
    placed=false;update(rawData,chosenNode);size();start();
  };
  const zoomOut=button('−',()=>zoom(-.1)),zoomIn=button('+',()=>zoom(.1)),fitButton=button(t('fit'),fit);
  const overviewNote=el('span',undefined,'overview-note'),overviewLabel=button(t('overviewLevel'),()=>{automatic=true;level='overview';scale=fitScale(layouts.overview.bounds,viewport.clientWidth-24,viewport.clientHeight-24);update(rawData,chosenNode);start();}),detailButton=button(t('detailLevel'),()=>{automatic=false;level='detail';scale=1;update(rawData,chosenNode);start();});
  overviewLabel.dataset.i18n='overviewLevel';detailButton.dataset.i18n='detailLevel';
  overviewNote.append(overviewLabel,detailButton);overflow.append(button(t('listAll'),()=>{$('accessible').open=true;$('accessible').scrollIntoView({block:'start'});},'small'));
  toolbar.append(zoomOut,zoomIn,fitButton,zoomText,overviewNote,overflow);
  zoomOut.dataset.i18nLabel='zoomOut';zoomIn.dataset.i18nLabel='zoomIn';viewport.dataset.i18nLabel='mapHelp';
  const mapTitle=el('div',undefined,'map-title'), name=el('strong',t('graph')), direction=el('span',t('mapDirection'));
  name.dataset.i18n='graph';direction.dataset.i18n='mapDirection';mapTitle.append(name,direction);toolbar.prepend(mapTitle);translate();
  function outside() {
    if(!layout || !viewport.clientWidth)return;
    const w=viewport.clientWidth,h=viewport.clientHeight,ox=origin.x,oy=origin.y;
    const groups={offLeft:[],offRight:[],offTop:[],offBottom:[]}; let visible=0;
    for(const n of data.nodes) {
      const p=layout.positions[n.id],x=p.x*scale+ox-viewport.scrollLeft,y=p.y*scale+oy-viewport.scrollTop;
      const element=nodes.get(n.id),title=element?.querySelector('.node-title'),vr=viewport.getBoundingClientRect(),tr=title?.getBoundingClientRect();
      const rect={x,y,width:p.width*scale,height:p.height*scale};
      const direction=offscreenDirection(rect,w,h);
      if(direction)groups[direction].push(n);
      if(!direction)visible++;
      if(element)element.style.visibility=intersectsViewport({x,y,width:p.width*scale,height:p.height*scale},w,h)?'visible':'hidden';
    }
    for(const c of layout.chips){const chip=chips.get(c.first);if(chip)chip.hidden=scale<1 || !!chip.dataset.tooWide || !!offscreenDirection({x:c.x*scale+ox-viewport.scrollLeft,y:c.y*scale+oy-viewport.scrollTop,width:c.width*scale,height:c.height*scale},w,h);}
    // The viewport clips routes naturally: an off-screen neighbour leaves a visible continuing stub.
    recordGraphRead();
    visibleCount.textContent=planCounts(data.plan_counts,language)+' · '+t('visibleTitles',{n:visible});
    for(const [direction,b] of overflowButtons)b.hidden=!groups[direction].length;
    for(const [direction,items] of Object.entries(groups))if(items.length) {
      let b=overflowButtons.get(direction);
      if(!b){b=button('',()=>{},'small');overflowButtons.set(direction,b);overflow.append(b);}
      overflow.append(b);
      b.textContent=(items.some(n=>!n.runLevel)?t('offCount',{direction:t(direction),n:items.filter(n=>!n.runLevel).length})+(items.some(n=>n.runLevel)?' + '+t('runChecksTitle'):''):t(direction)+' · '+t('runChecksTitle')) + (items.some(n=>['running','retrying','submitted'].includes(displayState(n,data.decisions))) ? t('offWorking',{n:items.filter(n=>['running','retrying','submitted'].includes(displayState(n,data.decisions))).length}) : '') + (items.some(n=>data.decisions.some(d=>d.node===n.id)) ? t('offNeeds',{n:items.filter(n=>data.decisions.some(d=>d.node===n.id)).length}) : '');
      b.onclick=()=>{
        const horizontal=['offLeft','offRight'].includes(direction),back=['offLeft','offTop'].includes(direction);
        const sorted=[...items].sort((a,b)=>(layout.positions[a.id][horizontal?'x':'y']-layout.positions[b.id][horizontal?'x':'y'])*(back?-1:1));
        const p=layout.positions[sorted[0].id];
        viewport.scrollLeft=Math.max(0,p.x*scale-(w-p.width*scale)/2+ox);
        viewport.scrollTop=Math.max(0,p.y*scale-Math.max(12,(h-p.height*scale)/2)+oy);outside();viewport.focus({preventScroll:true});
      };
    }
  }
  let snapTimer=null,panIntent=false;
  function snapTitles(){
    if(!panIntent||!layout)return;panIntent=false;
    const vr=viewport.getBoundingClientRect(),titles=[...nodes.values()].map(e=>e.querySelector('.node-title')?.getBoundingClientRect()).filter(Boolean);
    const x=viewport.scrollLeft,y=viewport.scrollTop;
    viewport.scrollLeft=snapTitleOffset(x,viewport.clientWidth,viewport.scrollWidth-viewport.clientWidth,titles.map(r=>[r.x-vr.x+x,r.right-vr.x+x]));
    viewport.scrollTop=snapTitleOffset(y,viewport.clientHeight,viewport.scrollHeight-viewport.clientHeight,titles.map(r=>[r.y-vr.y+y,r.bottom-vr.y+y]));
    rememberScroll();outside();
  }
  viewport.addEventListener('scroll',()=>{
    if(scrollPosition.left!==viewport.scrollLeft || scrollPosition.top!==viewport.scrollTop)automatic=false;
    rememberScroll();outside();updateReadout();if(panIntent){clearTimeout(snapTimer);snapTimer=setTimeout(snapTitles,160);}
  });
  function updateReadout() {
    const fits=layout && layout.bounds.width*scale<=viewport.clientWidth && layout.bounds.height*scale<=viewport.clientHeight;
    fitButton.textContent=t('fit');
    fitButton.removeAttribute('aria-pressed');
    overviewNote.title=t('overviewHelp');overviewNote.hidden=false;overviewLabel.setAttribute('aria-pressed',String(level==='overview'));detailButton.setAttribute('aria-pressed',String(level==='detail'));map.dataset.level=level;map.dataset.fitted=String(automatic&&fits);map.dataset.scale=String(scale);
  }
  function size() {
    if(!layout)return;
    if(map.getBoundingClientRect){
      const available=Math.max(300,innerHeight-map.getBoundingClientRect().top-38);
      map.style.height=available+'px';
      $('panel').style.maxHeight=matchMedia('(max-width:760px)').matches?'none':available+'px';
      $('panel').style.height=$('panel').style.maxHeight;
    }
    const w=viewport.clientWidth||900,h=viewport.clientHeight||600;
    if(!placed)origin={x:Math.max(0,(w-layout.bounds.width*scale)/2),y:Math.max(0,(h-layout.bounds.height*scale)/2)};
    Object.assign(stage.style,{left:origin.x+'px',top:origin.y+'px',width:layout.bounds.width+'px',height:layout.bounds.height+'px',transform:`scale(${scale})`});
    stage.style.setProperty('--map-text',Math.max(14,12/scale)+'px');
    Object.assign(spacer.style,{width:layout.bounds.width*scale>w?layout.bounds.width*scale+'px':'100%',height:layout.bounds.height*scale>h?layout.bounds.height*scale+'px':'100%'});
    if(!$('panel').hidden && $('panel').onscroll)$('panel').onscroll();
    zoomText.textContent=t(level==='overview'?'overviewLevel':'detailLevel')+' '+Math.round(scale*100)+'%';zoomOut.disabled=level==='overview'&&scale<=MIN_FIT_SCALE;zoomOut.title=zoomOut.disabled?t('minZoom'):t('zoomOut');zoomIn.disabled=level==='detail'&&scale>=1.6;updateReadout();rememberScroll();outside();
  }
  const setRect=(element,rect)=>Object.assign(element.style,{left:rect.x+'px',top:rect.y+'px',width:rect.width+'px',height:rect.height+'px'});
  function update(next,id) {
    rawData=next;next=planFlow(next,language);
    if(layout)size();
    const planKey=JSON.stringify([next.nodes.map(n=>[n.id,n.title,n.kind,n.target]),next.edges.map(e=>[e.from,e.to,e.relation,e.label])]);
    if(planKey!==layoutKey){layoutKey=planKey;if(!placed){automatic=true;level='detail';}}
    const reveal=id&&id!==chosenNode;data=next;chosenNode=id;map.classList.toggle('has-expanded',!!id);
    layouts=Object.fromEntries(['detail','overview'].map(level=>[level,layeredLayout(data.nodes,data.edges.map(e=>({...e,label:e.label?label(e.label):''})),data.decisions,true,{level,language,wrapLongChains:true})]));
    layouts.overview=compactOverview(layouts.overview,viewport.clientWidth-24);
    layout=layouts[level];
    size();
    if(!placed && viewport.clientWidth){const fitted=fitGraph(layouts,viewport.clientWidth-24,viewport.clientHeight-24);level=fitted.level;scale=fitted.scale;layout=layouts[level];}
    const focused=document.activeElement?.closest?.('[data-node]')?.dataset.node,focusedChip=document.activeElement?.dataset?.chip;
    const activeIds=new Set(data.nodes.map(n=>n.id));
    for(const [key,element] of nodes)if(!activeIds.has(key)){element.remove();nodes.delete(key);}
    for(const n of data.nodes) {
      const expanded=n.id===chosenNode;
      const signature=JSON.stringify([level,n,data.decisions.filter(d=>d.node===n.id)]);
      let element=nodes.get(n.id);
      if(!element){element=el('div',undefined,'node-position');nodes.set(n.id,element);stage.append(element);}
      if(element.dataset.signature!==signature) {
        const card=nodeCard(n,expanded,level),before=seen.get(n.id),tone=cardTone(n);
        // One-shot motion only for a change observed while the page was open.
        if(before&&cometCount(n)>before.comets)card.classList.add('changed');
        else if(before&&before.tone!==tone&&['passed','current'].includes(tone))card.classList.add('changed');
        element.replaceChildren(card);element.dataset.signature=signature;
      }
      seen.set(n.id,{tone:cardTone(n),comets:cometCount(n)});
    }
    clear(key);
    name.textContent=planCounts(data.plan_counts||{work:data.nodes.filter(n=>n.kind==='work').length,review:data.nodes.filter(n=>n.kind==='review').length,decision:data.nodes.filter(n=>n.kind==='decision').length},language);mapTitle.classList.toggle('returned-title',$('flow').classList.contains('sent-plan'));
    for(const [state,word] of [['open','lineSampleOpen'],['closed','lineSampleClosed'],['review','lineSampleReview']]){
      if(!layout.routes.some(r=>(r.relation==='reviews'?'review':r.gateState==='open'?'open':'closed')===state))continue;
      const sample=el('span',undefined,'line-sample '+state),caption=el('span',t(word));caption.dataset.i18n=word;sample.append(el('i'),caption);key.append(sample);
    }
    const states=el('div',undefined,'state-legend');
    for(const state of [...new Set(data.nodes.map(n=>displayState(n,data.decisions)))]) states.append(el('span',`${statusGlyph(state)} ${stateWords(state,language).name}`,'state-key state-'+state));
    if(data.nodes.some(n=>cometCount(n)>0)&&!data.nodes.some(n=>displayState(n,data.decisions)==='returned'))states.append(el('span','↩ '+t('returned'),'state-key'));
    if(data.nodes.some(n=>n.kind==='review')) { const mark=el('span',undefined,'state-key review-key'); mark.append(typeIcon('review'),el('span',t('review')));states.append(mark); }
    if(data.planned_questions?.length)states.append(el('span',t('questionsMark'),'state-key'));
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
    if(!data.nodes.length){placed=false;initialFitPending=false;automatic=true;level='detail';}
    else if(!placed&&viewport.clientWidth){
      const fitted=fitGraph(layouts,viewport.clientWidth-24,viewport.clientHeight-24);
      if(fitted.level!==level||Math.abs(fitted.scale-scale)>.001){level=fitted.level;scale=fitted.scale;update(rawData,chosenNode);return;}
      placed=true;start();
      if(!initialFitPending && document.fonts){
        initialFitPending=true;
        // Fonts and the plan band finish sizing after the first DOM update.
        document.fonts.ready.then(()=>setTimeout(()=>{
          if(automatic)fit();
        },0));
      }
    }

    outside();
    if(focused)nodes.get(focused)?.querySelector('button')?.focus({preventScroll:true});
    if(focusedChip)[...chips.values()].find(e=>e.dataset.chip===focusedChip&&e.tagName==='BUTTON')?.focus({preventScroll:true});
  }
  map.addEventListener('keydown',e=>{
    if(!['map-viewport','map'].includes(e.target.id||e.target.className))return;
    if(['+','=','-','0','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))e.preventDefault();
    if(e.key==='+'||e.key==='=')zoom(.1);if(e.key==='-')zoom(-.1);if(e.key==='0')fit();
    if(e.key.startsWith('Arrow')){automatic=false;panIntent=true;}
    if(e.key==='ArrowLeft')viewport.scrollLeft-=80;if(e.key==='ArrowRight')viewport.scrollLeft+=80;
    if(e.key==='ArrowUp')viewport.scrollTop-=80;if(e.key==='ArrowDown')viewport.scrollTop+=80;
  });
  let drag=null;
  viewport.addEventListener('pointerdown',e=>{if(e.target.closest('button,summary,a'))return;automatic=false;drag={x:e.clientX,y:e.clientY,left:viewport.scrollLeft,top:viewport.scrollTop};if(e.pointerType==='touch'){drag=null;return;}viewport.setPointerCapture(e.pointerId);viewport.classList.add('panning');});
  viewport.addEventListener('pointermove',e=>{if(drag){viewport.scrollLeft=drag.left+drag.x-e.clientX;viewport.scrollTop=drag.top+drag.y-e.clientY;}});
  const release=()=>{drag=null;viewport.classList.remove('panning');panIntent=true;snapTitles();};viewport.addEventListener('pointerup',release);viewport.addEventListener('pointercancel',release);
  viewport.addEventListener('wheel',e=>{
    panIntent=true;
    if(e.ctrlKey || e.metaKey){e.preventDefault();const r=viewport.getBoundingClientRect();zoom(e.deltaY<0?.1:-.1,{x:e.clientX-r.x,y:e.clientY-r.y});}
    else automatic=false;
  },{passive:false});
  let lastWidth=0,lastHeight=0;
  function resize(selection = false) {
    if(!layout)return;
    const w=viewport.clientWidth,h=viewport.clientHeight;
    if(w===lastWidth&&h===lastHeight)return;
    lastWidth=w;lastHeight=h;
    size();
  }
  new ResizeObserver(()=>resize()).observe(viewport);
  function revealSelection() {
    const p=layout?.positions[chosenNode];if(!p || !viewport.clientWidth)return;
    const w=viewport.clientWidth,h=viewport.clientHeight,ox=origin.x,oy=origin.y;
    const left=p.x*scale+ox,top=p.y*scale+oy,right=left+p.width*scale,bottom=top+p.height*scale;
    if(left<viewport.scrollLeft+12)viewport.scrollLeft=Math.max(0,left-12);
    else if(right>viewport.scrollLeft+w-12)viewport.scrollLeft=right-w+12;
    if(top<viewport.scrollTop+12)viewport.scrollTop=Math.max(0,top-12);
    else if(bottom>viewport.scrollTop+h-12)viewport.scrollTop=bottom-h+12;
    rememberScroll();outside();
  }
  return {update,select:id=>{
    chosenNode=id;
    for(const [key,element] of nodes){element.firstElementChild.classList.toggle('expanded',key===id);element.querySelector('.node-header').setAttribute('aria-expanded',String(key===id));}
    resize(true);size();revealSelection();
  },wake:size};
}
renderer = createMap(); if(view)renderer.update(view,selected);
}
