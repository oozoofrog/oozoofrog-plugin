---
name: auto-flow
description: 작업 난이도를 분류해 단계마다 맞는 Claude 모델(Haiku·Sonnet·Opus·Fable)과 effort로 계획·실행·통합 검증하는 Workflow를 실행한다. 실패하면 한 번만 모델이나 effort를 올려 수정한다. "/auto-flow", "auto-flow로 해줘", "모델 알아서 골라서 워크플로로 진행해줘", "토큰 효율적으로 워크플로 돌려줘", "교차 검토까지 해줘", "Codex도 섞어서 진행해줘", "보안 점검·공격 시나리오까지 워크플로로 해줘"에 사용한다. 보안 점검은 security tier(Fable)로 돌리고, Fable 안전장치에 막힌 단위만 사용자가 허용하면 Mythos 5.2로 넘긴다. T3 Code에서는 Codex 계정을 남은 사용량 기준으로 골라 교차 검토와 실행 분담에 쓴다.
---

# auto-flow

이 스킬을 불렀다는 것 자체가 Workflow 실행에 대한 사용자 동의다.

## 실행 환경

- 1~5절의 Workflow 경로는 Claude Code의 Workflow 도구가 필요하다. Codex 또는 이 도구가 없는 세션에서는 사용자에게 실행할 수 없다고 알리고 Workflow를 흉내 내지 않는다.
- Codex에는 스킬만 제공된다. `workflow.js`와 Plugin 에이전트 두 개는 Claude Code에서만 동작한다.
- 6절의 교차 제공자 단계는 T3 Code의 `delegate_task` 도구와 `~/.t3/caches/*.json` 사용량 데이터가 필요하다. 도구나 쓸 수 있는 사용량 데이터가 없으면 해당 단계를 실행하지 않고 알린다.
- Claude Code가 스킬을 읽을 때 출력하는 `Base directory for this skill: <path>`를 이 스킬의 기준 디렉터리로 쓴다. 아래의 `workflow.js`와 `pick-provider.py`는 모두 그 디렉터리 아래 파일로 해석한다.

## 리더 세션과 하위 세션

- 이 스킬을 요청받은 세션이 리더다. 분류, 단위 나누기, 하위 세션 생성, 결과 통합 판단, 사용자 보고는 리더가 한다.
- 사용자에게 하는 답을 뺀 모든 진행은 영어로 한다. 사용자가 한국어로 지시했더라도 그 지시를 영어로 옮겨 전달한다.
- 하위 세션(Workflow 에이전트, `delegate_task` 자식)에 주는 지시는 모두 영어로 쓴다. Workflow args의 `task`, `units`, `context`, `validator` 설명과 `delegate_task`의 `task`가 여기에 해당한다. 코드, 경로, 사용자에게 보일 문구처럼 원문이 필요한 것은 그대로 인용한다.
- 하위 세션은 영어로 작업하고 결과를 리더에게만 돌려준다. 사용자에게 직접 묻지 않고, 막힌 점과 결정이 필요한 점은 결과에 적는다. 하위 세션이 다시 하위 세션을 만들지 않는다.
- Workflow의 `log`와 결과의 `notes`도 영어다. 리더가 사용자의 언어로 옮겨 보고한다.
- 사용자와의 대화와 보고는 리더가 사용자의 언어로 한다.

## 1. 분류 (리더 세션이 직접)

지금까지의 대화 맥락으로 tier를 정한다. 확인이 필요하면 코드를 짧게만 훑는다. 두 tier 사이에서 망설여지면 높은 쪽을 고른다.

| tier | 기준 | 실행 모델 |
|---|---|---|
| direct | 파일 1개, 수 줄 수준이고 위치를 이미 안다 | 워크플로 없이 메인이 직접 한다 |
| bulk | 같은 규칙을 많은 항목에 반복(분류·추출·태깅·기계적 치환), 항목끼리 독립 | haiku/medium |
| scoped | 명세가 분명, 파일 약 5개 이하, 설계 결정 없음, 테스트로 확인 가능 | sonnet/medium |
| daily | 원인·접근을 스스로 찾아야 함(디버깅, 여러 모듈 기능, 설계 선택 1~2개). 애매하면 여기 | opus/medium |
| large | 모듈 경계·공개 인터페이스 변경, 리팩터링·마이그레이션·아키텍처, 파일 약 15개 이상 | fable 계획 → 단위별 sonnet/opus 실행 |
| security | 사용자가 소유한 시스템의 보안 점검·위협 모델·공격 시나리오 시험(레드팀, PoC). 취약점을 찾는 것이 목적이면 범위가 작아도 여기 | fable/high, 검증 opus/high |

