"""Run matches in parallel and append one CSV row per game, safe to stop and resume.

    python -m experiments.runner --suite gomoku9 --workers 14
"""
import argparse
import csv
import hashlib
import json
import multiprocessing
import random
import time
from pathlib import Path

from experiments.data import game_key, valid_game
from experiments.plan import build_suite, expected_rows, row_key
from gameai.agents import build_agent
from gameai.games.tictactoe import TicTacToe
from gameai.games.xiangqi import Xiangqi
from gameai.match import play_game

RAW_DIR = Path(__file__).resolve().parent.parent / "results" / "raw"
FIELDS = ["exp", "game", "a", "b", "index", "a_first", "a_score", "plies",
          "a_time", "b_time", "a_nodes", "b_nodes", "seed", "moves"]
GAME_FACTORIES = {
    "ttt3": lambda: TicTacToe(3, 3),
    "gomoku9": lambda: TicTacToe(9, 5),
    "xiangqi": Xiangqi,
}


def match_seed(exp, game, a, b, index):
    """Seed derived from the match description, stable across processes and machines."""
    text = json.dumps([exp, game, a, b, index], sort_keys=True)
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def run_one(task):
    exp, game_name, a_spec, b_spec, index = (
        task["exp"], task["game"], task["a"], task["b"], task["index"]
    )
    seed = match_seed(exp, game_name, a_spec, b_spec, index)
    rng = random.Random(seed)
    a_first = index % 2 == 0  # alternate who moves first
    a_agent, b_agent = build_agent(a_spec), build_agent(b_spec)
    first, second = (a_agent, b_agent) if a_first else (b_agent, a_agent)
    outcome = play_game(GAME_FACTORIES[game_name](), first, second, rng)
    # The first agent always plays +1, so a win for +1 is a win for it.
    first_score = (outcome["winner"] + 1) / 2
    return {
        "exp": exp,
        "game": game_name,
        "a": json.dumps(a_spec, sort_keys=True),
        "b": json.dumps(b_spec, sort_keys=True),
        "index": index,
        "a_first": int(a_first),
        "a_score": first_score if a_first else 1 - first_score,
        "plies": outcome["plies"],
        "a_time": round(outcome["first_time" if a_first else "second_time"], 4),
        "b_time": round(outcome["second_time" if a_first else "first_time"], 4),
        "a_nodes": outcome["first_nodes" if a_first else "second_nodes"],
        "b_nodes": outcome["second_nodes" if a_first else "first_nodes"],
        "seed": seed,
        "moves": json.dumps(outcome["moves"], separators=(",", ":")),
    }


def _completed_keys(path):
    done = set()
    if path.exists():
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if valid_game(row):
                    done.add(game_key(row))
    return done


def _drop_partial_last_line(path):
    """Remove a row left unfinished by a crash, so that game is simply played again."""
    if path.exists():
        data = path.read_bytes()
        if data and not data.endswith(b"\n"):
            path.write_bytes(data[: data.rfind(b"\n") + 1])


def run_tasks(tasks, path, workers=1, progress_every=0):
    """Play every task whose row is not in ``path`` yet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _drop_partial_last_line(path)
    done = _completed_keys(path)
    pending = [
        t for t in tasks if row_key(t["exp"], t["game"], t["a"], t["b"], t["index"]) not in done
    ]
    needs_header = not path.exists() or path.stat().st_size == 0
    start = time.perf_counter()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, lineterminator="\n")
        if needs_header:
            writer.writeheader()
        if workers == 1:
            results = map(run_one, pending)
            for count, row in enumerate(results, 1):
                writer.writerow(row)
                handle.flush()
                _report(count, len(pending), start, progress_every)
        else:
            with multiprocessing.Pool(workers) as pool:
                for count, row in enumerate(pool.imap_unordered(run_one, pending), 1):
                    writer.writerow(row)
                    handle.flush()
                    _report(count, len(pending), start, progress_every)
    return len(pending)


def _report(count, total, start, every):
    if every and (count % every == 0 or count == total):
        elapsed = time.perf_counter() - start
        print(f"{count}/{total} games, {elapsed:.0f}s elapsed", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True, choices=["ttt3", "gomoku9", "xiangqi"])
    parser.add_argument("--workers", type=int, default=max(1, (multiprocessing.cpu_count() or 2) - 2))
    parser.add_argument("--exp", nargs="*", help="only these experiments")
    args = parser.parse_args()
    tasks = build_suite(args.suite)
    if args.exp:
        tasks = [t for t in tasks if t["exp"] in args.exp]
    # Cheap games first, so a stopped run still has complete low-iteration results.
    tasks.sort(key=lambda t: t["a"].get("iterations", 0) + t["b"].get("iterations", 0))
    path = RAW_DIR / f"{args.suite}.csv"
    print(f"{args.suite}: {expected_rows(tasks, path)} of {len(tasks)} games to play", flush=True)
    run_tasks(tasks, path, args.workers, progress_every=max(1, len(tasks) // 50))
    print("RESULT: done", expected_rows(tasks, path), "missing", flush=True)


if __name__ == "__main__":
    main()
