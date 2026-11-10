# 온톨로지 시각화 참고 자료

2026-11-10 공식 문서·소스에서 확인한 설계 자료입니다. 아래 서비스의 화면을 직접 조작해 평가했다는 뜻은 아닙니다. 라이브러리 코드·이미지·브랜드 자산을 복제하지 않고 표기·상호작용 원칙을 독자적인 CSS/SVG 구현에 적용했습니다.

## WebVOWL / VOWL: 의미가 다른 대상은 다르게 표시

- [공식 저장소](https://github.com/VisualDataWeb/WebVOWL)
- [VOWL 논문](https://www.semantic-web-journal.net/content/visualizing-ontologies-vowl-0)
- 적용: 작업·검증·결정·에이전트의 도형과 테두리를 구분하고 범례를 유지합니다. 상태 값은 색뿐 아니라 짧은 문자로도 표시합니다.
- 제외: 모든 작업을 동일한 원으로 만들거나 실제 기록에 없는 클래스·추론 관계를 추가하지 않습니다. 이 도구는 OWL 추론기나 온톨로지 편집기가 아닙니다.
- 주의: 공식 저장소는 예전 visualdataweb.org 도메인이 더 이상 프로젝트 소유가 아니라고 경고합니다. 공식 저장소가 가리키는 새 데모는 https://service.tib.eu/webvowl/ 입니다.

## Neo4j Bloom: 주변 관계에 집중

- [공식 개요](https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/bloom-overview/)
- 적용: 노드와 연결된 관계를 국소적으로 강조하여 큰 그래프의 방향을 읽기 쉽게 합니다. 상세 증거는 별도 접힌 영역에 유지합니다.
- 제외: DB 검색·여러 hop 질의·실시간 인스펙터 기능을 구현했다고 주장하지 않습니다.

## Observable D3 / Cytoscape: 맥락과 위치 보존

- [Temporal Force-Directed Graph](https://observablehq.github.io/notebook-kit/ex/d3/temporal-force-directed-graph)
- [Cytoscape layouts 설명](https://blog.js.cytoscape.org/2020/05/11/layouts/)
- 적용: 기존 노드의 좌표를 유지하고 짧은 진입 연출과 국소 강조로 관계를 드러냅니다. 지속적인 전체 재배치·흔들림을 피합니다.
- 제외: 이 보고서에는 실제 이벤트 스트림이 없으므로 시간 슬라이더·실시간 재생·가상의 상태 변화는 추가하지 않습니다.

## React Flow: 관계 방향을 보여주는 모션

- [Animated edges 예제](https://reactflow.dev/examples/edges/animating-edges)
- [접근성 안내](https://reactflow.dev/learn/advanced-use/accessibility)
- 적용: 정적인 기본 경로 위에 이동하는 장식 강조를 겹쳐 방향을 읽게 합니다. 마우스뿐 아니라 키보드로도 노드의 관계를 강조할 수 있게 하고, 장식은 의미 정보와 분리합니다.
- 제외: 선 위에서 빛이 움직인다는 이유로 작업이 실제 실행 중이라고 표시하지 않습니다. 상태 텍스트와 저장된 증거가 기준입니다.

## 모션 접근성 기준

- [W3C: Animation from Interactions](https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions)
- [W3C: Pause, Stop, Hide](https://www.w3.org/WAI/WCAG20/Understanding/pause-stop-hide.html)
- 적용: 명시적인 모션 끄기, 시스템 prefers-reduced-motion 우선, 정지해도 보이는 노드·상태·기본 경로, 명확한 초점 표시를 유지합니다.
- 이 지침과 정적 검사는 전체 WCAG 준수 인증이나 실제 보조기술 검증을 대신하지 않습니다.
