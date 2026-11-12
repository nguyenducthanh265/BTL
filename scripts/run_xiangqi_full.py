"""Resume the complete Xiangqi grid with a persistent receipt and exclusive job lock.

Only starts Xiangqi. Other raw writers and the reviewed snapshot are preserved.
Run from the project root: python -u scripts/run_xiangqi_full.py
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    from experiments.plan import build_suite, expected_rows

    folder = ROOT / "results/jobs"
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / "xiangqi.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit(f"A job lock exists: {lock}. Check its PID before starting another writer.")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"pid": os.getpid(), "started_utc": datetime.now(timezone.utc).isoformat()}, handle)
    receipt = folder / "xiangqi_full.json"
    state = {"supervisor_pid": os.getpid(), "status": "running",
             "started_utc": datetime.now(timezone.utc).isoformat(), "workers": 4,
             "raw": str(ROOT / "results/raw/xiangqi.csv"),
             "initial_missing": expected_rows(build_suite("xiangqi"), ROOT / "results/raw/xiangqi.csv")}

    def save():
        temp = receipt.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        temp.replace(receipt)

    try:
        save()
        command = [sys.executable, "-u", "-m", "experiments.runner", "--suite", "xiangqi", "--workers", "4"]
        with (folder / "xiangqi_full.log").open("a", encoding="utf-8") as log:
            child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            state["runner_pid"] = child.pid
            save()
            code = child.wait()
        missing = expected_rows(build_suite("xiangqi"), ROOT / "results/raw/xiangqi.csv")
        state.update(status="complete" if code == 0 and missing == 0 else "failed",
                     exit_code=code, missing=missing, finished_utc=datetime.now(timezone.utc).isoformat())
        save()
        if code or missing:
            raise SystemExit(code or 1)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
