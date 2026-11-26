# fstack 명령 이름

원하는 결과를 한국어로 요청하거나 아래 이름으로 직접 호출하세요. 예를 들어 Codex에서는 `$fstack:summarize-progress`, Claude Code에서는 `/fstack:summarize-progress`로 진행 상황을 확인합니다. 기본 호출 이름은 `fstack`입니다.

## 작업별 명령

| 원하는 작업 | 2.0 명령 | 1.x 명령 |
| --- | --- | --- |
| 인터페이스 설계 | [`design-interfaces`](skills/design-interfaces/SKILL.md) | `architect` |
| 여러 해법 비교·통합 | [`compare-solutions`](skills/compare-solutions/SKILL.md) | `arena` |
| 개인 작업 방식 정리 | [`create-personal-workflow`](skills/create-personal-workflow/SKILL.md) | `automate-me` |
| 성능 측정 검토 | [`verify-benchmark`](skills/verify-benchmark/SKILL.md) | `benchmark-checklist` |
| 변경 영향 확인 | [`assess-change-impact`](skills/assess-change-impact/SKILL.md) | `blast-radius` |
| 쉽게 설명 | [`explain-simply`](skills/explain-simply/SKILL.md) | `bro` |
| 반복 실수 방지 | [`prevent-repeated-mistakes`](skills/prevent-repeated-mistakes/SKILL.md) | `correct` |
| 모델 검증 스킬 만들기 | [`create-model-checker-skill`](skills/create-model-checker-skill/SKILL.md) | `create-formal-verification-skill` |
| 앱 동작 검증 스킬 만들기 | [`create-app-check-skill`](skills/create-app-check-skill/SKILL.md) | `create-verification-skill` |
| 작업 절차 설계 | [`design-workflow`](skills/design-workflow/SKILL.md) | `figure-it-out` |
| 코드 동작 설명 | [`explain-code`](skills/explain-code/SKILL.md) | `how` |
| 이해한 목표 확인 | [`confirm-goal`](skills/confirm-goal/SKILL.md) | `in-your-own-words` |
| 여러 모델로 변경 검토 | [`review-with-multiple-models`](skills/review-with-multiple-models/SKILL.md) | `interrogate` |
| 진행 상황 요약 | [`summarize-progress`](skills/summarize-progress/SKILL.md) | `ketchup` |
| 진행 상황 영상 요약 | [`summarize-progress-on-video`](skills/summarize-progress-on-video/SKILL.md) | `ketchup-video` |
| 모델 검증 스킬 갱신 | [`update-model-checker-skill`](skills/update-model-checker-skill/SKILL.md) | `maintain-formal-verification-skill` |
| 앱 동작 검증 스킬 갱신 | [`update-app-check-skill`](skills/update-app-check-skill/SKILL.md) | `maintain-verification-skill` |
| 웹훅 연동 화면 만들기 | [`build-webhook-ui`](skills/build-webhook-ui/SKILL.md) | `make-bot-ui` |
| 코드 주석 검토 | [`review-code-comments`](skills/review-code-comments/SKILL.md) | `no-comments` |
| 작업별 사용법 찾기 | [`find-workflows`](skills/find-workflows/SKILL.md) | `poteto-help` |
| 개발 절차 실행 | [`run-engineering-workflow`](skills/run-engineering-workflow/SKILL.md) | `poteto-mode` |
| 이전 작업 맥락 복원 | [`recover-work-context`](skills/recover-work-context/SKILL.md) | `recall` |
| 작업에서 배운 점 기록 | [`capture-lessons`](skills/capture-lessons/SKILL.md) | `reflect` |
| 아이디어에 맞는 전문 용어 찾기 | [`clarify-terminology`](skills/clarify-terminology/SKILL.md) | `reframe` |
| 모델 설정 | [`configure-models`](skills/configure-models/SKILL.md) | `setup-pstack` |
| 요청문 다듬기 | [`refine-request`](skills/refine-request/SKILL.md) | `sharpen` |
| 작업 판단 근거 기록 | [`record-decisions`](skills/record-decisions/SKILL.md) | `show-me-your-work` |
| 상태 전이 검증 | [`verify-state-transitions`](skills/verify-state-transitions/SKILL.md) | `statechart` |
| 병렬 작업 조율 | [`coordinate-workers`](skills/coordinate-workers/SKILL.md) | `swarm` |
| 테스트 주도 개발 | [`develop-test-first`](skills/develop-test-first/SKILL.md) | `tdd` |
| 완료한 작업 설명 | [`explain-completed-work`](skills/explain-completed-work/SKILL.md) | `teach` |
| 기술 문서 작성 | [`write-technical-docs`](skills/write-technical-docs/SKILL.md) | `technical-writing` |
| 타입스크립트 작성 | [`write-typescript`](skills/write-typescript/SKILL.md) | `typescript-best-practices` |
| 문장 다듬기 | [`edit-prose`](skills/edit-prose/SKILL.md) | `unslop` |
| 설계 이유 설명 | [`explain-design-decisions`](skills/explain-design-decisions/SKILL.md) | `why` |

