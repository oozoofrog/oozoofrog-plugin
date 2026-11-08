# Mac Computer Use for Claude Code and Codex

Let Claude Code or Codex use the apps on your Mac, in the background.

> "Use Calculator to work out 12 × 12."
> "Open Notes and find my packing list."

The agent reads and operates the app for you while you keep working in another window. It uses the
macOS accessibility API through `mac-cu`, an MCP server in this folder. For web pages it also runs
JavaScript in a tab: in your own browser through Apple Events, in your own Chrome through the mac-cu
Chrome extension (as Claude in Chrome does: your logins, real clicks and keys, network requests), or in a
separate Chrome through the Chrome DevTools Protocol. No other app is needed.

It also reads the screen of a booted iOS Simulator as an accessibility tree (role, label, id, value,
center), waits for an element and taps it by its label or id, and taps, swipes and types (Xcode 27 or
later) with HID events: Korean too, as two-set keys or by paste. No other tool (AXe, idb) is needed.

It inspects WKWebView and Safari pages of booted simulators and USB iPhones through their Web Inspector,
without Safari: JavaScript, console, network (with the cache source), cookies and a picture of the page.

This folder started as a copy of
[BrickleRex/codex-computer-use-skill](https://github.com/BrickleRex/codex-computer-use-skill)
(commit 869f727), which connected the ChatGPT app's Computer Use. It now has its own server.

## What you need

- **A Mac** with the Xcode command line tools (`xcode-select --install`), for `swiftc`
- **Claude Code** or **Codex** (the `codex` CLI, or the ChatGPT app that includes it)
- **Accessibility permission** for mac-cu.app, the menu bar app that does the work (System Settings >
  Privacy & Security > Accessibility), Screen Recording for screenshots and the window preview, and
  Automation for the browser tool with your own browser (macOS asks the first time). You allow mac-cu
  once, whichever app runs the agent. When Accessibility or Screen Recording is missing, mac-cu opens
  its page with a panel that shows its icon to drag into the list; the menu bar menu and
  `scripts/setup.py --permissions` show these guides again.
- An **Apple Development** signing identity (every iOS developer has one) keeps the permissions over
  plugin updates. Without one, the app is signed ad-hoc and macOS forgets the Accessibility permission
  at each update: turn mac-cu on again in the list.
- For JavaScript in your own browser: "Allow JavaScript from Apple Events" (Chrome: View >
  Developer; Safari: Develop menu), or the mac-cu Chrome extension (see Install, step 4)

## Install

1. Install the plugin: `claude plugin install mac-computer-use@oozoofrog-plugin` (Claude Code) or
   `codex plugin add mac-computer-use@oozoofrog-plugin` (Codex).
2. Ask the agent to "set up mac-cu". It runs `scripts/setup.py --agent claude` or
   `scripts/setup.py --agent codex` from the installed plugin folder. The script builds
   `~/Library/Application Support/mac-cu/mac-cu.app`, registers it and starts it: a menu bar icon
   shows the version, the sessions and what they do, the permissions, the modes, manual update guidance,
   and Quit.
3. Restart the agent: close and reopen Claude Code, or start a new Codex chat.
4. Optional, for your own Chrome with the extension engine: in Chrome, open chrome://extensions, turn
   on Developer mode, choose Load unpacked, and select
   `~/Library/Application Support/mac-cu/chrome-extension` (step 2 copies it there and registers its
   native messaging host). `Library` is hidden: in the folder dialog press cmd+shift+G and paste the
   path. If mac-cu is not in the list at chrome://extensions, it was never loaded: do this step.
   After a plugin update, step 2 copies it again: click the reload button of mac-cu in
   chrome://extensions, then restart the agent so it runs the new mac-cu too.

The glow and preview of the target window use Claude Code hooks. Codex has no glow.

Modes: ask the agent, or run `scripts/mac-cu --mode` yourself. `input=auto|background|foreground` sets
whether actions may bring the app to the front; `show=glow|steps|off` sets what the window shows
(`steps` adds the goal and the current step). The modes are kept in
`~/Library/Application Support/mac-cu/modes.json`.

The setup registers mac-cu by its path in `~/Library/Application Support/mac-cu`, which does not change
with the plugin version. After a plugin update, run the setup again (after updating the selected Plugin through its host): it rebuilds the app from the new version and restarts it. The next
call also replaces a running older app by itself. The devtools Chrome profile (`browser-profile`), the
modes and the apps allowed with Always Allow live in the same folder and stay over updates.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| The agent says it has no mac-cu tools | Run the setup again (step 2 above), then restart the agent. |
| "mac-cu could not reach its daemon" | The app is missing or does not start. Run the setup again; to see the error, open `~/Library/Application Support/mac-cu/mac-cu.app` yourself. |
| "The accessibility API is not allowed" | mac-cu (and `setup.py`) opens Privacy & Security > Accessibility with a panel below it: drag the mac-cu icon in the panel into the list (or turn mac-cu on), then try again. If it is still not allowed, quit mac-cu in the menu bar and try again. |
| The permission is on in the list but mac-cu says it is not | The app was signed ad-hoc (no Apple Development identity) and rebuilt: turn mac-cu off and on in the list. |
| There is no glow around the window (Claude Code) | Run the setup again. |
| "The mac-cu extension host refused …" | The native host that Chrome runs is an older or different mac-cu than the one the agent runs (the host answers only the same mac-cu program). If the message allows the newer folder, the agent still runs the old mac-cu: restart the agent. Otherwise run the setup again, reload mac-cu in chrome://extensions so Chrome starts the host from the new folder, and restart the agent. |
| You do not want to be asked about an app | Choose **Always Allow** in the dialog: mac-cu adds the app to `~/Library/Application Support/mac-cu/always-allow.txt` (kept after a plugin update). You can also edit that file, one app name or bundle ID per line. |

To remove everything: run `scripts/setup.py --uninstall` from the plugin folder, then uninstall the
plugin.

## What's inside

- `SKILL.md`: the instructions the agent follows
- `scripts/mac-cu-src/`: the MCP server (tools `get_app_state`, `act`, `browser`, `simulator`, `webinspector` and `decide`), and the
  native messaging host of the Chrome extension (the same program; it answers only mac-cu itself, and the
  extension runs only the protocol commands the browser tool needs)
- `chrome-extension/`: the mac-cu Chrome extension (the browser tool with `"engine": "extension"`)
- `verify-prompts.md`: the prompts for `act` verify and `decide`
- `scripts/setup.py`: builds and signs mac-cu.app, connects it to Claude Code and/or Codex, and restarts it
- `scripts/focus.py`, `scripts/focus-overlay.swift`: the glow and preview of the target window

## License

MIT

The simulator LCD window uses an opaque device body without a title bar. Drag its device/status capsule to move it; its menu provides focus mode, size, minimize and close. Home, rotation, folding and capture sit below the LCD, with auxiliary controls at the side. See [device window controls](references/device-window.md).

The menu bar Settings connection check displays the actual synthetic request body and validated response, including elapsed time and failures. It uses saved settings and excludes API keys and authentication headers from its read-only reports.
