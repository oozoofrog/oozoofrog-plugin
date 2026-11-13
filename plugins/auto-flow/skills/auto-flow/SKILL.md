---
name: auto-flow
description: 작업 난이도를 분류해 단계마다 맞는 Claude 모델(Haiku·Sonnet·Opus·Fable)과 effort로 계획·실행·통합 검증하는 Workflow를 실행한다. 실패하면 한 번만 모델이나 effort를 올려 수정한다. "/auto-flow", "auto-flow로 해줘", "모델 알아서 골라서 워크플로로 진행해줘", "토큰 효율적으로 워크플로 돌려줘", "교차 검토까지 해줘", "Codex도 섞어서 진행해줘"에 사용한다. T3 Code에서는 Codex 계정을 남은 사용량 기준으로 골라 교차 검토와 실행 분담에 쓴다.
---

# auto-flow

이 스킬을 불렀다는 것 자체가 Workflow 실행에 대한 사용자 동의다.

## 실행 환경

- 1~5절의 Workflow 경로는 Claude Code의 Workflow 도구가 필요하다. Codex 또는 이 도구가 없는 세션에서는 사용자에게 실행할 수 없다고 알리고 Workflow를 흉내 내지 않는다.
- Codex에는 스킬만 제공된다. `workflow.js`와 Plugin 에이전트 두 개는 Claude Code에서만 동작한다.
- 6절의 교차 제공자 단계는 T3 Code의 `delegate_task` 도구와 `~/.t3/caches/*.json` 사용량 데이터가 필요하다. 도구나 쓸 수 있는 사용량 데이터가 없으면 해당 단계를 실행하지 않고 알린다.
- Claude Code가 스킬을 읽을 때 출력하는 `Base directory for this skill: <path>`를 이 스킬의 기준 디렉터리로 쓴다. 아래의 `workflow.js`와 `pick-provider.py`는 모두 그 디렉터리 아래 파일로 해석한다.

## 1. 분류 (메인 세션이 직접)

지금까지의 대화 맥락으로 tier를 정한다. 확인이 필요하면 코드를 짧게만 훑는다. 두 tier 사이에서 망설여지면 높은 쪽을 고른다.

| tier | 기준 | 실행 모델 |
|---|---|---|
| direct | 파일 1개, 수 줄 수준이고 위치를 이미 안다 | 워크플로 없이 메인이 직접 한다 |
| bulk | 같은 규칙을 많은 항목에 반복(분류·추출·태깅·기계적 치환), 항목끼리 독립 | haiku/medium |
| scoped | 명세가 분명, 파일 약 5개 이하, 설계 결정 없음, 테스트로 확인 가능 | sonnet/medium |
| daily | 원인·접근을 스스로 찾아야 함(디버깅, 여러 모듈 기능, 설계 선택 1~2개). 애매하면 여기 | opus/medium |
| large | 모듈 경계·공개 인터페이스 변경, 리팩터링·마이그레이션·아키텍처, 파일 약 15개 이상 | fable 계획 → 단위별 sonnet/opus 실행 |

한 단계 올리는 조건: 자동 검증 수단이 없다 / 요구가 모호하다 / 되돌리기 어렵다(데이터 마이그레이션, 공개 API, 보안, 동시성) / 명세는 분명하지만 본질적으로 어렵다.

## 2. 단위 나누기 (large 제외)

- 서로 다른 파일 집합을 건드리는 독립 작업만 나눈다. 같은 파일을 두 단위가 고치면 합친다. 확신이 없으면 1개.
- 상한: bulk 6청크(청크당 20~50항목), scoped 2, daily 3. large는 계획자가 최대 4개로 나눈다.
- bulk는 결과를 자동 확인할 명령이 있으면 `validator`로 넘긴다.

## 3. worktree 여부

`worktree: true`는 아래를 모두 만족할 때만 준다. 아니면 단위를 현재 작업 트리에서 순서대로 실행한다.
- git 저장소다.
- 단위가 2개 이상이고 파일을 수정한다. large는 계획 결과에 따라 달라지므로, 다른 조건만 맞으면 true로 둔다.
- 작업과 관련된 커밋되지 않은 변경이 없다. worktree는 HEAD에서 시작하므로 그런 변경이 보이지 않는다.

## 4. 실행

1. `date +%Y%m%d%H%M%S`로 runId를 만든다.
2. 스킬 기준 디렉터리의 [workflow.js](workflow.js)를 절대 경로로 해석한 뒤, 그 결과를 Workflow 도구의 `scriptPath`로 넘긴다. args:

```json
{
  "task": "사용자 요청을 구체적으로",
  "tier": "scoped",
  "units": ["단위1 목표", "단위2 목표"],
  "context": "메인이 이미 파악한 관련 파일·제약·재현 방법",
  "validator": "bulk일 때만, 선택",
  "worktree": false,
  "runId": "20261113231500"
}
```

`context`를 충실히 채울수록 하위 에이전트가 같은 탐색을 반복하지 않아 토큰이 준다.

## 5. 결과 보고

- `outcome`, 단위별 사용 모델과 변경 파일, 검증에서 돌린 명령을 보고한다.
- `notes`에 실행하지 못한 단위가 있으면 남은 단위로 다시 호출할지 사용자에게 묻는다.
- `unresolved`나 최종 fail이 있으면 findings를 그대로 보여 주고 다음 행동을 제안한다. 자동으로 재시도하지 않는다.
- 결과는 커밋되지 않은 변경으로 남는다. 커밋은 사용자가 결정한다.
- worktree를 썼다면 `git worktree list`와 `git branch --list 'auto-flow/*'`로 정리됐는지 확인하고, 남은 것이 있으면 위치를 보고한다.