## 개발 원칙

| 원하는 작업 | 2.0 명령 | 1.x 명령 |
| --- | --- | --- |
| 반복 실패의 전제 검증 | [`principle-test-assumptions`](skills/principle-test-assumptions/SKILL.md) | `principle-attack-the-premise` |
| 시스템 경계에서 입력 검증 | [`principle-validate-at-boundaries`](skills/principle-validate-at-boundaries/SKILL.md) | `principle-boundary-discipline` |
| 반복 작업 자동화 | [`principle-automate-repeatable-work`](skills/principle-automate-repeatable-work/SKILL.md) | `principle-build-the-lever` |
| 반복 지침을 검사 규칙으로 반영 | [`principle-enforce-learned-rules`](skills/principle-enforce-learned-rules/SKILL.md) | `principle-encode-lessons-in-structure` |
| 설계 대안 시제품 비교 | [`principle-prototype-alternatives`](skills/principle-prototype-alternatives/SKILL.md) | `principle-exhaust-the-design-space` |
| 사용자 경험 우선 | [`principle-prioritize-user-experience`](skills/principle-prioritize-user-experience/SKILL.md) | `principle-experience-first` |
| 측정값의 의미 검증 | [`principle-validate-measurements`](skills/principle-validate-measurements/SKILL.md) | `principle-explain-the-number` |
| 근본 원인 추적 | [`principle-trace-root-causes`](skills/principle-trace-root-causes/SKILL.md) | `principle-fix-root-causes` |
| 핵심 타입과 구조 설계 | [`principle-design-core-types`](skills/principle-design-core-types/SKILL.md) | `principle-foundational-thinking` |
| 작업 맥락 분량 관리 | [`principle-manage-context`](skills/principle-manage-context/SKILL.md) | `principle-guard-the-context-window` |
| 변경 범위 단순화 | [`principle-simplify-changes`](skills/principle-simplify-changes/SKILL.md) | `principle-laziness-protocol` |
| 재시도해도 안전한 작업 설계 | [`principle-design-retry-safe-operations`](skills/principle-design-retry-safe-operations/SKILL.md) | `principle-make-operations-idempotent` |
| 호출부 이전과 기존 API 제거 | [`principle-migrate-api-callers`](skills/principle-migrate-api-callers/SKILL.md) | `principle-migrate-callers-then-delete-legacy-apis` |
| 읽기 쉬운 코드 구성 | [`principle-simplify-code-reading`](skills/principle-simplify-code-reading/SKILL.md) | `principle-minimize-reader-load` |
| 도메인 규칙을 자료 구조로 표현 | [`principle-represent-domain-rules`](skills/principle-represent-domain-rules/SKILL.md) | `principle-model-the-domain` |
| 되돌릴 수 있는 작업 진행 | [`principle-proceed-on-reversible-work`](skills/principle-proceed-on-reversible-work/SKILL.md) | `principle-never-block-on-the-human` |
| 목표 구조까지 이전 | [`principle-complete-migrations`](skills/principle-complete-migrations/SKILL.md) | `principle-outcome-oriented-execution` |
| 실제 동작 검증 | [`principle-verify-real-behavior`](skills/principle-verify-real-behavior/SKILL.md) | `principle-prove-it-works` |
| 새 요구에 맞춰 설계 재검토 | [`principle-rethink-design`](skills/principle-rethink-design/SKILL.md) | `principle-redesign-from-first-principles` |
| 동시 쓰기 대상 분리 | [`principle-isolate-shared-writes`](skills/principle-isolate-shared-writes/SKILL.md) | `principle-separate-before-serializing-shared-state` |
| 단계별 결과 검증 | [`principle-verify-in-stages`](skills/principle-verify-in-stages/SKILL.md) | `principle-sequence-verifiable-units` |
| 추가 전 불필요한 코드 제거 | [`principle-remove-unused-code`](skills/principle-remove-unused-code/SKILL.md) | `principle-subtract-before-you-add` |
| 관찰 가능한 동작 테스트 | [`principle-test-observable-behavior`](skills/principle-test-observable-behavior/SKILL.md) | `principle-test-behavior-not-implementation` |
| 제약 조건을 타입으로 표현 | [`principle-encode-constraints-in-types`](skills/principle-encode-constraints-in-types/SKILL.md) | `principle-type-system-discipline` |
