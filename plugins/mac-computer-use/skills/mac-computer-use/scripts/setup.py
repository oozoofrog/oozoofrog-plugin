#!/usr/bin/env python3
"""
setup.py: connect mac-cu (scripts/mac-cu-src) to Claude Code and/or Codex.

This script:
  1. builds ~/Library/Application Support/mac-cu/mac-cu.app (the menu bar daemon and the MCP stdio
     client, one program from scripts/mac-cu-src) with swiftc, signs it with your "Apple Development"
     identity when you have one (ad-hoc otherwise), and builds scripts/focus-overlay (the focus glow);
  2. registers the app's program as a user-wide MCP server named "mac-cu" in each selected agent
     (`claude mcp`, `codex mcp`); the path does not change with the plugin version;
  3. copies the mac-cu Chrome extension (chrome-extension/) to ~/Library/Application Support/mac-cu and
     registers mac-cu as its native messaging host in Chrome (the browser tool with engine "extension");
  4. Claude Code only: adds the focus glow hooks (scripts/focus.py) to ~/.claude/settings.json (a
     backup is saved first), and removes what older versions of this skill added: the MCP server
     "codex-cu" (the ChatGPT app's Computer Use) and its approval and turn_ended hooks;
  5. quits the running daemon (an older build) and starts the new one, which asks macOS for the
     Accessibility and Screen Recording permissions of mac-cu.app itself.

Run it again after a plugin update: it rebuilds the app and restarts the daemon.

Usage:
    python3 setup.py                  # every agent whose CLI is found
    python3 setup.py --agent codex    # only Codex (repeat --agent for more)
    python3 setup.py --dry-run        # show what would change, change nothing
    python3 setup.py --uninstall      # remove the server (and the Claude Code hooks)
    python3 setup.py --permissions    # only check Accessibility and Screen Recording, and show the guides

Standard library only. Nothing is sent anywhere: the script runs `swiftc`, `codesign`, `claude mcp`
and `codex mcp`, edits your own Claude Code settings file, and writes the Chrome files above.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

NAME = "mac-cu"
LEGACY_NAME = "codex-cu"
HERE = Path(__file__).resolve().parent
FOCUS = HERE / "focus.py"
SETTINGS = Path.home() / ".claude" / "settings.json"
SUPPORT = Path.home() / "Library" / "Application Support"
# The app bundle: a path that does not change with the plugin version, so the registrations below stay valid.
BUNDLE = SUPPORT / "mac-cu" / "mac-cu.app"
BUNDLE_ID = "com.kakao.mac-cu"
SERVER = BUNDLE / "Contents" / "MacOS" / "mac-cu"
# A copy of the program next to this script, for `scripts/mac-cu --mode` as the docs say.
LOCAL = HERE / "mac-cu"
PLUGIN_MANIFEST = HERE.parents[2] / ".claude-plugin" / "plugin.json"
ICON_SOURCE = HERE.parent / "assets" / "mac-cu-icon.png"
INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleExecutable</key><string>mac-cu</string>
  <key>CFBundleIdentifier</key><string>com.kakao.mac-cu</string>
  <key>CFBundleName</key><string>mac-cu</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>{version}</string>
  <key>LSUIElement</key><true/>
  <key>NSPrincipalClass</key><string>NSApplication</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
"""
EXTENSION_SOURCE = HERE.parent / "chrome-extension"
# A folder that does not change with the plugin version: Chrome loads the unpacked extension from it.
EXTENSION_FOLDER = SUPPORT / "mac-cu" / "chrome-extension"
# The ID follows from the "key" in chrome-extension/manifest.json.
EXTENSION_ID = "ifkhldnpkcfdbegecenabmnkjonmddng"
HOST_MANIFEST = SUPPORT / "Google" / "Chrome" / "NativeMessagingHosts" / "com.kakao.mac_cu.json"


def fail(message: str) -> None:
    print(f"\nSetup stopped: {message}", file=sys.stderr)
    sys.exit(1)


def build(sources: list, output: Path) -> bool:
    """Build into a new file, then replace the old one: a running copy keeps its own file."""
    temporary = output.with_name(output.name + ".new")
    built = subprocess.run(["swiftc", "-O", *map(str, sources), "-o", str(temporary)], capture_output=True, text=True)
    if built.returncode != 0:
        print(built.stderr.strip(), file=sys.stderr)
        return False
    os.replace(temporary, output)
    return True


