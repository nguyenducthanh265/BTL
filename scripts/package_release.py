"""Create a portable technical source bundle with per-file integrity metadata.

The runtime wheel is built separately. No external publication is performed.
"""
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent


def main():
    version = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)[1]
    verification_log = ROOT / "docs/verification-technical.log"
    log_bytes = verification_log.read_bytes()
    log_encoding = "utf-16" if log_bytes.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    log_lines = log_bytes.decode(log_encoding).strip().splitlines()
    summary = log_lines[-1] if log_lines else ""
    if not re.search(r"\b\d+ passed\b", summary) or re.search(r"\b(?:failed|errors?)\b", summary):
        raise SystemExit("Refusing release: final integrated test log is not a passing run.")
    matches = json.loads((ROOT / "results/integrity.json").read_text())
    if any(v["errors"] or v["duplicates"] or v["valid"] != v["rows"]
           or v["matched"] != v["planned"] for v in matches.values()):
        raise SystemExit("Refusing release: match audit has errors or incomplete planned coverage.")
    auxiliary = json.loads((ROOT / "results/auxiliary_integrity.json").read_text())
    if auxiliary["errors"]:
        raise SystemExit("Refusing release: auxiliary audit has errors.")
    snapshot = json.loads((ROOT / "results/source_data/manifest.json").read_text())
    for name, record in snapshot["files"].items():
        for folder in ("results/raw", "results/source_data/raw"):
            data = (ROOT / folder / name).read_bytes()
            if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise SystemExit(f"Refusing release: {folder}/{name} differs from the audited snapshot.")
    files = set()
    for folder, suffixes in {
        "gameai": {".py", ".html"}, "experiments": {".py"},
        "tests": {".py"}, "scripts": {".py"},
        "results/raw": {".csv"},
        "results/source_data": {".csv", ".json"},
        "results/tables": {".md", ".tex"},
        "results/figures": {".png", ".pdf"},
        "docs/mobile-qa": {".png", ".json", ".js", ".md", ".log", ".py"},
    }.items():
        files.update(p for p in (ROOT / folder).rglob("*")
                     if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts)
    for name in ("README.md", "PLAN.md", "ARCHITECTURE.md", "pyproject.toml", ".gitignore",
                 "paper/build.py", "results/SUMMARY.md", "results/integrity.json",
                 "results/auxiliary_integrity.json",
                 "results/snapshot_integrity.json",
                 "docs/TECHNICAL_STATUS.md", "docs/final_experiments.md", "docs/final_demo.md",
                 "docs/final_findings.md", "docs/verification-technical.log"):
        path = ROOT / name
        if not path.is_file():
            raise FileNotFoundError(path)
        files.add(path)
    metadata = {"name": "btl-ai-mcts", "version": version,
                "scope": "Technical source, tests, validated experiment data; report/publication deferred",
                "verification": summary,
                "files": {p.relative_to(ROOT).as_posix(): {
                    "bytes": p.stat().st_size,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()
                } for p in sorted(files)}}
    out = ROOT / "output/packages"
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"btl-ai-mcts-{version}-technical.zip"
    prefix = f"btl-ai-mcts-{version}"
    with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(files):
            archive.write(path, prefix + "/" + path.relative_to(ROOT).as_posix())
        archive.writestr(prefix + "/RELEASE_MANIFEST.json", json.dumps(metadata, indent=2) + "\n")
    with ZipFile(target) as archive:
        assert archive.testzip() is None
        for name, record in metadata["files"].items():
            data = archive.read(prefix + "/" + name)
            assert len(data) == record["bytes"]
            assert hashlib.sha256(data).hexdigest() == record["sha256"], name
    receipt = {"archive": target.name, "bytes": target.stat().st_size,
               "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
               "files": len(files), "version": version}
    (out / "technical_release.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
