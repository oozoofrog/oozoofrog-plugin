#!/usr/bin/env python3
"""Check the real macOS icon packer without building or replacing the app."""
import contextlib
import importlib.util
import io
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
script = Path(__file__).resolve().parents[1] / "skills/mac-computer-use/scripts/setup.py"
spec = importlib.util.spec_from_file_location("mac_cu_setup", script)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
assert plistlib.loads(setup.INFO_PLIST.format(version="1.0.0").encode())["CFBundleIconFile"] == "AppIcon"
with tempfile.TemporaryDirectory(prefix="mac-cu-icon-check-") as temporary:
    folder = Path(temporary)
    resources = folder / "Resources"
    resources.mkdir()
    assert setup.build_app_icon(resources)
    icon = resources / "AppIcon.icns"
    assert icon.read_bytes().startswith(b"icns")
    extracted = folder / "decoded.iconset"
    subprocess.run(["/usr/bin/iconutil", "--convert", "iconset", "--output", str(extracted), str(icon)], check=True)
    images = sorted(extracted.glob("*.png"))
    assert len(images) == 10
    for name, size in [("icon_16x16.png", 16), ("icon_512x512@2x.png", 1024)]:
        properties = subprocess.check_output(["/usr/bin/sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "hasAlpha", str(extracted / name)], text=True)
        assert f"pixelWidth: {size}" in properties and f"pixelHeight: {size}" in properties and "hasAlpha: yes" in properties
    assert not (folder / "AppIcon.iconset").exists()
    for source in [folder / "missing.png", folder / "invalid.png"]:
        if source.name == "invalid.png": source.write_bytes(b"not a PNG")
        setup.ICON_SOURCE = source
        with contextlib.redirect_stderr(io.StringIO()):
            assert not setup.build_app_icon(resources)
        assert not (folder / "AppIcon.iconset").exists()
print("App icon checks passed: plist, decodable ICNS, ten sizes, alpha, failure handling and cleanup.")