def signing_identity() -> str:
    """The SHA-1 of an "Apple Development" identity (iOS developers have one), else "-" for an ad-hoc signature.
    An ad-hoc signature changes with each build, and macOS then drops the Accessibility permission."""
    found = subprocess.run(["security", "find-identity", "-v", "-p", "codesigning"], capture_output=True, text=True).stdout
    return next((line.split()[1] for line in found.splitlines() if "Apple Development" in line), "-")


def build_app_icon(resources: Path) -> bool:
    """macOS builds the icon bundle from one PNG; generated sizes stay in the temporary app."""
    if not ICON_SOURCE.is_file():
        print(f"App icon is missing: {ICON_SOURCE}", file=sys.stderr)
        return False
    iconset = resources.parent / "AppIcon.iconset"
    shutil.rmtree(iconset, ignore_errors=True)
    iconset.mkdir()
    try:
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                pixels = str(size * scale)
                target = iconset / f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
                resized = subprocess.run(["/usr/bin/sips", "--resampleHeightWidth", pixels, pixels,
                                          str(ICON_SOURCE), "--out", str(target)], capture_output=True, text=True)
                if resized.returncode != 0:
                    print(f"Could not resize app icon: {resized.stderr.strip() or resized.stdout.strip()}", file=sys.stderr)
                    return False
        output = resources / "AppIcon.icns"
        packed = subprocess.run(["/usr/bin/iconutil", "--convert", "icns", "--output", str(output), str(iconset)],
                                capture_output=True, text=True)
        if packed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            print(f"Could not build AppIcon.icns: {packed.stderr.strip() or packed.stdout.strip()}", file=sys.stderr)
            return False
        return True
    except OSError as error:
        print(f"Could not build app icon: {error}", file=sys.stderr)
        return False
    finally:
        shutil.rmtree(iconset, ignore_errors=True)


def build_app() -> bool:
    """Build mac-cu.app in a new folder, sign it, then put it in place: a running daemon keeps its own files."""
    temporary = BUNDLE.with_name(BUNDLE.name + ".new")
    shutil.rmtree(temporary, ignore_errors=True)
    (temporary / "Contents" / "MacOS").mkdir(parents=True)
    (temporary / "Contents" / "Resources").mkdir()
    version = json.loads(PLUGIN_MANIFEST.read_text())["version"]
    (temporary / "Contents" / "Info.plist").write_text(INFO_PLIST.format(version=version))
    if not build_app_icon(temporary / "Contents" / "Resources"):
        return False
    if (HERE.parent / "always-allow.txt").exists():
        shutil.copy(HERE.parent / "always-allow.txt", temporary / "Contents" / "Resources")
    sources = sorted((HERE / "mac-cu-src").glob("*.swift"))
    built = subprocess.run(["swiftc", "-O", *map(str, sources), "-o", str(temporary / "Contents" / "MacOS" / "mac-cu")],
                           capture_output=True, text=True)
    if built.returncode != 0:
        print(built.stderr.strip(), file=sys.stderr)
        return False
    identity = signing_identity()
    signed = subprocess.run(["codesign", "--force", "--sign", identity, "--identifier", BUNDLE_ID, str(temporary)],
                            capture_output=True, text=True)
    if signed.returncode != 0 and identity != "-":
        # The key was refused (keychain prompt) or the certificate is out of date: an ad-hoc signature still runs.
        print(f"Could not sign with the Apple Development identity ({signed.stderr.strip()}); signing ad-hoc.")
        identity = "-"
        signed = subprocess.run(["codesign", "--force", "--sign", identity, "--identifier", BUNDLE_ID, str(temporary)],
                                capture_output=True, text=True)
    if signed.returncode != 0:
        print(signed.stderr.strip(), file=sys.stderr)
        return False
    shutil.rmtree(BUNDLE, ignore_errors=True)
    os.rename(temporary, BUNDLE)
    shutil.copy2(SERVER, LOCAL)
    # The bundle's signature seals Info.plist too, so macOS kills the copy outside the bundle: sign it ad-hoc.
    subprocess.run(["codesign", "--force", "--sign", "-", str(LOCAL)], capture_output=True)
    print(f"Built {BUNDLE} ({version}), signed " + ("ad-hoc: after an update you may have to turn the Accessibility"
          " permission of mac-cu on again." if identity == "-" else "with your Apple Development identity."))
    return True


def is_our_hook(entry: dict) -> bool:
    for hook in entry.get("hooks", []):
        command = hook.get("command", "")
        if "focus.py" in command or "approvals.py" in command:
            return True
        if hook.get("type") == "mcp_tool" and hook.get("server") == LEGACY_NAME and hook.get("tool") == "turn_ended":
            return True
    return False


