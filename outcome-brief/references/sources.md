# 확인한 출처와 적용 범위

확인일: **2026-10-21 UTC**. 조사팀 `/root/evidence`가 로컬 공식 자료를 읽고 다음 공식/일차 원문을 실제 확인했다. 이 스킬을 작성한 실행 환경은 Codex이며, 현재 세션의 실제 추론 모델 ID·계정별 이용 가능성·청구액은 관측하지 않았다. 아래는 사용자 성능 비교가 아니다.

- [OpenAI — Using GPT-6: Prompting best practices](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices): GPT-6 계열의 시작 권고, 관찰은 Astra 행동 기반. 선택 모델·작업으로 평가해야 하며 기존 지시를 일괄 폐기할 근거가 아니다.
- [OpenAI — Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices#how-to-prompt-reasoning-models-effectively): 추론 모델에서 직접적인 목표·제약과 간단한 지시를 권고. CoT 지시가 필요하지 않거나 방해될 수 있다는 범위이며 모든 모델·교육용 설명 요청에 대한 금지가 아니다.
- [OpenAI — Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices): 작업별 지표, 쌍대 비교와 사람 판단의 보정. 다중 에이전트 인계의 불확실성도 평가 대상으로 본다.
- [OpenAI — Best practices: Context and prompts](https://learn.chatgpt.com/guides/best-practices#strong-first-use-context-and-prompts): Codex의 목표·맥락·제약·완료 조건, 관련 검사와 스킬화 안내. 특정 향상률을 입증한 사용자 실험은 아니다.
- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/research/multi-agent-research-system): 2025-06-13 공식 구현 사례. Opus 4/Sonnet 4의 내부 연구 평가이며 독립 조사 적합성·토큰 및 인계 비용을 설명한다. Codex나 이 사용자 결과로 일반화하지 않는다.
- [Wei et al. — Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/html/2201.11903v6): NeurIPS 2022 일차 연구(v6 2023-01-10). 당시 GPT-3·LaMDA·PaLM 등과 few-shot 추론 과제의 결과이며 현재 내부 추론 모델의 비공개 생각 공개 요구를 뒷받침하지 않는다.
- [OpenAI — Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization): 출력량·요청 수·병렬화 등 여러 요인을 다룬다. 입력 글자 수 감소와 사용자 지연/금액 절감이 같은 비율이라는 근거가 아니다.

설계 해석: 결과·제약·완료 기준을 선명히 하되, 절차·문서·페르소나·검증량은 실제 과제에 필요한 만큼 적용한다. 팀 수가 많을수록 좋다는 결론을 채택하지 않는다. 이 사용자의 전역 리더+팀 규칙은 유지하며 분할·반복 정도를 그 안에서 조정한다. 관측 전에는 정확도·품질·시간·비용 향상을 주장하지 않는다.