한 단계 올리는 조건: 자동 검증 수단이 없다 / 요구가 모호하다 / 되돌리기 어렵다(데이터 마이그레이션, 공개 API, 보안, 동시성) / 명세는 분명하지만 본질적으로 어렵다.

보안 코드를 고치는 일반 변경은 security가 아니라 원래 tier에서 한 단계 올린다. security는 결함을 찾는 작업이고, 실행 단위는 안전장치에 막히면 우회하지 않고 막힌 부분을 `blocked: "safeguard"`로 보고한다. 하위 세션에는 코드와 합성 시험 데이터만 넘기고 실제 카드·키·토큰·개인정보는 넘기지 않는다.

## 2. 단위 나누기 (large 제외)

- 서로 다른 파일 집합을 건드리는 독립 작업만 나눈다. 같은 파일을 두 단위가 고치면 합친다. 확신이 없으면 1개.
- 상한: bulk 6청크(청크당 20~50항목), scoped 2, daily 3, security 2(예: 앱별·표면별). large는 계획자가 최대 4개로 나눈다.
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
  "task": "The user's request, stated concretely, in English",
  "tier": "scoped",
  "units": ["Goal of unit 1", "Goal of unit 2"],
  "context": "Relevant files, constraints, and reproduction steps the leader already found",
  "validator": "bulk only, optional",
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
- `safeguardBlocked`가 비어 있지 않으면 단위별로 무엇이 막혔는지 보여 주고 7절대로 진행한다. 다른 Claude 모델로 자동 재시도하지 않는다.

## 6. 교차 제공자 단계 (T3 Code에서만)

T3 도구(`delegate_task`)가 없는 환경에서는 이 절을 건너뛴다. Workflow 안에서는 다른 제공자를 부를 수 없으므로, 이 단계는 메인 세션이 Workflow 앞뒤에서 직접 위임한다.

### 6.1 계정과 제공자 고르기

스킬 기준 디렉터리의 [pick-provider.py](pick-provider.py)를 절대 경로로 해석한 뒤 `python3 "<해석한 pick-provider.py 절대 경로>" <병렬 위임 수>`를 실행한다. 위임을 띄우기 직전마다 다시 실행한다.

- `assign`: 위임별로 쓸 Codex 계정이다. 남은 사용량이 많은 계정부터, 남은 비율대로 나뉜다. 90% 이상 쓴 계정은 다른 계정이 있으면 빠진다.
- `claude.preferCodexForExecution`이 true면(Claude 주간 사용량 80% 이상) 6.3의 실행 분담을 쓴다.
- `warnings`가 있으면 사용자에게 그대로 알린다. 쓸 수 있는 계정이 없으면 이 단계를 하지 않고 알린다. 다른 제공자로 바꾸지 않는다.
- 이 스레드에서 첫 위임 전에 `orchestrator_capabilities`를 한 번 호출해 모델이 실제로 있는지 확인한다.
- 모든 `delegate_task`에 `title`을 `<역할> · <모델>/<effort>` 형식으로 준다. 예: `review · gpt-6.1-sol/high`, `exec:u2 · gpt-6-luna/medium`. 자식 스레드 목록에서 모델과 effort가 바로 보이게 하기 위해서다.

### 6.2 교차 검토 (Workflow가 끝난 뒤)

| 조건 | 검토 모델 |
|---|---|
| daily | gpt-6.1-sol / high |
| large, security, 또는 되돌리기 어려운 변경(데이터 마이그레이션, 공개 API, 보안, 동시성) | gpt-6-astra / high |
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

Workflow 대신 단위마다 `delegate_task`로 실행한다. `task`는 영어로 쓰고 목표, 소유 파일, 수용 기준, 검증 명령, 리더에게 돌려줄 결과 형식(변경 파일, 돌린 검사와 결과, 확신이 낮은 부분, 막힌 점)을 넣는다. 사용자에게 묻지 말고 영어로 리더에게 보고하라는 문장도 넣는다.

| tier | 실행 모델 |
|---|---|
| bulk | gpt-6-luna / medium |
| scoped | gpt-6.1-sol / medium |
| daily | gpt-6.1-sol / high |
| large | 메인이 2절 규칙으로 최대 4단위로 나눠 단위별 scoped·daily 모델 사용. 나눌 수 없으면 gpt-6-astra / high |
| security | gpt-6-astra / high |