def wanted_hooks() -> dict:
    """The hook entries this skill adds, by event: the focus glow around the target window."""
    command = f'python3 "{FOCUS}"'
    return {
        "PostToolUse": [{"matcher": f"mcp__{NAME}__.*", "hooks": [{"type": "command", "command": f"{command} post"}]}],
        "Stop": [{"hooks": [{"type": "command", "command": f"{command} stop"}]}],
        "SubagentStop": [{"hooks": [{"type": "command", "command": f"{command} subagent-stop"}]}],
    }


def update_hooks(install: bool, dry_run: bool) -> None:
    """Remove every hook of this skill (also older ones), then add the current ones when installing."""
    settings = json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {}
    hooks = settings.setdefault("hooks", {})
    add = wanted_hooks() if install else {}
    for event in set(hooks) | set(add):
        kept = [entry for entry in hooks.get(event, []) if not is_our_hook(entry)] + add.get(event, [])
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks")
    if dry_run:
        print(f"Would {'replace' if install else 'remove'} the hooks of this skill in {SETTINGS}.")
        return
    if SETTINGS.exists():
        SETTINGS.with_name("settings.json.backup-mac-cu").write_text(SETTINGS.read_text())
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"{'Updated' if install else 'Removed'} the hooks in {SETTINGS} (backup: settings.json.backup-mac-cu).")


# The ChatGPT app ships the Codex CLI without putting it on PATH.
CODEX_IN_APP = Path("/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex")


def find_cli(agent: str):
    found = shutil.which(agent)
    if not found and agent == "codex" and CODEX_IN_APP.exists():
        found = str(CODEX_IN_APP)
    return found


def register_claude(claude: str, uninstall: bool) -> None:
    for name in (LEGACY_NAME, NAME):
        subprocess.run([claude, "mcp", "remove", name, "--scope", "user"], capture_output=True, text=True)
    if uninstall:
        print(f'Claude Code: removed the MCP server "{NAME}".')
        update_hooks(install=False, dry_run=False)
        return
    spec = {"type": "stdio", "command": str(SERVER), "args": []}
    added = subprocess.run([claude, "mcp", "add-json", NAME, json.dumps(spec), "--scope", "user"],
                           capture_output=True, text=True)
    if added.returncode != 0:
        fail(f"`claude mcp add-json` failed:\n{added.stderr.strip() or added.stdout.strip()}")
    check = subprocess.run([claude, "mcp", "get", NAME], capture_output=True, text=True, timeout=60)
    status = next((line.strip() for line in check.stdout.splitlines() if line.strip().startswith("Status:")), "")
    print(f'Claude Code: registered "{NAME}" for all your projects. {status}')
    if "Connected" not in status:
        fail(f"The server did not connect. Run `claude mcp get {NAME}` to see why.")
    update_hooks(install=True, dry_run=False)


def register_codex(codex: str, uninstall: bool) -> None:
    """Codex gets the server only. The focus glow hooks are for Claude Code."""
    subprocess.run([codex, "mcp", "remove", NAME], capture_output=True, text=True)
    if uninstall:
        print(f'Codex: removed the MCP server "{NAME}".')
        return
    added = subprocess.run([codex, "mcp", "add", NAME, "--", str(SERVER)], capture_output=True, text=True)
    check = subprocess.run([codex, "mcp", "get", NAME], capture_output=True, text=True, timeout=60)
    if added.returncode != 0 or str(SERVER) not in check.stdout:
        fail(f"`codex mcp add` failed:\n{added.stderr.strip() or added.stdout.strip()}")
    print(f'Codex: registered "{NAME}" in ~/.codex/config.toml.')


def install_chrome_extension(uninstall: bool) -> None:
    """The extension files and the native messaging host manifest (the host is mac-cu itself)."""
    if uninstall:
        HOST_MANIFEST.unlink(missing_ok=True)
        shutil.rmtree(EXTENSION_FOLDER, ignore_errors=True)
        print("Chrome: removed the mac-cu extension files and native messaging host. Remove the extension in chrome://extensions.")
        return
    if not HOST_MANIFEST.parent.parent.exists():
        print("Chrome: no Google Chrome profile was found, so the extension engine is not set up.")
        return
    shutil.copytree(EXTENSION_SOURCE, EXTENSION_FOLDER, dirs_exist_ok=True)
    HOST_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    HOST_MANIFEST.write_text(json.dumps({
        "name": "com.kakao.mac_cu", "description": "mac-cu", "path": str(SERVER), "type": "stdio",
        "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"],
    }, indent=2) + "\n")
    print(f"Chrome: copied the mac-cu extension to {EXTENSION_FOLDER} and registered its native messaging host.\n"
          "  Once, to use the browser tool with engine \"extension\": chrome://extensions > Developer mode on >"
          " Load unpacked > that folder. After a plugin update, click the reload button of mac-cu in"
          " chrome://extensions.")


