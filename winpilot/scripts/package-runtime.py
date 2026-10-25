"""Package an already verified publish directory and pin all runtime files."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.1"


def main():
    app = ROOT / "tool/artifacts/app"
    if not (app / "windows-pilot.exe").is_file():
        raise SystemExit("Publish the win-x64 runtime first")
    files = sorted(p for p in app.rglob("*") if p.is_file())
    if any(p.is_symlink() for p in files):
        raise SystemExit("Symlinks are not allowed")
    output = ROOT / "evidence/release"
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"winpilot-{VERSION}-win-x64.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in files:
            zipped.write(path, path.relative_to(app).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = dict(version=VERSION, platform="win-x64", sha256=digest,
                    files={p.relative_to(app).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (ROOT / "runtime/distribution.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert set(zipped.namelist()) == set(manifest["files"])
        for name, expected in manifest["files"].items():
            assert hashlib.sha256(zipped.read(name)).hexdigest() == expected, name
    print(json.dumps(dict(archive=str(archive), sha256=digest, files=len(files))))


if __name__ == "__main__":
    main()