- 단위가 2개 이상이면 `isolation: "worktree"`, `mode: "async"`로 띄우고 알림을 기다린다. 확인하려고 반복 조회하지 않는다. 단위가 1개면 `shared`로 둔다.
- 위임은 한 번에 최대 4개다.
- 검토는 반대 계열이 맡는다. Codex가 실행했으면 `auto-flow:flow-verifier` Plugin 에이전트(Claude Opus)로 통합과 검증을 한다.
- gpt-6.1 계열은 reasoningEffort 기본값이 low이므로 항상 값을 명시한다.
- gpt-6.1-terra와 이전 세대(gpt-6-sol, gpt-5.6-*)는 사용자가 이름을 말할 때만 쓴다.

### 6.4 보고

5절 보고에 더해, 위임마다 쓴 계정·모델과 그때의 남은 사용량, 자식 스레드 링크를 적는다.

## 7. Mythos 대체 (security tier, 사용자가 허용할 때만)

Claude Mythos 5.2(`claude-mythos-5-2`)는 Fable 5.2와 같은 모델에서 사이버보안·생명과학 안전장치를 완화한 버전이다. 능력은 같으므로 일반 실패(defect·incomplete·approach)에는 쓰지 않는다. 쓸 수 있는 경우는 security 단위가 Fable 안전장치에 막혔을 때 하나뿐이다.

1. Workflow 결과의 `safeguardBlocked`가 비어 있지 않으면, 막힌 단위와 이유를 사용자에게 보고하고 Mythos로 넘길지 묻는다. 이번 요청에서 사용자가 Mythos 대체를 미리 허용했더라도 이 질문은 생략하지 않는다. 넘기는 내용과 데이터 보관 조건을 보여 줘야 하기 때문이다.
2. 질문에 함께 적을 것:
   - Mythos는 Anthropic 검증 프로그램(예: Cyber Verification Program)을 통과한 조직만 호출할 수 있다.
   - 기본 30일 데이터 보관이 필수다.
   - 넘길 내용은 막힌 단위의 목표, 관련 코드 경로, 합성 시험 데이터뿐이다.
3. 사용자가 승인하면 막힌 단위만 넘긴다. 지시문은 영어로 쓰고 목표, 소유 범위(수정 여부), 방어 목적이라는 점, 실제 비밀 정보를 읽거나 출력하지 말 것, 결과 형식을 넣는다.
   - T3 Code에서는 먼저 `orchestrator_capabilities`로 `claude-mythos-5-2`가 목록에 있는지 확인한다. 있으면 `delegate_task`(`target.model: "claude-mythos-5-2"`, effort 명시, `title: "security:<unit> · claude-mythos-5-2/<effort>"`)로 넘긴다. 자식 스레드에 기록이 남기 때문이다.
   - T3가 아니거나 목록에 없을 때만 백그라운드 Claude Code 세션을 쓴다. 지시문은 파일로 저장해 넘긴다. `--allowedTools`·`--disallowedTools`는 값을 여러 개 받으므로 그 뒤에 지시문을 인자로 붙이면 도구 이름으로 읽힌다. 이 옵션을 쓸 때는 지시문을 표준 입력으로 넘긴다.

```sh
claude --bg --model claude-mythos-5-2 --effort high -n "security:<unit> · mythos-5.2/high" "$(cat <지시문 파일 절대 경로>)"
```

4. 모델 ID가 거부되거나 계정에 접근 권한이 없으면, 그 오류를 그대로 보고하고 멈춘다. 다른 모델로 바꾸지 않는다.
5. Mythos 결과도 6.2의 교차 검토(gpt-6-astra / high) 대상이다. 보고에는 Mythos를 쓴 단위와 넘긴 이유를 적는다.

## 상향 규칙 (스크립트가 자동 적용, 1회)

- defect·incomplete: 같은 모델, effort 한 단계 위로 올린다(opus는 high까지).
- approach: 모델 한 단계 위, effort는 medium(haiku → sonnet → opus → fable).
- fable/high에서도 approach로 실패하면 자동 상향하지 않고 보고한다.
- bulk의 실패 항목과 lowConfidence 항목은 sonnet/medium으로 다시 처리한다.
- safeguard(security 단위가 안전장치에 막힘): 자동 상향하지 않는다. `safeguardBlocked`로 돌려주고 리더가 7절을 따른다.
