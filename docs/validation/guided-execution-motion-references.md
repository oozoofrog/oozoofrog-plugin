# 온톨로지 파이프라인 모션 참고 자료

2026-11-11에 수집했습니다. 대상은 `serve_dashboard.py` 실시간 대시보드의 모션 그래픽 개선입니다. [기존 시각화 참고 자료](guided-execution-visual-references.md)에 있는 WebVOWL, Neo4j Bloom, D3/Cytoscape, React Flow 애니메이션 선, W3C 모션 기준은 다시 적지 않았습니다.

확인 수준은 항목마다 다음 셋 중 하나로 표시합니다.
- **원문 확인:** 원문을 직접 읽었습니다.
- **초록:** 초록이나 논문 소개 페이지까지만 읽었습니다.
- **2차:** 검색 요약이나 다른 사람의 해설에서 본 내용입니다. 적용 전에 원문을 확인해야 합니다.

제품 화면은 문서와 공개 이슈만 읽었고, 직접 조작해 보지 않았습니다.

## 현재 대시보드의 모션

- 첫 화면에서만 카드가 짧게 등장합니다(0.6초).
- 모든 의존선에 같은 주기(3.2초)의 점이 흐릅니다. 시작 시점만 선마다 다릅니다.
- 기록이 바뀌면 SVG를 통째로 다시 그립니다. 바뀐 카드를 따로 알려 주는 전환은 없습니다.
- 움직임 끄기 버튼이 있고, 시스템의 동작 줄이기 설정을 따릅니다. 상태는 색과 기호로 표시하고, 점이 흐르는 것은 장식입니다.

## 연구: 변하는 그래프와 애니메이션 전환

