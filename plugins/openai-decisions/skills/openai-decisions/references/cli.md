# CLI setup and direct requests

This Plugin carries instructions, not the personal MCP/CLI runtime. Use an already registered `openai_decide` tool first. For the shared wrapper, check `command -v openai-decisions` and `~/.local/bin/openai-decisions`; run its `status` command before diagnosing credentials. Existing tool registrations do not need to move when the skill moves.

## Official CLI fallback

When the wrapper is absent, use the official OpenAI CLI with `openai decisions create --format json`. The native request uses `input`, not the wrapper's `state`. Verify `openai --version`; version 1.51.2 or later is the input-handling contract verified for this workflow. The legacy Python SDK's `openai` executable is a different CLI.

On macOS the official installation command is `brew install --cask openai/tools/openai`. Install only when the requested task needs it and the current permissions allow it. Other platforms should follow the [official CLI documentation](https://developers.openai.com/api/reference/cli/).

The direct CLI requires `OPENAI_API_KEY` from the host's secret manager or private secret-input mechanism. It does not use Codex subscription login. Unlike the shared wrapper, this fallback does not automatically look up `local.openai-decisions` or `com.kakao.mac-cu.decisions` in Keychain. Never print or put the key in command arguments, source files, or chat. For stored keys, keep the API origin at `https://api.openai.com/v1`; do not forward a stored credential to a custom `OPENAI_BASE_URL`.

Example with explicit nonsecret evidence and an API key already injected into the process environment:

```sh
OPENAI_UNTRUSTED_STDIN=1 OPENAI_CLI_NO_UPDATE_CHECK=1 OPENAI_CLI_NO_AUTO_UPDATE=1 openai decisions create --format json <<'JSON'
{"model":"gpt-6-luna","input":"결제가 두 번 됐습니다. 환불해주세요.","questions":[{"type":"predicate","name":"refund","instructions":"고객이 환불을 요청하는가?"}]}
JSON
```

Keep `OPENAI_UNTRUSTED_STDIN=1`: untrusted `@file://` or `@data://` evidence must not expand into local file reads. Use stdin for the request, not interpolated shell arguments. Do not automatically retry a timed-out request; the first call may already have incurred usage.

For JSON evidence, native `input` is `[{"role":"user","content":[{"type":"input_json","data":{"ticket":"..."}}]}]`. Wrap a primitive array as an object, for example `{"items":[1,true]}`. For images, add `{"type":"input_image","image_url":"https://..."}` or a base64 data URL to the user's content. Send only images explicitly selected for the task. Native requests do not use `image_urls`, `state`, or `timeout_seconds`; those are wrapper parameters.

Use the same question shapes described in [the skill](../SKILL.md). Keep native answers, refusals, and usage; check answer names/types and finite probabilities in 0–1 before using a result. Do not infer a negative answer from a CLI failure or fabricate probabilities. The standalone wrapper performs more extensive response validation than this raw CLI fallback.

Sources: [Decisions guide](https://developers.openai.com/api/docs/guides/decisions), [CLI Decisions reference](https://developers.openai.com/api/reference/cli/resources/decisions).
