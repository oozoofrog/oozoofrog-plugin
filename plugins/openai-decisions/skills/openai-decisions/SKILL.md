---
name: openai-decisions
description: Call the OpenAI Decisions API directly to classify text, JSON, or images, estimate predicate probabilities, or score against an ordered rubric. Use for explicit Decisions API requests or bounded semantic judgments that benefit from measured probabilities; not for general chat or free-form extraction.
---

# OpenAI Decisions

Run the bundled `scripts/openai-decisions` (path relative to this skill's directory; in Claude Code `${CLAUDE_SKILL_DIR}/scripts/openai-decisions`) or `openai-decisions` on `PATH` (also check `~/.local/bin/openai-decisions`). Both Codex and Claude Code use the same command. It needs `python3` and the official OpenAI CLI 1.51.2 or later, converts the request below into `openai decisions create --format json`, and prints the CLI's JSON response unchanged. `gpt-6-luna` is the supported Decisions model. API usage is billed separately from the conversation's subscription.

This is a skills-only Plugin: it registers no MCP server or tool. If the command cannot run, read [CLI setup and direct requests](references/cli.md) and call the official OpenAI CLI directly. Keep existing credential configuration.

## Calling

- `state`: explicit text, a JSON object, or a JSON array. Arrays are wrapped as `{"items": [...]}`; arrays never become conversation instructions.
- `questions`: 1–400 independent questions with unique `name`, `type`, and `instructions`. Batch questions about the same evidence. Use separate calls when later questions depend on earlier answers.
- `predicate`: estimates whether the stated condition holds.
- `choice`: add 2–255 `choices`, each with a unique string/boolean `value` and optional `description`; include an unknown/other option when needed.
- `score`: add 2–10 `levels`, ordered low to high, with `label` and optional `description`. Scores are probability-weighted zero-based indices, not arbitrary 1–10 ratings.
- Optional `image_urls`: public HTTP(S) image URLs or base64 data URLs. Local files go through repeated `--image /absolute/path.png` (PNG, JPEG, GIF, WebP).
- Optional `timeout_seconds`: 1–300, default 60. A timed-out request is not retried by the wrapper, because the first call may already have incurred usage. The official CLI itself may retry transient errors (HTTP 408, 429, 5xx) within one invocation and offers no option to turn that off. Request size limit is 8 MiB.
- Optional `prompt_cache_key`, `prompt_cache_options`, and `safety_identifier` are passed to the CLI unchanged.
- A native request (`model`, `input`, `questions`) is also accepted and passed through.

CLI example (the heredoc contains evidence, never credentials):

```sh
openai-decisions create <<'JSON'
{"state":"결제가 두 번 됐습니다. 환불해주세요.","questions":[{"type":"predicate","name":"refund","instructions":"고객이 환불을 요청하는가?"}]}
JSON
```

For a prepared request use `openai-decisions create --input /absolute/request.json`; add `--image /absolute/image.png` for image evidence. Invalid questions fail before any API call. Only supplied evidence is sent to OpenAI: no automatic session-history or screen collection.

## Credentials and failures

To save the key, run `jev-client key set openai` (hidden prompt, `--pasteboard`, or `--file` from a T3 `request_secret` file) from the `jev-client` Plugin; it writes Keychain `local.openai-decisions`/`openai`.

`openai-decisions status` reports the CLI path and version and which credential source is available (name only) without an API call. It does not establish API access or billing status.

Credential order: `OPENAI_API_KEY`, macOS Keychain service `local.openai-decisions` / account `openai`, then the existing `com.kakao.mac-cu.decisions` / `openai` entry. Keychain is read with `security find-generic-password`; mac-cu need not run. The key reaches the OpenAI CLI only through its process environment. Keychain credentials are restricted to `https://api.openai.com/v1`: when `OPENAI_API_KEY` is unset and `OPENAI_BASE_URL` names another origin, the command fails before reading Keychain. Never print keys, put them in tool arguments, or copy them into config/skill files. If missing, use T3 `request_secret` for private delivery when available, or the host's secret-input facility. An existing mac-cu Decisions settings window can save the shared Keychain key. Do not ask for a key in chat. ChatGPT/Codex login tokens are not API keys.

Return the actual answers and usage. A refusal remains a refusal; a nonzero exit is a failure, not a negative judgment. Probabilities/confidence are estimates, not accuracy guarantees or permission to perform an action. Do not replace the API with the conversation model silently. Calibrate thresholds on labeled examples when building automation.

Sources: [Decisions guide](https://developers.openai.com/api/docs/guides/decisions), [API reference](https://developers.openai.com/api/reference/resources/decisions/methods/create).
