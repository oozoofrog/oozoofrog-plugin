---
name: fstack
description: "Use fstack for development requests in plain Korean or English: explain code, refine an idea, compare designs, assess measurements, review changes, implement or verify a fix. 개발 저장소에서 코드 설명, 요청문 다듬기, 사용법 안내, 변경 검토와 구현 검증에 사용한다. “둘 중 뭐가 나아요?”, “이걸로 빨라졌다고 할 수 있어요?”처럼 짧은 구현 비교나 측정 질문도 포함한다."
---

# fstack

Start with the result the user wants. Resolve references such as “이 결과” or “이 변경” from the conversation and matching workspace artifacts before asking for more input. Use the current **project directory** for task evidence. Resolve workflow instructions relative to this installed skill. Use the user's language. Once fstack is active, the user supplies the outcome in Korean or English.

**When the deliverable is a prompt** (for example, “뭐라고 부탁하면 돼?” or “요청문만 주세요”): identify the *work the next agent will do* in the [specialist index](../poteto-help/SKILL.md). Read the corresponding method and put its verification step in the request. Write directly to the next agent in the language of the request. If the user asks for the prompt alone, start with its first instruction and stop at its last instruction. Leave out skill names, introductions and usage tips. The next agent executes the work.

A state diagram plus a shortest violation path calls for [model checking](../statechart/SKILL.md). In Korean, a ready-to-send request for this result is:

> 상태 전이를 모델로 만들고 도달 가능한 상태를 검사해 주세요. 팀원이 이해할 수 있는 말로 상태 전이 그림을 그려 주세요. 규칙을 위반하는 상태마다 시작점에서 가장 짧은 사건 순서를 보여 주세요. 코드가 있으면 그 순서를 재현하고 결과를 함께 적어 주세요.

| Requested result | What to do |
| --- | --- |
| Understand code, a choice or an unfamiliar idea | Read the relevant source. Use [how](../how/SKILL.md) for behavior, [why](../why/SKILL.md) for rationale, and [reframe](../reframe/SKILL.md) when the user wants expert terminology or alternative problem definitions. |
| Deepen or rewrite a task description | Use [sharpen](../sharpen/SKILL.md) when the user wants a deeper task. Use [reframe](../reframe/SKILL.md) first when they also want alternative problem definitions or domain terminology. |
| Compare strengths or simplify a workflow | Use the project’s notes or source to establish what each option provides. If the question concerns fstack itself, its [package documentation](../../README.md) records its upstream version and adaptations. Show how both methods contribute to one outcome in a single fstack session. For a usability goal, lead with one request the user can say and what they get back. Discuss installation, removal or migration only when the user asks how to manage an installation. Implement when the request calls for a change. |
| Choose between runnable implementations, or judge a measurement | When the question names a source file, inspect its implementation to identify what the two alternatives actually do. For a runnable choice, open the [prototype playbook](../poteto-mode/playbooks/prototype.md), execute each option on equivalent input and use the observed results for the recommendation. If the comparison cannot run here, say which evidence is missing. For an existing result, inspect its inputs and conditions with the [benchmark checklist](../benchmark-checklist/SKILL.md). |
| Review, fix or build | For a review, inspect the diff and report verified findings. Use [blast-radius](../blast-radius/SKILL.md) when the question is what else might break. For an implementation request, use the matching [engineering playbook](../poteto-mode/SKILL.md) and verify the requested behavior. |

For other outcomes, consult the [specialist index](../poteto-help/SKILL.md) and the [playbook list](../poteto-mode/SKILL.md#playbooks). Open the matching instructions inside **this installation** and apply them. The index is for the agent to select methods. Give the user the requested artifact, even when it takes several methods. Honor explicit skill names and model choices. For help with fstack itself, give an immediately usable example starting with the user's goal. Model setup is optional.

Read [the host profile](references/host.md) for host operations. Follow project and user instructions for delegation, external actions and verification. Report missing capabilities when they affect the result. If a project wiki or journal exists, follow [records](references/records.md) before an authorized commit. For projects with numbered acceptance criteria, [trace.py](scripts/trace.py) checks their links to plans and test names.