REGISTER = {"claude": register_claude, "codex": register_codex}
APP_NAMES = {"claude": "Claude Code", "codex": "Codex"}


def quit_daemon() -> None:
    """The running daemon is an older build (or none runs): the next client call starts the new one."""
    subprocess.run([str(SERVER), "--quit-daemon"], timeout=15)


def request_permissions() -> None:
    """Through the client, which starts the daemon (`open -a`, so it is its own responsible process): the
    daemon asks macOS about mac-cu.app. A missing permission opens its page in System Settings with a panel
    that shows the app's icon to drag into the list."""
    client = subprocess.Popen([str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    client.stdin.write('{"mac-cu":"permissions"}\n')
    client.stdin.flush()
    reply = client.stdout.readline()
    client.stdin.close()
    client.wait(timeout=15)
    try:
        print(json.loads(reply)["text"])
    except (ValueError, KeyError):
        fail(f"the mac-cu daemon did not answer the permissions request. Run `{SERVER} --daemon` to see why.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Connect mac-cu to Claude Code and/or Codex.")
    parser.add_argument("--agent", action="append", choices=sorted(REGISTER),
                        help="The agent to connect (repeat for both). Default: every agent whose CLI is found.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change; change nothing.")
    parser.add_argument("--uninstall", action="store_true", help="Remove the server (and the Claude Code hooks).")
    parser.add_argument("--permissions", action="store_true",
                        help="Only check Accessibility and Screen Recording for this app, and show the guides.")
    args = parser.parse_args()

    if platform.system() != "Darwin":
        fail("mac-cu works on macOS only.")
    if args.permissions:
        if not SERVER.exists():
            fail("mac-cu is not built yet. Run this script without --permissions first.")
        request_permissions()
        return 0
    agents = args.agent or [agent for agent in REGISTER if find_cli(agent)]
    if not agents:
        fail("Neither the `claude` nor the `codex` command was found. Install Claude Code or Codex first.")
    clis = {agent: find_cli(agent) for agent in agents}
    for agent, cli in clis.items():
        if not cli:
            fail(f"The `{agent}` command was not found. Install {APP_NAMES[agent]} first.")

    if args.dry_run:
        action = "remove" if args.uninstall else "build mac-cu.app and focus-overlay, then register"
        print(f'Would {action} the user MCP server "{NAME}" ({SERVER}) for: {", ".join(APP_NAMES[a] for a in agents)}.')
        if "claude" in agents:
            update_hooks(install=not args.uninstall, dry_run=True)
        print(f"Would {'remove' if args.uninstall else 'write'} {EXTENSION_FOLDER} and {HOST_MANIFEST}.")
        return 0

    names = " and ".join(APP_NAMES[a] for a in agents)
    if args.uninstall:
        for agent, cli in clis.items():
            REGISTER[agent](cli, uninstall=True)
        install_chrome_extension(uninstall=True)
        if SERVER.exists():
            quit_daemon()
        shutil.rmtree(BUNDLE, ignore_errors=True)
        LOCAL.unlink(missing_ok=True)
        print(f"\nDone. Close {names} and open it again.")
        return 0

    if not shutil.which("swiftc"):
        fail("swiftc was not found. Install the Xcode command line tools: xcode-select --install")
    if SERVER.exists():
        quit_daemon()
    if not build_app():
        fail("mac-cu-src did not build (see the messages above).")
    if build([HERE / "focus-overlay.swift"], HERE / "focus-overlay"):
        print("Built the focus glow.")
    else:
        print("The focus glow did not build. mac-cu still works, with no glow.")

    for agent, cli in clis.items():
        REGISTER[agent](cli, uninstall=False)
    install_chrome_extension(uninstall=False)
    print(f"\nDone. Close {names} and open it again (in Codex, a new chat is enough), so it loads the new tools.")
    print("mac-cu runs as a menu bar app (mac-cu.app) that the first call starts. It needs the Accessibility"
          " permission, Screen Recording for screenshots, and Automation for the browser tool:"
          " System Settings > Privacy & Security.")
    request_permissions()
    return 0


if __name__ == "__main__":
    sys.exit(main())
