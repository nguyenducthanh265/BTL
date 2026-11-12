"""Every match of the experiment, as data. Changing one thing per experiment.

exp names used by the report:
  curve       c x iterations against a fixed opponent (assignment section 4)
  wdl         win/draw/loss tables
  ab_ladder   how many iterations MCTS needs against Alpha-Beta
  rollout     heuristic rollouts against random rollouts
  final       choosing the move by N against choosing by W/N
  formula     UCT variants against the standard formula
  radius      restricting the tree to cells near stones
"""
import csv
import json
from pathlib import Path

from experiments.data import game_key, valid_game

C_VALUES = (0.5, 1.0, 1.4, 2.0)
ITERATIONS = (100, 200, 500, 1000, 2000, 5000)
TTT_ITERATIONS = (10, 25, 50, 100, 200, 500, 1000, 2000, 5000)
TTT_LOW = (10, 25, 50, 100, 200)
VARIANTS = ("no_sqrt", "no_log", "polynomial", "ucb1_tuned", "progressive_bias")

RANDOM = {"type": "random"}
PERFECT = {"type": "perfect"}
TTT_GAMES, GOMOKU_GAMES, XIANGQI_GAMES = 200, 100, 50


def mcts(iterations, c=1.4, formula="ucb1", rollout="random", final_rule="robust", radius=None):
    return {"type": "mcts", "iterations": iterations, "c": c, "formula": formula,
            "rollout": rollout, "final_rule": final_rule, "radius": radius}


def alphabeta(depth, radius=None):
    return {"type": "alphabeta", "depth": depth, "radius": radius}


def _games(exp, game, a, b, count):
    return [{"exp": exp, "game": game, "a": a, "b": b, "index": i} for i in range(count)]


def _ttt3():
    tasks = []
    full_search = alphabeta(None)
    for c in C_VALUES:
        for it in TTT_ITERATIONS:
            tasks += _games("curve", "ttt3", mcts(it, c), RANDOM, TTT_GAMES)
            tasks += _games("curve_perfect", "ttt3", mcts(it, c), PERFECT, TTT_GAMES)
    for opponent in (RANDOM, PERFECT, full_search):
        tasks += _games("wdl", "ttt3", mcts(1000), opponent, TTT_GAMES)
    for it in TTT_LOW:
        # No "cutoff" here: 3x3 games end before the cutoff depth, so it equals "heuristic".
        for rollout in ("random", "heuristic"):
            tasks += _games("rollout", "ttt3", mcts(it, rollout=rollout), PERFECT, TTT_GAMES)
        for rule in ("robust", "max_ratio"):
            tasks += _games("final", "ttt3", mcts(it, final_rule=rule), PERFECT, TTT_GAMES)
        for formula in ("ucb1",) + VARIANTS:
            for c in C_VALUES:
                tasks += _games("formula", "ttt3", mcts(it, c, formula), PERFECT, TTT_GAMES)
    return tasks


def _gomoku9():
    tasks = []
    reference = mcts(500)
    baseline = mcts(1000)
    shallow, deeper = alphabeta(1, 1), alphabeta(2, 2)
    for c in C_VALUES:
        for it in ITERATIONS:
            tasks += _games("curve", "gomoku9", mcts(it, c), reference, GOMOKU_GAMES)
    for it in (1000, 5000):
        for opponent in (RANDOM, shallow, deeper):
            tasks += _games("wdl", "gomoku9", mcts(it), opponent, GOMOKU_GAMES)
    for it in ITERATIONS:
        tasks += _games("ab_ladder", "gomoku9", mcts(it), deeper, GOMOKU_GAMES)
    # Equal iterations, then roughly equal time using the measured speed ratios.
    for rollout, it in (("heuristic", 1000), ("cutoff", 1000), ("heuristic", 220), ("cutoff", 500)):
        tasks += _games("rollout", "gomoku9", mcts(it, rollout=rollout), baseline, GOMOKU_GAMES)
    for rollout in ("random", "heuristic", "cutoff"):
        tasks += _games("rollout_vs_ab", "gomoku9", mcts(1000, rollout=rollout), deeper, GOMOKU_GAMES)
    for it in (100, 500, 2000):
        tasks += _games("final", "gomoku9", mcts(it, final_rule="max_ratio"), mcts(it), GOMOKU_GAMES)
    for formula in VARIANTS:
        for c in C_VALUES:
            tasks += _games("formula", "gomoku9", mcts(1000, c, formula), baseline, GOMOKU_GAMES)
    tasks += _games("radius", "gomoku9", mcts(1000, radius=2), baseline, GOMOKU_GAMES)
    return tasks


def _xiangqi():
    tasks = []
    def cut(iterations, c=1.4, **options):
        return mcts(iterations, c, rollout=options.pop("rollout", "cutoff"), **options)
    reference = cut(500)
    shallow, deeper, deepest = alphabeta(1), alphabeta(2), alphabeta(3)
    for c in C_VALUES:
        for it in ITERATIONS:
            tasks += _games("curve", "xiangqi", cut(it, c), reference, XIANGQI_GAMES)
    for it in (1000, 5000):
        for opponent in (RANDOM, shallow, deeper):
            tasks += _games("wdl", "xiangqi", cut(it), opponent, XIANGQI_GAMES)
    for it in ITERATIONS:
        tasks += _games("ab_ladder", "xiangqi", cut(it), deeper, XIANGQI_GAMES)
    tasks += _games("ab_self", "xiangqi", deeper, RANDOM, XIANGQI_GAMES)
    tasks += _games("ab_self", "xiangqi", deepest, deeper, XIANGQI_GAMES)
    random_base = mcts(500, rollout="random")
    for rollout in ("heuristic", "cutoff"):
        tasks += _games("rollout", "xiangqi", cut(500, rollout=rollout), random_base, XIANGQI_GAMES)
    for rollout in ("random", "heuristic", "cutoff"):
        tasks += _games("rollout_vs_ab", "xiangqi", cut(1000, rollout=rollout), shallow, XIANGQI_GAMES)
    tasks += _games("final", "xiangqi", cut(500, final_rule="max_ratio"), reference, XIANGQI_GAMES)
    for formula in VARIANTS:
        for c in C_VALUES:
            tasks += _games("formula", "xiangqi", cut(500, c, formula=formula), reference, XIANGQI_GAMES)
    return tasks


SUITES = {"ttt3": _ttt3, "gomoku9": _gomoku9, "xiangqi": _xiangqi}


def build_suite(name):
    return SUITES[name]()


def row_key(exp, game, a, b, index):
    return (exp, game, json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True), int(index))


def expected_rows(tasks, path):
    """How many of ``tasks`` are still missing from the results file."""
    done = set()
    path = Path(path)
    if path.exists():
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if valid_game(row):
                    done.add(game_key(row))
    return sum(
        row_key(t["exp"], t["game"], t["a"], t["b"], t["index"]) not in done for t in tasks
    )
