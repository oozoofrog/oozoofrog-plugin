---
name: korean-travel-guidebook
description: 몇 가지 핵심 질문으로 여행 정보를 모으고 동행자와 보행 부담을 검토한 뒤 정확한 한국어 HTML 여행 가이드북을 만든다. 일정 조정, 현장 검색표, 출입국·교통·결제 실전 안내가 필요한 여행 계획 요청에 사용한다.
---

# 한국어 여행 가이드북

설명만 제안하고 끝내지 말고 실제 열리는 HTML을 전달한다. 사용자가 스킬 자체를 만드는 중이라면 여행지 설문을 시작하지 않는다. HTML이 기본이며 PDF는 요청할 때만 만든다.

## 진행 순서

1. [질문 흐름](references/question-flow.md)을 읽는다. 이미 확인된 정보는 다시 묻지 않는다. 첫 질문에는 아직 미확정인 **실제 동행 구성과 관련 연령·이동 조건**을 포함한다. 동행 정보가 서로 충돌할 때만 그 차이를 확인하고, 언급되지 않은 동행자를 자동 추가하지 않는다. 답변 전에는 미정으로 두고 어느 쪽에도 종속되지 않는 작업부터 한다.
2. [자료 검증](references/research-policy.md)과 [보행·일정 검사](references/walking-and-schedule.md)를 적용한다. **전체 여행의 동행자 부담을 먼저 평가하고 조정**한 뒤 첫날 가이드북을 완성한다. 매일 호텔 출발부터 귀가까지 7~8천 보를 목표로 잡고 1만 보 미만으로 보수적으로 계획한다. 측정 보증은 하지 않는다. 범위 상단이 1만 보 이상이면 축소·교통 대안으로 조정하거나 충족 불가를 표시한다.
3. [콘텐츠 계약](references/content-contract.md)에 따라 첫날을 실제 사용할 수 있게 쓴다. 확인되지 않은 운영정보·입출구·길찾기·사진·수치를 만들지 않는다. 사실, 후기, 추정, 미확인을 구분하고 조사 충돌은 참고자료에 둔다.
4. [실전 안내](references/practical-guide.md)는 일정 본문과 별도로 묶는다. 최신 화면과 버전을 검증한 경우에만 버튼 순서를 확정한다. 계정 생성·민감정보 입력·예약·결제 실행은 이 스킬의 안내 작성 권한에 포함되지 않는다.
5. `examples/fictional-input.json`의 필드 형태로 자료를 작성한다. `assets/template.html`과 `scripts/generate.py`를 사용하거나 같은 콘텐츠·디자인 계약을 지키는 HTML을 직접 만든다. 허가된 사진과 나눔고딕 폰트를 가능하면 내장하고 라이선스를 함께 보존한다. 지도·복사·사진 확대가 실패해도 원문과 외부 링크를 쓸 수 있게 한다.
6. 아래 도구와 [검수 계약](references/content-contract.md#검수)을 적용한다. 정적 검사는 사실 정확성이나 실제 화면 검증을 대신하지 않는다. 모든 통과·실패·미실행을 구분하여 보고한다.

아래 `/absolute/loaded-skill-root`는 실제 로드한 스킬 패키지 경로로 바꾼다. 기본 설치 위치나 `CODEX_HOME`을 가정하지 않고 사용자 프로젝트의 작업 디렉터리를 유지한다.

```bash
python3 /absolute/loaded-skill-root/scripts/generate.py /absolute/loaded-skill-root/examples/fictional-input.json /tmp/guidebook.html
python3 /absolute/loaded-skill-root/scripts/validate.py /tmp/guidebook.html
```

## 전달

실제 HTML 경로와 완성 범위, 전체 여행의 부담 조정, 남은 주요 미정 사항, 확인일, 온라인이 필요한 기능을 짧게 전달한다. 미정 때문에 가능한 작업을 멈추지 않는다. 보행 수치는 계획 추정이며 현장 여건에 따라 달라진다고 명시한다. 전역 설치·활성화는 실제 경로와 확인 증거가 있을 때만 완료라고 말한다. 이 패키지는 승인정책을 바꾸는 규칙이 아니다.
