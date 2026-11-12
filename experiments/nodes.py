"""Node counts and one-core time for Minimax, Alpha-Beta and Alpha-Beta with ordering.

Node counts are exact and repeatable; times depend on the machine and its load.
Entries that are too expensive are written with a "skipped" status, never left out:

skipped_node_limit  gomoku9 Minimax predicted above MINIMAX_NODE_LIMIT, the prediction
                    being (nodes one ply shallower) x (moves at the root)
skipped_shallower   the same search one ply shallower did not finish
skipped_budget      the whole script ran past TOTAL_BUDGET_S
timeout             the search was stopped after SEARCH_TIMEOUT_S

skipped_budget and timeout depend on the machine and its load, the others only on node counts.

    python -m experiments.nodes
"""
import csv
import json
import math
import random
import time

from experiments.runner import RAW_DIR
from gameai.games.tictactoe import TicTacToe
from gameai.games.xiangqi import Xiangqi
from gameai.search.minimax import search

SEED = 2024
MINIMAX_NODE_LIMIT = 300_000
SEARCH_TIMEOUT_S = 60
TOTAL_BUDGET_S = 660
GOMOKU_PLIES = (8, 10, 12, 14, 16)
XIANGQI_PLIES = (16, 24, 32)
ALGORITHMS = {
    "minimax": {"pruning": False, "order": False},
    "alphabeta": {"pruning": True, "order": False},
    "alphabeta_ordered": {"pruning": True, "order": True},
}
FIELDS = ["game", "position", "moves", "radius", "depth", "algorithm", "status", "nodes",
          "predicted_nodes", "wall_s", "cpu_s", "value", "best_moves", "root_moves"]


class _TimedOut(Exception):
    pass


def new_gomoku():
    return TicTacToe(9, 5)


def midgame_moves(new_game, plies, rng, candidates, min_moves=1):
    """Random play from the start until ``plies`` moves are made and the game is still open.

    ``min_moves`` rejects positions with very few replies, such as being in check.
    """
    while True:
        game, moves = new_game(), []
        while len(moves) < plies and game.winner() is None:
            moves.append(rng.choice(candidates(game)))
            game.play(moves[-1])
        if game.winner() is None and len(candidates(game)) >= min_moves:
            return moves


def gomoku_positions(seed=SEED):
    """{name: moves}: stones placed next to earlier stones, as they are in real games."""
    rng = random.Random(seed)
    return {f"midgame_{plies}": midgame_moves(new_gomoku, plies, rng, lambda g: g.candidate_moves(1))
            for plies in GOMOKU_PLIES}


def xiangqi_positions(seed=SEED):
    rng = random.Random(seed)
    positions = {"start": []}
    for plies in XIANGQI_PLIES:
        positions[f"midgame_{plies}"] = midgame_moves(
            Xiangqi, plies, rng, lambda g: g.legal_moves(), min_moves=20)
    return positions


def replay(new_game, moves):
    game = new_game()
    for move in moves:
        game.play(tuple(move) if isinstance(move, list) else move)
    return game


def _measure(game, depth, base_moves, algorithm, repeats):
    """Best of ``repeats`` runs. Works on a clone: a timeout leaves the board mid-search."""
    best_wall = best_cpu = float("inf")
    for _ in range(repeats):
        deadline = time.perf_counter() + SEARCH_TIMEOUT_S

        def moves(state):
            if time.perf_counter() > deadline:
                raise _TimedOut
            return base_moves(state)

        start_wall, start_cpu = time.perf_counter(), time.process_time()
        result = search(game.clone(), depth=depth, moves=moves, **ALGORITHMS[algorithm])
        best_wall = min(best_wall, time.perf_counter() - start_wall)
        best_cpu = min(best_cpu, time.process_time() - start_cpu)
    return result, best_wall, best_cpu


def entries():
    """Every planned search, shallow first so that a budget overrun only costs deep ones.

    Radius 2 comes last in each depth: at depth 4 it is the slowest group of all.
    """
    for name, moves in {"empty": [], "corner": [0], "centre": [4]}.items():
        for algorithm in ALGORITHMS:
            yield "ttt3", lambda: TicTacToe(3, 3), name, moves, None, None, algorithm
    gomoku, xiangqi = gomoku_positions(), xiangqi_positions()

    def gomoku_entries(radius, depth):
        for name, moves in gomoku.items():
            for algorithm in ALGORITHMS:
                yield "gomoku9", new_gomoku, name, moves, radius, depth, algorithm

    for depth in range(1, 5):
        yield from gomoku_entries(1, depth)
        for name, moves in xiangqi.items():
            for algorithm in ALGORITHMS:
                if depth <= 3 or algorithm != "minimax":
                    yield "xiangqi", Xiangqi, name, moves, None, depth, algorithm
        yield from gomoku_entries(2, depth)


