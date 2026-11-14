---
name: jev-client
description: Call TypeSafe Jev (System One API) from the Swift jev-client command and register TypeSafe or OpenAI API keys in the macOS Keychain. Use for explicit Jev or TypeSafe requests: typed yes/no, choice or score judgments with probabilities, listing models, or checking and saving API keys.
---

# Jev Client

Use the `jev-client` command (`~/.local/bin/jev-client`). Codex and Claude Code run it the same way from the shell. If it is missing, build and install it from this repository with `tools/jev-client/Scripts/install.sh` (Swift 6, macOS 14+; build cache under `/Volumes/eyedisk/build/jev-client`).

## Keys

Order for the TypeSafe key: `TYPESAFE_API_KEY`, Keychain `local.jev-client`/`typesafe`, then the legacy `~/.typesafeai` file. `jev-client status` shows which source is used without a network call. `jev-client models` sends one request and is the real key check.

To save a key, never ask for it in chat, a command argument, or a log:

- In T3 Code, call `request_secret` with `delivery: "file"`, then run `jev-client key set typesafe --file "<file>"` (or `openai`).
- In a terminal the user runs `jev-client key set typesafe` (hidden prompt) or copies the key and runs `jev-client key set typesafe --pasteboard`.
- `jev-client key import-legacy` copies `~/.typesafeai` into Keychain and keeps the file for other tools.

`jev-client key set openai` stores the OpenAI key in Keychain `local.openai-decisions`/`openai`, where the `openai-decisions` command reads it first. Keys are written through `security -i` on stdin, so they never appear in a process list. `key status` and `key delete` manage both entries.

## Asking Jev

Send a System One request as JSON on stdin or with `--input FILE`. `model` is required (`jev-latest`, or a pinned ID from `jev-client models`):

```sh
jev-client ask <<'JSON'
{"model":"jev-latest","state":"I was charged twice this month. Please refund it.",
 "questions":{
  "refund":{"type":"noul","instructions":"Is the customer asking for a refund?"},
  "tone":{"type":"choice","instructions":"What is the tone?","criteria":{"angry":"Upset or hostile","calm":"Neutral or polite"}},
  "urgency":{"type":"score","instructions":"How urgent is it?","criteria":["Can wait","This week","Today"]}}}
JSON
```

`noul` returns the probability of yes, `choice` one option with per-option probabilities and confidence, `score` a probability-weighted position on the ordered levels. Ask independent questions about the same state in one request. The response JSON is printed unchanged; an HTTP error exits 1 with the API's message, with the key redacted. Requests are not retried automatically; `--timeout` is 1-300 seconds (default 60). Add `--long-context` when the request exceeds 64k tokens of context.

## Calling from other skills, scripts and hooks

`jev-client` and `openai-decisions` follow one contract, so a caller can use either without host-specific code. Both install to `~/.local/bin` with `tools/jev-client/Scripts/install.sh`.

- Request JSON on stdin, result JSON on stdout, diagnostics on stderr.
- Exit codes: `0` success; `2` bad arguments or request, nothing sent; `3` not ready (no key), nothing sent; `4` the API call failed or timed out and may have been billed. Codes 2-4 are failures, never a "no" answer.
- `jev-client status` makes no network call, prints `"ready"` and `"contract": 1`, and exits `3` when not ready. Treat the tool as optional: check it, and fall back to your own handling when it is missing.
- `jev-client ask --summary` prints the same shape from both tools instead of the raw response:

```json
{"contract":1,"provider":"jev","model":"...","complete":true,"usage":{"input_tokens":296},
 "answers":[{"name":"refund","type":"yesno","probability":0.98},
            {"name":"tone","type":"choice","answer":"angry","probability":0.8},
            {"name":"urgency","type":"score","answer":1.7}]}
```

`probability` is the probability of yes for `yesno` and of the selected option for `choice`; `score` is the zero-based position on the ordered levels. Answers are listed in name order; a type the summary does not cover (for example `box`) is `unknown`. `complete` is false when any answer is not a usable `yesno`, `choice` or `score`. Confidence is left out because the two providers compute it differently; read the raw response when you need it. Thresholds and what to do with an answer belong to the caller.

```sh
jev-client status >/dev/null 2>&1 || exit 0   # optional dependency: skip when not ready
p=$(jev-client ask --summary --input "$request" | jq -r '.answers[] | select(.name=="refund").probability') || exit 0
```

For question design, models and limits, read the live docs: [index](https://docs.typesafe.ai/llms.txt), [System One API](https://docs.typesafe.ai/api/system-one.md), [primitives](https://docs.typesafe.ai/primitives.md). Probabilities and confidence are estimates, not permission to act; a failed call is not a negative answer.