## 6. 교차 제공자 단계 (T3 Code에서만)

T3 도구(`delegate_task`)가 없는 환경에서는 이 절을 건너뛴다. Workflow 안에서는 다른 제공자를 부를 수 없으므로, 이 단계는 메인 세션이 Workflow 앞뒤에서 직접 위임한다.

### 6.1 계정과 제공자 고르기

스킬 기준 디렉터리의 [pick-provider.py](pick-provider.py)를 절대 경로로 해석한 뒤 `python3 "<해석한 pick-provider.py 절대 경로>" <병렬 위임 수>`를 실행한다. 위임을 띄우기 직전마다 다시 실행한다.

- `assign`: 위임별로 쓸 Codex 계정이다. 남은 사용량이 많은 계정부터, 남은 비율대로 나뉜다. 90% 이상 쓴 계정은 다른 계정이 있으면 빠진다.
- `claude.preferCodexForExecution`이 true면(Claude 주간 사용량 80% 이상) 6.3의 실행 분담을 쓴다.
- `warnings`가 있으면 사용자에게 그대로 알린다. 쓸 수 있는 계정이 없으면 이 단계를 하지 않고 알린다. 다른 제공자로 바꾸지 않는다.
- 이 스레드에서 첫 위임 전에 `orchestrator_capabilities`를 한 번 호출해 모델이 실제로 있는지 확인한다.

### 6.2 교차 검토 (Workflow가 끝난 뒤)

| 조건 | 검토 모델 |
|---|---|
| daily | gpt-6.1-sol / high |
| large, 또는 되돌리기 어려운 변경(데이터 마이그레이션, 공개 API, 보안, 동시성) | gpt-6-astra / high |
| scoped, bulk, direct | 하지 않는다(사용자가 요청하면 gpt-6.1-sol / high) |

- Workflow의 `outcome`이 fail이면 하지 않는다. 먼저 5절대로 보고한다.
- `delegate_task`를 `role: "review"`, `isolation: "shared"`, `mode: "wait"`로 호출한다. 변경이 커밋되지 않은 상태이므로 worktree를 쓰지 않는다.
- 자식은 이 대화를 보지 못한다. `task`는 영어로, 아래 내용을 모두 넣어 쓴다.

```
Review the uncommitted changes in <absolute repo path> (git diff HEAD).
Goal: <what the change must achieve>
Acceptance criteria: <criteria>
Changed files: <list from workflow result>
Checks already run and passed: <commands>
Do not modify files. Do not re-run the full build unless a finding needs it.
Try to refute the change: correctness, missed edge cases, regressions, contract breaks.
Reply in English, at most 40 lines:
VERDICT: pass | fail
FINDINGS: one per line — severity(high|med|low) | file:line | defect | how to reproduce
Report only defects you can point to in the code. No style comments.
```

- 지적이 작으면 메인이 직접 고친다. 크면(high가 있거나 여러 파일에 걸침) 3절 기준에 맞는 모델로 수정을 맡기고, 새 `delegate_task`로 한 번만 다시 검토한다. 그래도 fail이면 멈추고 보고한다.
- 검토 지적을 받아들이지 않을 때는 근거를 사용자에게 함께 보고한다.

### 6.3 실행 분담 (Claude 사용량이 높거나 사용자가 Codex 실행을 요청할 때)

Workflow 대신 단위마다 `delegate_task`로 실행한다.

| tier | 실행 모델 |
|---|---|
| bulk | gpt-6-luna / medium |
| scoped | gpt-6.1-sol / medium |
| daily | gpt-6.1-sol / high |
| large | 메인이 2절 규칙으로 최대 4단위로 나눠 단위별 scoped·daily 모델 사용. 나눌 수 없으면 gpt-6-astra / high |

- 단위가 2개 이상이면 `isolation: "worktree"`, `mode: "async"`로 띄우고 알림을 기다린다. 확인하려고 반복 조회하지 않는다. 단위가 1개면 `shared`로 둔다.
- 위임은 한 번에 최대 4개다.
- 검토는 반대 계열이 맡는다. Codex가 실행했으면 `auto-flow:flow-verifier` Plugin 에이전트(Claude Opus)로 통합과 검증을 한다.
- gpt-6.1 계열은 reasoningEffort 기본값이 low이므로 항상 값을 명시한다.
- gpt-6.1-terra와 이전 세대(gpt-6-sol, gpt-5.6-*)는 사용자가 이름을 말할 때만 쓴다.

### 6.4 보고

5절 보고에 더해, 위임마다 쓴 계정·모델과 그때의 남은 사용량, 자식 스레드 링크를 적는다.

## 상향 규칙 (스크립트가 자동 적용, 1회)

- defect·incomplete: 같은 모델, effort 한 단계 위로 올린다(opus는 high까지).
- approach: 모델 한 단계 위, effort는 medium(haiku → sonnet → opus → fable).
- fable/high에서도 approach로 실패하면 자동 상향하지 않고 보고한다.
- bulk의 실패 항목과 lowConfidence 항목은 sonnet/medium으로 다시 처리한다.