def run_entry(entry, previous_nodes, elapsed):
    game_name, new_game, name, moves, radius, depth, algorithm = entry
    game = replay(new_game, moves)
    base = (lambda s: s.candidate_moves(radius)) if radius else (lambda s: s.legal_moves())
    root_moves = len(base(game))
    row = {"game": game_name, "position": name, "moves": json.dumps(moves, separators=(",", ":")),
           "radius": radius or "", "depth": depth or "full", "algorithm": algorithm,
           "root_moves": root_moves}
    predicted = None if previous_nodes is None else previous_nodes * root_moves
    row["predicted_nodes"] = predicted if predicted is not None else ""
    if previous_nodes is None:
        row["status"] = "skipped_shallower"
    elif elapsed > TOTAL_BUDGET_S:
        row["status"] = "skipped_budget"
    elif game_name == "gomoku9" and algorithm == "minimax" and predicted > MINIMAX_NODE_LIMIT:
        row["status"] = "skipped_node_limit"
    else:
        try:
            # Small searches are timed five times: they are close to the clock resolution.
            result, wall, cpu = _measure(game, depth, base, algorithm, 5 if depth is None else 1)
        except _TimedOut:
            row["status"] = "timeout"
        else:
            row.update(status="ok", nodes=result.nodes, wall_s=round(wall, 4), cpu_s=round(cpu, 4),
                       value=result.value, best_moves=json.dumps(sorted(result.best_moves),
                                                                 separators=(",", ":")))
    return row


def entry_key(entry):
    game, _, name, moves, radius, depth, algorithm = entry
    return (game, name, json.dumps(moves, separators=(",", ":")), str(radius or ""),
            str(depth or "full"), algorithm)


def row_key(row):
    return (row["game"], row["position"],
            json.dumps(json.loads(row["moves"]), separators=(",", ":")), row["radius"],
            row["depth"], row["algorithm"])


def existing_rows(path):
    """Refuse ambiguous evidence before appending; completed failures remain evidence too."""
    if not path.exists() or not path.stat().st_size:
        return {}
    if not path.read_bytes().endswith(b"\n"):
        raise ValueError(f"nodes.csv has an unterminated record; inspect before resuming: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"unexpected nodes schema: {path}")
        rows = {}
        for row in reader:
            key = row_key(row)
            if key in rows:
                raise ValueError(f"duplicate node identity: {key}")
            if row["status"] not in {"ok", "skipped_shallower", "skipped_budget",
                                      "skipped_node_limit", "timeout"}:
                raise ValueError(f"invalid node status: {row}")
            if row["status"] == "ok":
                if int(row["nodes"]) < 1 or any(not math.isfinite(float(row[k]))
                        or float(row[k]) < 0 for k in ("wall_s", "cpu_s")):
                    raise ValueError(f"invalid node measurement: {row}")
            rows[key] = row
    return rows


def main(path=None):
    path = path or RAW_DIR / "nodes.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    previous = {}
    completed = existing_rows(path)
    planned = list(entries())
    if set(completed) - {entry_key(entry) for entry in planned}:
        raise ValueError("nodes.csv contains an unplanned configuration; inspect before resuming")
    needs_header = not path.exists() or not path.stat().st_size
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, lineterminator="\n")
        if needs_header:
            writer.writeheader()
        for entry in planned:
            game_name, _, name, _, radius, depth, algorithm = entry
            key = (game_name, name, radius, algorithm)
            if entry_key(entry) in completed:
                old = completed[entry_key(entry)]
                previous[key] = int(old["nodes"]) if old["status"] == "ok" else None
                continue
            row = run_entry(entry, previous.get(key, 1), time.perf_counter() - start)
            previous[key] = row.get("nodes")
            writer.writerow(row)
            handle.flush()
            print(f"{time.perf_counter() - start:6.0f}s {game_name} {name} r={radius} d={depth} "
                  f"{algorithm}: {row['status']} {row.get('nodes', '')} {row.get('wall_s', '')}s",
                  flush=True)
    print("RESULT: resumed without replacing existing rows:", path, flush=True)


if __name__ == "__main__":
    main()