### Heer & Robertson, Animated Transitions in Statistical Data Graphics (InfoVis 2007)
원문 확인 · [PDF](https://homes.cs.washington.edu/~jheer/files/2007-AnimatedTrans-InfoVis.pdf)

- **일치성(Congruence)**
  - 전환 중간 상태도 올바른 그래프여야 합니다.
  - 의미가 같은 변화는 같은 방식으로 움직여야 합니다.
  - 특정 데이터를 나타내던 표식을 다른 데이터에 다시 쓰지 않습니다.
  - 서로 다른 의미 변화가 같은 움직임으로 보이지 않게 합니다.
- **파악 용이성(Apprehension)**
  - 비슷한 변화는 묶어서 함께 움직입니다(공통 운명).
  - 대상끼리 가리지 않게 합니다.
  - 천천히 시작해 천천히 끝나는 가속으로 도착점을 예측할 수 있게 합니다.
  - 전환은 단순하게 만듭니다. 이동과 확대·축소는 회전보다 이해하기 쉽습니다.
  - 복잡한 전환은 여러 단계로 나눕니다.
  - 필요한 만큼만 길게 합니다. 선행 연구는 약 1초를 권하고, 움직임이 작으면 더 짧게 합니다.
- **시차 두기:** 정렬 애니메이션에서 겹침을 줄이려고 원소마다 시작 시점을 조금씩 늦췄습니다(4.1.2절).
- **결과:** 애니메이션 전환은 대상을 계속 따라가는 일과 값을 추정하는 일에서 그래프 인지를 크게 개선했습니다.

### Chevalier, Dragicevic, Franconeri, The Not-so-Staggering Effect of Staggered Animated Transitions on Visual Tracking (TVCG 2014)
초록·2차 · [HAL](https://hal.archives-ouvertes.fr/hal-01054408v1)

- 원소마다 시작 시점을 늦추는 시차는 대상을 따라가는 성능을 높이지 못했다고 보고됩니다.
- 시차 연출은 보기 좋으라고 넣는 것이지, 대상 추적을 돕는다고 기대하면 안 됩니다.

### Archambault, Purchase, Pinaud, Animation, Small Multiples, and the Effect of Mental Map Preservation in Dynamic Graphs (TVCG 2011)
초록 · [PubMed](https://pubmed.ncbi.nlm.nih.gov/20498503/)

- 작은 그림을 여러 장 나란히 보여 주는 방식(small multiples)이 전반적으로 더 빨랐습니다.
- 같은 시점에 추가된 노드·선을 찾는 과제에서는 애니메이션이 오류가 더 적었습니다.
- 위치를 유지하는 것(mental map 보존)은 두 방식 모두에서 영향이 작았습니다.
- 같은 저자들의 후속 연구에 따르면, 배치가 불안정하고 중요한 노드를 계속 강조할 수 없을 때는 애니메이션이 더 낫습니다. [Glasgow eprints](https://eprints.gla.ac.uk/108352)

### Bach, Pietriga, Fekete, GraphDiaries (TVCG 2014)
초록 · [DOI](https://doi.org/10.1109/TVCG.2013.254)

- 시점 사이의 변화를 단계별 애니메이션으로 강조합니다.
- 시간을 앞뒤로 자유롭게 오갈 수 있고, 차이 강조와 작은 그림 비교를 함께 제공합니다.
- 사용자 연구에서 기존 시간 탐색 방식보다 여러 과제에서 시간과 오류가 줄었습니다.

### Holten & van Wijk, A User Study on Visualizing Directed Edges in Graphs (CHI 2009) 및 확장 연구 (PacificVis 2011)
초록·2차 · [확장 연구 PDF](https://www.lri.fr/~isenberg/publications/papers/Holten_2011_AEP.pdf)

- 방향 표현 방식 가운데 끝이 가늘어지는 선(tapered)이 화살표보다 좋았습니다.
- 끝이 가늘어지는 선과 움직이는 선 사이에는 유의한 차이가 없었습니다.
- 움직이는 선은 방향을 알려 주는 정당한 수단입니다. 같은 역할을 정지 화면에서는 끝이 가늘어지는 선이 대신할 수 있습니다.

### Romat 외, Animated Edge Textures in Node-Link Diagrams (CHI 2018)
원문 확인(실험 부분) · [Microsoft Research](https://www.microsoft.com/en-us/research/?p=485655)

- **모델:** 선은 터널이고, 노드는 입자를 내보내는 발생원입니다. 움직임의 변수는 무늬(pattern), 빈도(frequency), 속도(speed) 세 가지입니다.
- **실험 설계:** 36명이 참여했고, 2·4·6가지 값으로 선을 묶는 과제를 했습니다.
  - 값 사이 간격은 예비 실험에서 구한 최소 식별 차이(0.13~0.26)보다 크게 잡았습니다. 속도는 0.7, 빈도는 0.5를 썼습니다.
  - 속도는 3.3~46.7 mm/s, 빈도는 0.3~2.3 Hz 범위였습니다.
- **결과**
  - 시간 제한 안에서 묶음 수를 대략 추정할 때는 속도(0.88)와 빈도(0.81)가 무늬(0.68)보다 나았습니다.
  - 시간 제한 없이 정확히 셀 때는 무늬(0.99)가 속도(0.93)와 빈도(0.88)보다 정확했고, 그래프가 커져도 유지되었습니다.
  - 빈도는 그래프가 클수록 정확도가 떨어졌습니다. 속도와 빈도 모두 높은 값끼리 헷갈렸습니다.
- **후속 연구(INTERACT 2019):** 입자의 밝기, 색, 폭은 체감 속도에 영향을 주지 않았습니다. 길이가 다르면 선끼리 속도를 비교하기 어려워졌습니다(초록). [요약 페이지](https://hugoromat.github.io/AnimatedParticles)

### Bartram, Ware, Calvert, Moticons (IJHCS 2003)
초록·2차 · [PDF](https://www.interruptions.net/literature/Bartram-IJHCS03.pdf)

- 단순한 움직임을 가진 아이콘은 특히 시야 주변부에서 색이나 모양보다 잘 눈에 띕니다.
- 그만큼 주의를 빼앗고, 움직임 종류에 따라 짜증을 유발합니다.

## 모션 디자인 체계

### Apple Human Interface Guidelines: Motion
원문 확인 · [원문](https://developer.apple.com/design/human-interface-guidelines/motion)

- "Add motion purposefully, supporting the experience without overshadowing it."
- 모션은 끌 수 있어야 하고, 중요한 정보를 전하는 유일한 수단이 되면 안 됩니다.
- 애니메이션이 끝날 때까지 사람을 기다리게 하지 않습니다.
- 피드백 애니메이션은 짧고 정확하게 만듭니다. 자주 쓰는 조작에는 모션을 추가하지 않습니다.
- visionOS 절에는 약 0.2 Hz 진동을 피하고 시야 가장자리의 움직임을 줄이라는 지침이 있습니다. 이 지침은 공간 컴퓨팅 맥락입니다.

### IBM Carbon: Motion
원문 확인 · [원문](https://carbondesignsystem.com/elements/motion/overview/)

- **생산적(productive) 모션:** 효율과 반응성을 전하고 눈에 덜 띕니다. 작업 중심 화면에 씁니다.
- **표현적(expressive) 모션:** 가끔 있는 중요한 순간에만 씁니다.
- **지속 시간**

  | 토큰 | 시간 | 용도 |
  | --- | --- | --- |
  | fast-01 | 70ms | 버튼·토글 |
  | fast-02 | 110ms | 페이드 |
  | moderate-01 | 150ms | 짧은 이동 |
  | moderate-02 | 240ms | 확장, 토스트 |
  | slow-01 | 400ms | 중요한 알림 |
  | slow-02 | 700ms | 배경 어둡게 하기 |

  이동 거리와 크기가 클수록 길게 합니다.
- **가속 곡선**
  - 생산적 standard: `cubic-bezier(0.2, 0, 0.38, 0.9)`
  - 표현적 standard: `cubic-bezier(0.4, 0.14, 0.3, 1)`
  - 처음부터 끝까지 보이는 대상에는 standard를, 화면에서 사라지는 대상에는 exit를 씁니다.

### Material Design 3: Motion
2차 · [Material motion customization(이전 판)](https://material.io/design/motion/customization.html)

- standard는 `cubic-bezier(0.2, 0, 0, 1)`, emphasized decelerate는 `(0.05, 0.7, 0.1, 1)`로 보고됩니다.
- 출처마다 지속 시간 값이 다르므로 공식 사양으로 다시 확인해야 합니다.

## 제품 사례(문서·공개 이슈 기준)

- **LangGraph Studio** · 2차 · [graph execution](https://docs.langchain.com/oss/python/langgraph/frontend/graph-execution)
  - 실행 중 현재 노드와 지나간 선을 보여 주고, 노드별 카드가 스트림을 받습니다.
  - 한 포럼 제안에 따르면, 스트림만으로는 지금 움직이는 선을 알 수 없습니다. [제안](https://forum.langchain.com/t/proposal-add-langgraph-writers-metadata-to-enable-edge-visualization-and-better-debugging/2432)
- **GitHub Actions 시각화 그래프** · 2차 · [문서](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-the-visualization-graph)
  - 실행 진행을 실시간 그래프로 보여 줍니다.
  - 작업 이름 왼쪽의 아이콘이 상태를, 선이 의존 관계를 나타냅니다.
  - 작업을 누르면 로그가 열립니다.
- **Apache Airflow** · 2차 · [상태 색 사용자화](https://airflow.apache.org/docs/apache-airflow/2.1.3/howto/customize-state-colors-ui.html), [PR #61854](https://go.mail-archive.com/commits@airflow.apache.org/msg490113.html)
  - 상태 색을 설정으로 바꿀 수 있습니다.
  - 묶인 작업의 하위 상태 비율을 구간 막대로 보여 주자는 제안이 있습니다. 병합 여부는 확인하지 못했습니다.
- **n8n 캔버스** · 2차(커뮤니티) · [베타 피드백](https://community.n8n.io/t/help-us-test-the-new-n8n-canvas-beta/60070)
  - 움직이는 선과 회전 표시가 길거나 오류 난 실행, 반복, 수동 중지에서 멈춘 채 남는다는 보고가 있습니다.
  - 실행하지 않는데 애니메이션이 보인다는 보고도 있습니다. [이슈](https://community.n8n.io/t/workflow-showing-execution-animation-when-not-running/278880)
- **Dagster** · 2차 · [changelog](https://docs.dagster.io/changelog?page=2)
  - 실행을 지웠는데도 자산 상태가 "Materializing"으로 남던 버그가 수정되었습니다.
  - n8n과 같은 교훈입니다. 실행 중 표시는 실제 기록과 함께 검증해야 합니다.

## 구현 기법

- **CSS Motion Path:** `offset-path`로 경로를 지정하고 `offset-distance`를 0%에서 100%로 움직입니다. 2024년 1월 이후 주요 브라우저에서 동작한다고 MDN에 나와 있습니다(2차). [MDN offset-path](https://developer.mozilla.org/docs/Web/CSS/offset-path)
  - 지금 쓰는 `stroke-dashoffset` 점과 달리, 점·무늬 요소를 실제 도형으로 경로 위에 놓을 수 있습니다.
  - SMIL `animateMotion`은 대안으로 거론되지만 권장되지 않는다는 해설이 있습니다.
- **FLIP:** 시작 위치를 기록하고, 배치를 바꾼 뒤, transform으로 원래 위치처럼 보이게 했다가 되돌리는 기법입니다(Paul Lewis, 2015, 2차). [GSAP Flip 문서](https://gsap.com/docs/v3/Plugins/Flip)
  - 기록이 바뀌어 카드 위치가 달라질 때, 같은 작업의 카드가 이어서 움직이게 할 수 있습니다.
- **View Transitions API:** `document.startViewTransition(콜백)`이 DOM을 바꾸기 전후 화면을 찍어 연결합니다. 지원하지 않는 브라우저는 애니메이션 없이 바로 갱신합니다(2차). [MDN](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API/Using)
  - SVG 내부 요소에 개별 이름을 붙여 전환할 수 있는지는 확인하지 못했습니다.
- **ELK Layered(elkjs)** · 2차 · [알고리즘 문서](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html)
  - Sugiyama 방식을 다섯 단계로 처리합니다: 순환 제거, 층 배정, 교차 최소화, 노드 배치, 선 경로.
  - 선 경로는 기본이 직각입니다.
  - 지금처럼 단계마다 열을 나누는 배치보다 교차와 겹침을 줄일 수 있습니다. 다만 외부 라이브러리를 페이지에 넣어야 하므로, CDN 없이 오프라인으로 동작하는 지금 조건과 충돌합니다.

## 대시보드 적용 후보

2026-11-11에 아래 표의 1~3번(바뀐 카드 전환, 새 결정·차단 강조, 선택한 작업의 선에만 무늬로 구분한 점 흐름)을 적용했습니다. 확인 내용은 [검증 기록](guided-execution.md)에 있습니다. 4~5번 일부(정지 화살표, 선택 이웃에만 흐름)도 함께 반영되었고, 기록 재생과 층별 직각 배치는 남아 있습니다.

근거 강도와 현재 규칙(상태는 기록에서만, 모션은 장식, 모션 끄기·동작 줄이기 우선)을 기준으로 정리했습니다. 구현은 별도 요청으로 진행합니다.

| 후보 | 근거 | 지금과 다른 점 | 주의 |
| --- | --- | --- | --- |
| 기록이 바뀐 카드만 짧게 전환: 상태 막대와 기호는 240ms(Carbon 생산적), 이동은 FLIP | Heer(일치성·단순 전환·약 1초 이하), Carbon | 지금은 통째로 다시 그려 무엇이 바뀌었는지 보이지 않음 | 같은 작업은 같은 카드로 유지. 위치 이동과 상태 변화는 단계로 나눔 |
| 새로 생긴 '결정 필요'·'차단' 항목에 한 번만 400ms 강조 | Bartram(주변부 움직임은 주의를 끎), Carbon 표현적(중요한 순간에만), Apple(자주 쓰는 것에는 모션 금지) | 지금은 사람의 할 일이 생겨도 움직임 신호가 없음 | 반복 깜빡임 금지. 기호·문구가 같은 정보를 함께 전함 |
| 흐르는 점은 방향 표시로만 쓰고, 모든 선에 같은 속도 유지 | Holten(움직이는 선은 방향 표시로 유효), Romat(속도·빈도는 값이 많거나 그래프가 크면 헷갈림) | 지금과 같음. 속도로 의미를 담지 않는다는 원칙을 명시 | 속도나 빈도로 실행량·진행률을 표현하지 않음 |
| 선 종류(의존 / AI 단계 / 선택 이웃)를 점의 무늬로 구분하고, 같은 구분을 점선·색 같은 정지 표시로도 반복 | Romat(무늬는 정확한 구분에 강함), Apple(모션이 유일한 정보면 안 됨) | 지금은 선 종류마다 색·점선만 다름 | 무늬는 2~3가지로 제한 |
| 점이 흐르는 주기를 조정하거나 선택된 이웃에만 흐르게 함 | Apple(진동·주변부 움직임 줄이기, 단 visionOS 맥락), Bartram(산만함) | 지금은 3.2초 주기(약 0.31 Hz)로 모든 선에서 계속 흐름 | 정지 상태에서도 방향은 화살표 등으로 보여야 함 |
| 기록 재생: `state.history`의 실제 전이를 순서대로 단계별 애니메이션과 차이 강조로 보여 줌 | GraphDiaries, Archambault(추가된 요소 찾기는 애니메이션이 정확) | 지금은 현재 상태만 보여 줌 | 기록된 순서와 시각만 사용. 재생 속도가 실제 걸린 시간을 뜻하지 않음을 화면 구조로 구분. 기록에 없는 사건은 만들지 않음 |
| 직각 선을 쓰는 층별 배치(ELK 방식) | ELK 문서 | 지금은 단계별 열 배치에 곡선 | 외부 라이브러리 또는 자체 구현이 필요하고 오프라인 조건을 지켜야 함 |
| 실행 중 표시의 '멈춘 애니메이션' 방지 | n8n·Dagster 사례 | 지금은 진행 상태가 기록에서 오므로 같은 위험은 작음 | 연결이 끊기면 진행 표시의 움직임도 멈추고 '연결 끊김'을 우선 표시 |
