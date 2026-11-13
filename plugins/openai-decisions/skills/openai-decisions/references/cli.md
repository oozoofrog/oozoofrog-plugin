# CLI setup and direct requests

The skill ships `scripts/openai-decisions`, a dependency-free Python 3 wrapper over the official OpenAI CLI. Use it directly from the skill directory, or link it onto `PATH`, for example `ln -s <skill-dir>/scripts/openai-decisions ~/.local/bin/openai-decisions`. Run `openai-decisions status` before diagnosing credentials. For tests only, `OPENAI_DECISIONS_OPENAI_BIN` selects a different `openai` executable and `OPENAI_DECISIONS_SECURITY_BIN` replaces `/usr/bin/security`, the program that reads the Keychain key. Do not set `OPENAI_DECISIONS_SECURITY_BIN` outside tests: whatever it names receives the Keychain lookup and returns the key that is sent to OpenAI.

## Official CLI fallback

When the wrapper cannot run (for example, no `python3`), use the official OpenAI CLI with `openai decisions create --format json`. The native request uses `input`, not the wrapper's `state`. Verify `openai --version`; version 1.51.2 or later is the input-handling contract verified for this workflow. The legacy Python SDK's `openai` executable is a different CLI.

On macOS the official installation command is `brew install --cask openai/tools/openai`. Install only when the requested task needs it and the current permissions allow it. Other platforms should follow the [official CLI documentation](https://developers.openai.com/api/reference/cli/).

The direct CLI requires `OPENAI_API_KEY` from the host's secret manager or private secret-input mechanism. It does not use Codex subscription login. Unlike the bundled wrapper, this fallback does not automatically look up `local.openai-decisions` or `com.kakao.mac-cu.decisions` in Keychain. Never print or put the key in command arguments, source files, or chat. For stored keys, keep the API origin at `https://api.openai.com/v1`; do not forward a stored credential to a custom `OPENAI_BASE_URL`.

Example with explicit nonsecret evidence and an API key already injected into the process environment:

```sh
OPENAI_UNTRUSTED_STDIN=1 OPENAI_CLI_NO_UPDATE_CHECK=1 OPENAI_CLI_NO_AUTO_UPDATE=1 openai decisions create --format json <<'JSON'
{"model":"gpt-6-luna","input":"결제가 두 번 됐습니다. 환불해주세요.","questions":[{"type":"predicate","name":"refund","instructions":"고객이 환불을 요청하는가?"}]}
JSON
```

Keep `OPENAI_UNTRUSTED_STDIN=1`: untrusted `@file://` or `@data://` evidence must not expand into local file reads. Use stdin for the request, not interpolated shell arguments. Do not automatically retry a timed-out request; the first call may already have incurred usage. The official CLI (1.51.2) may itself retry transient errors (HTTP 408, 429, 5xx) within one invocation and has no flag or environment variable to disable that, so one `create` can send more than one request. The wrapper redacts the API key from CLI output and errors.

For JSON evidence, native `input` is `[{"role":"user","content":[{"type":"input_json","data":{"ticket":"..."}}]}]`. Wrap a primitive array as an object, for example `{"items":[1,true]}`. For images, add `{"type":"input_image","image_url":"https://..."}` or a base64 data URL to the user's content. Send only images explicitly selected for the task. Native requests do not use `image_urls`, `state`, or `timeout_seconds`; those are wrapper parameters.

Use the same question shapes described in [the skill](../SKILL.md). Keep native answers, refusals, and usage; check answer names/types and finite probabilities in 0–1 before using a result. Do not infer a negative answer from a CLI failure or fabricate probabilities. The bundled wrapper validates questions before the call and passes the CLI response through unchanged, so check the response the same way.

Sources: [Decisions guide](https://developers.openai.com/api/docs/guides/decisions), [CLI Decisions reference](https://developers.openai.com/api/reference/cli/resources/decisions).
