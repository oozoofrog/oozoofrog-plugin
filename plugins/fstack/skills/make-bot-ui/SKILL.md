---
name: make-bot-ui
description: Build a UI whose server sends an authenticated webhook to wake a configured automation.
disable-model-invocation: true
---
# Build a webhook UI

Read [the host profile](../fstack/references/host.md). Identify the target routine, accepted payload, provider authentication and a secure credential channel. For a Cursor routine use the [provider setup](references/cursor-routine.md) and its request format. Other providers need an equivalent endpoint and documented request format. When the user supplies an existing webhook, reuse it. If the requested service cannot be reached or provisioned, identify the missing prerequisite.

Build the requested controls around the payload fields. Validate incoming actions at the server, send only allowed fields, and store the sender credential in the server's secret store. Use secure input. Never put the credential into browser code, URLs, chat or logs. Bind to the intended interface and require authorization for remote exposure. Use the provider's header and content type. Surface delivery failures in the UI.

Use a receiver fixture to verify the browser-to-server payload, method and authentication without disclosing the credential. Verify an actual wake only with an authorized target and report which part ran. For duplicate or retried events follow the provider's delivery and idempotency semantics.
