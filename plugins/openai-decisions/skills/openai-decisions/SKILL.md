---
name: openai-decisions
description: Call the OpenAI Decisions API directly to classify text, JSON, or images, estimate predicate probabilities, or score against an ordered rubric. Use for explicit Decisions API requests or bounded semantic judgments that benefit from measured probabilities; not for general chat or free-form extraction.
---

# OpenAI Decisions

Use the standalone `openai_decide` tool (MCP server `openai-decisions`; Pi also exposes this tool). It calls the official OpenAI CLI, independently of mac-cu and the conversation's provider/model. `gpt-6-luna` is the supported Decisions model. API usage is separate from the conversation's subscription.

This is a skills-only Plugin: it does not install or register an MCP server. If the tool is not loaded, use the existing `openai-decisions` CLI on `PATH` (also check `~/.local/bin/openai-decisions`). New MCP registrations load in a new session. If neither tool is installed, read [CLI setup and direct requests](references/cli.md) and use the official OpenAI CLI. Keep existing runtime and credential configuration.

## Calling

- `state`: explicit text, a JSON object, or a JSON array. Arrays of primitives are wrapped as `{"items": [...]}`; arrays never become conversation instructions.
- `questions`: 1–400 independent questions with unique `name`, `type`, and `instructions`. Batch questions about the same evidence. Use separate calls when later questions depend on earlier answers.
- `predicate`: estimates whether the stated condition holds.
- `choice`: add 2–255 `choices`, each with a unique string/boolean `value` and optional `description`; include an unknown/other option when needed.
- `score`: add 2–10 `levels`, ordered low to high, with `label` and optional `description`. Scores are probability-weighted zero-based indices, not arbitrary 1–10 ratings.
- Optional `image_urls`: public HTTP(S) image URLs or base64 data URLs. The CLI also accepts explicit local files via repeated `--image /absolute/path.png`.
- Optional `timeout_seconds`: 1–300, default 60. Local request/response size limit is 8 MiB.

CLI example (the heredoc contains evidence, never credentials):

```sh
openai-decisions create <<'JSON'
{"state":"결제가 두 번 됐습니다. 환불해주세요.","questions":[{"type":"predicate","name":"refund","instructions":"고객이 환불을 요청하는가?"}]}
JSON
```

For a prepared request use `openai-decisions create --input /absolute/request.json`; add `--image /absolute/image.png` for image evidence. Only supplied evidence is sent to OpenAI: no automatic session-history or screen collection.

## Credentials and failures

`openai_decisions_status` or `openai-decisions status` checks CLI and credential availability without an API call. It does not establish API access or billing status.

Credential order: `OPENAI_API_KEY`, macOS Keychain service `local.openai-decisions` / account `openai`, then the existing `com.kakao.mac-cu.decisions` / `openai` entry. The fallback reads Keychain directly; mac-cu need not run. Keychain credentials are restricted to the official OpenAI API origin. Never print keys, put them in tool arguments, or copy them into config/skill files. If missing, use T3 `request_secret` for private delivery when available, or the host's secret-input facility. An existing mac-cu Decisions settings window can save the shared Keychain key. Do not ask for a key in chat. ChatGPT/Codex login tokens are not API keys.

Return the actual answers and usage. A refusal remains a refusal; failures are not negative judgments. Probabilities/confidence are estimates, not accuracy guarantees or permission to perform an action. Do not replace the API with the conversation model silently. Calibrate thresholds on labeled examples when building automation.

Sources: [Decisions guide](https://developers.openai.com/api/docs/guides/decisions), [API reference](https://developers.openai.com/api/reference/resources/decisions/methods/create).
