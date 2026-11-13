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

Send a System One request as JSON on stdin or with `--input FILE`:

```sh
jev-client ask <<'JSON'
{"model":"jev-latest","state":"I was charged twice this month. Please refund it.",
 "questions":{
  "refund":{"type":"noul","instructions":"Is the customer asking for a refund?"},
  "tone":{"type":"choice","instructions":"What is the tone?","criteria":{"angry":"Upset or hostile","calm":"Neutral or polite"}},
  "urgency":{"type":"score","instructions":"How urgent is it?","criteria":["Can wait","This week","Today"]}}}
JSON
```

`noul` returns the probability of yes, `choice` one option with per-option probabilities and confidence, `score` a probability-weighted position on the ordered levels. Ask independent questions about the same state in one request. The response JSON is printed unchanged; an HTTP error exits 1 with the API's message, with the key redacted. Requests are not retried automatically; `--timeout` is 1-300 seconds (default 60).

For question design, models and limits, read the live docs: [index](https://docs.typesafe.ai/llms.txt), [System One API](https://docs.typesafe.ai/api/system-one.md), [primitives](https://docs.typesafe.ai/primitives.md). Probabilities and confidence are estimates, not permission to act; a failed call is not a negative answer.
