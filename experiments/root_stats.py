"""What MCTS sees at the root: move, N, W, W/N and the UCT score, after a fixed search.

W counts rewards for the player choosing at the root, so W/N is that player's view.
Xiangqi uses the cutoff rollout, as all Xiangqi experiments do; the others use random.

    python -m experiments.root_stats
"""
import csv
import json
import math
import random

from experiments.nodes import gomoku_positions, new_gomoku, replay
from experiments.runner import RAW_DIR
from gameai.games.tictactoe import TicTacToe
from gameai.games.xiangqi import Xiangqi
from gameai.search.mcts import MCTS, final_move
from gameai.search.selection import ucb1

C = 1.4
ITERATIONS = (100, 1000, 5000)
SEEDS = range(5)
ASSIGNMENT_MOVES = [1, 0, 6, 4]  # X to move; cell 8 is the only move that does not lose
GOMOKU_POSITION = "midgame_12"
FIELDS = ["position", "game", "rollout", "iterations", "c", "seed", "move", "N", "W", "W_over_N",
          "UCT", "chosen"]


def positions():
    """(name, game name, game factory, moves, rollout) of every position studied."""
    new_3x3 = lambda: TicTacToe(3, 3)
    return [
        ("assignment", "ttt3", new_3x3, ASSIGNMENT_MOVES, "random"),
        ("empty_3x3", "ttt3", new_3x3, [], "random"),
        (GOMOKU_POSITION, "gomoku9", new_gomoku, gomoku_positions()[GOMOKU_POSITION], "random"),
        ("xiangqi_start", "xiangqi", Xiangqi, [], "cutoff"),
    ]


def root_rows(name, game_name, new_game, moves, rollout, iterations, seed):
    rng = random.Random(f"root-{name}-{iterations}-{seed}")
    search = MCTS(iterations, c=C, rollout=rollout, rng=rng)
    root = search.search(replay(new_game, moves))
    chosen = final_move(root.children, "robust")
    log_n = math.log(root.n)
    return [
        {"position": name, "game": game_name, "rollout": rollout, "iterations": iterations, "c": C,
         "seed": seed, "move": json.dumps(child.move, separators=(",", ":")), "N": child.n,
         "W": round(child.w, 4), "W_over_N": round(child.w / child.n, 4),
         "UCT": round(ucb1(child, root.n, log_n, C), 4), "chosen": int(child is chosen)}
        for child in sorted(root.children, key=lambda child: -child.n)
    ]


def main(path=None):
    path = path or RAW_DIR / "root_stats.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, lineterminator="\n")
        writer.writeheader()
        for position in positions():
            for iterations in ITERATIONS:
                chosen = []
                for seed in SEEDS:
                    rows = root_rows(*position, iterations, seed)
                    writer.writerows(rows)
                    chosen += [row["move"] for row in rows if row["chosen"]]
                print(position[0], iterations, "chosen per seed:", " ".join(chosen), flush=True)
    print("RESULT: wrote", path, flush=True)


if __name__ == "__main__":
    main()
