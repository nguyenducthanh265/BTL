"""Check the claim "MCTS never loses at 3x3 Tic-Tac-Toe" as hard as is practical.

A randomised algorithm with finite iterations cannot be proved perfect by playing a
few games, so two stronger tests are used:

move quality        run MCTS on every reachable position and compare its move with the
                    exact solution. A blunder is a move that worsens the game value.
exhaustive opponent let MCTS play one side while the other side tries EVERY legal reply
                    at every turn, so all opponent strategies are covered at once.

    python -m experiments.verify_3x3 --workers 14
"""
import argparse
import csv
import multiprocessing
import random
from pathlib import Path

from gameai.agents import build_agent
from gameai.games.tictactoe import TicTacToe
from gameai.search.minimax import optimal_moves
from experiments.plan import TTT_ITERATIONS, mcts

RAW_DIR = Path(__file__).resolve().parent.parent / "results" / "raw"
QUALITY_SEEDS = 3
EXHAUSTIVE_SEEDS = 20
EXHAUSTIVE_ITERATIONS = (50, 100, 200, 500, 1000, 2000, 5000)


def reachable_positions():
    """Every position with a move still to make, each listed once, as move sequences."""
    found = {}

    def visit(game):
        if game.winner() is not None or game.key() in found:
            return
        found[game.key()] = list(game.history)
        for move in game.legal_moves():
            game.play(move)
            visit(game)
            game.undo()

    visit(TicTacToe(3, 3))
    return list(found.values())


def _replay(moves):
    game = TicTacToe(3, 3)
    for move in moves:
        game.play(move)
    return game


def move_quality(agent, positions, rng, memo=None):
    memo = {} if memo is None else memo
    blunders = 0
    examples = []
    for moves in positions:
        game = _replay(moves)
        good = optimal_moves(game, memo)
        choice = agent.choose(game, rng)
        if choice not in good:
            blunders += 1
            examples.append(moves + [choice])
    return {"positions": len(positions), "blunders": blunders, "examples": examples}


def exhaustive_opponent(agent, role, rng):
    """Agent plays ``role``; the opponent branches over every legal move."""
    report = {"lines": 0, "wins": 0, "draws": 0, "losses": 0, "loss_examples": []}

    def visit(game):
        result = game.winner()
        if result is not None:
            report["lines"] += 1
            if result == 0:
                report["draws"] += 1
            elif result == role:
                report["wins"] += 1
            else:
                report["losses"] += 1
                report["loss_examples"].append(list(game.history))
            return
        if game.to_play == role:
            game.play(agent.choose(game, rng))
            visit(game)
            game.undo()
            return
        for move in game.legal_moves():
            game.play(move)
            visit(game)
            game.undo()

    visit(TicTacToe(3, 3))
    return report


def _quality_task(args):
    iterations, seed = args
    agent = build_agent(mcts(iterations))
    report = move_quality(agent, reachable_positions(), random.Random(f"quality-{iterations}-{seed}"))
    return {"iterations": iterations, "seed": seed, "positions": report["positions"],
            "blunders": report["blunders"]}


def _exhaustive_task(args):
    iterations, role, seed = args
    agent = build_agent(mcts(iterations))
    report = exhaustive_opponent(agent, role, random.Random(f"exhaustive-{iterations}-{role}-{seed}"))
    return {"iterations": iterations, "role": role, "seed": seed, "lines": report["lines"],
            "wins": report["wins"], "draws": report["draws"], "losses": report["losses"]}


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=max(1, (multiprocessing.cpu_count() or 2) - 2))
    args = parser.parse_args()
    with multiprocessing.Pool(args.workers) as pool:
        quality = pool.map(
            _quality_task,
            [(it, seed) for it in TTT_ITERATIONS for seed in range(QUALITY_SEEDS)],
            chunksize=1,
        )
        exhaustive = pool.map(
            _exhaustive_task,
            [(it, role, seed) for it in EXHAUSTIVE_ITERATIONS for role in (1, -1)
             for seed in range(EXHAUSTIVE_SEEDS)],
            chunksize=1,
        )
    _write(RAW_DIR / "verify_quality.csv", quality)
    _write(RAW_DIR / "verify_exhaustive.csv", exhaustive)
    for iterations in EXHAUSTIVE_ITERATIONS:
        rows = [r for r in exhaustive if r["iterations"] == iterations]
        print(iterations, "lines", sum(r["lines"] for r in rows),
              "losses", sum(r["losses"] for r in rows), flush=True)
    print("RESULT: done", flush=True)


if __name__ == "__main__":
    main()
