"""Bernoulli bandit: why the UCT exploration term has a square root and a logarithm.

Regret after T pulls is the sum over pulls of (best mean - mean of the pulled arm). This
is the expected loss of each choice, not the noisy rewards, so it has less noise.

All seeds of one strategy advance together as numpy arrays, one row per seed. Each seed
shuffles the arms, because argmax breaks ties towards the first column. As in MCTS, every
arm is pulled once first and the parent count is the number of pulls made so far.

c = 0.5 is run as well as 1.4 because the three bonus terms have different sizes, so one
fixed c compares their scale as much as their form. wrong_arm_share is the fraction of
seeds whose most-pulled arm is not the best arm: the failure the mean regret can hide.

    python -m experiments.bandit
"""
import csv
import math
import time
from types import SimpleNamespace

import numpy as np

from experiments.runner import RAW_DIR
from gameai.search.selection import FORMULAS

SETTINGS = {
    "easy": (0.9, 0.8, 0.7, 0.5, 0.3),
    "hard": (0.55, 0.50, 0.50, 0.45, 0.40),
    "two_arms": (0.50, 0.48),
}
C = 1.4
EPSILON = 0.1
RUNS = (("ucb1", C), ("no_sqrt", C), ("no_log", C), ("epsilon_greedy", None),
        ("ucb1", 0.5), ("no_sqrt", 0.5))
HORIZON = 100_000
SEEDS = 1000
BASE_SEED = 2024
FIELDS = ["setting", "arms", "strategy", "c", "epsilon", "seeds", "step", "mean_regret", "ci95",
          "median_regret", "p95_regret", "max_regret", "wrong_arm_share"]


def index(strategy, wins, pulls, parent_n, c=C):
    """The numpy form of the formulas in gameai/search/selection.py."""
    mean = wins / pulls
    if strategy == "ucb1":
        return mean + c * np.sqrt(math.log(parent_n) / pulls)
    if strategy == "no_sqrt":
        return mean + c * math.log(parent_n) / pulls
    if strategy == "no_log":
        return mean + c * np.sqrt(parent_n / pulls)
    raise ValueError(f"unknown strategy: {strategy}")


def check_same_formulas():
    """Stop at once if this file and selection.py ever disagree."""
    child = SimpleNamespace(w=3.0, n=7)
    for name in ("ucb1", "no_sqrt", "no_log"):
        here = index(name, np.array([child.w]), np.array([child.n]), 50)[0]
        there = FORMULAS[name](child, 50, math.log(50), C)
        if not math.isclose(here, there):
            raise AssertionError(f"{name}: {here} != {there}")


def record_steps(horizon, arms):
    steps = {int(x) for x in np.geomspace(arms, horizon, 60)} | {1000, 10_000, horizon}
    return {step for step in steps if arms <= step <= horizon}


def simulate(arms, strategy, c=C, seeds=SEEDS, horizon=HORIZON, seed=BASE_SEED):
    """Return {step: (regret of every seed, share of seeds favouring a wrong arm)}."""
    arms = np.asarray(arms)
    rng = np.random.default_rng(seed)
    count = len(arms)
    if count < 1 or seeds < 1 or horizon < count:
        raise ValueError("need at least one seed and arm, and horizon >= arm count")
    order = rng.permuted(np.tile(np.arange(count), (seeds, 1)), axis=1)
    means = arms[order]
    gaps = arms.max() - means
    rows = np.arange(seeds)
    pulls = np.ones((seeds, count))
    wins = (rng.random((seeds, count)) < means).astype(float)
    regret = gaps.sum(axis=1)
    steps = record_steps(horizon, count)
    favourite = pulls.argmax(axis=1)
    recorded = {count: (regret.copy(), float((gaps[rows, favourite] > 0).mean()))}
    for step in range(count + 1, horizon + 1):
        if strategy == "epsilon_greedy":
            choice = (wins / pulls).argmax(axis=1)
            explore = rng.random(seeds) < EPSILON
            choice[explore] = rng.integers(0, count, explore.sum())
        else:
            choice = index(strategy, wins, pulls, step - 1, c).argmax(axis=1)
        wins[rows, choice] += rng.random(seeds) < means[rows, choice]
        pulls[rows, choice] += 1
        regret += gaps[rows, choice]
        if step in steps:
            favourite = pulls.argmax(axis=1)
            recorded[step] = (regret.copy(), float((gaps[rows, favourite] > 0).mean()))
    return recorded


def summary_rows(setting, arms, strategy, c, recorded):
    rows = []
    for step, (regret, wrong) in sorted(recorded.items()):
        rows.append({
            "setting": setting, "arms": " ".join(map(str, arms)), "strategy": strategy,
            "c": "" if c is None else c,
            "epsilon": EPSILON if strategy == "epsilon_greedy" else "",
            "seeds": len(regret), "step": step,
            "mean_regret": round(float(regret.mean()), 3),
            "ci95": round(float(1.96 * regret.std(ddof=1) / math.sqrt(len(regret))), 3),
            "median_regret": round(float(np.median(regret)), 3),
            "p95_regret": round(float(np.percentile(regret, 95)), 3),
            "max_regret": round(float(regret.max()), 3),
            "wrong_arm_share": round(wrong, 4),
        })
    return rows


def main(path=None):
    check_same_formulas()
    path = path or RAW_DIR / "bandit.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    existing = {}
    if path.exists() and path.stat().st_size:
        if not path.read_bytes().endswith(b"\n"):
            raise ValueError(f"bandit.csv has an unterminated record; inspect before resuming: {path}")
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != FIELDS:
                raise ValueError(f"unexpected bandit schema: {path}")
            for row in reader:
                key = (row["setting"], row["strategy"], row["c"], int(row["step"]))
                if key in existing:
                    raise ValueError(f"duplicate bandit checkpoint: {key}")
                existing[key] = row
    planned = {(setting, strategy, "" if c is None else str(c), step)
               for setting, arms in SETTINGS.items() for strategy, c in RUNS
               for step in record_steps(HORIZON, len(arms))}
    if set(existing) - planned:
        raise ValueError("bandit.csv contains an unplanned checkpoint; inspect before resuming")
    for (setting, strategy, c, _), row in existing.items():
        if (int(row["seeds"]) != SEEDS or row["arms"] != " ".join(map(str, SETTINGS[setting]))
                or row["epsilon"] != (str(EPSILON) if strategy == "epsilon_greedy" else "")
                or any(not math.isfinite(float(row[k])) or float(row[k]) < 0 for k in
                       ("mean_regret", "ci95", "median_regret", "p95_regret", "max_regret"))
                or not 0 <= float(row["wrong_arm_share"]) <= 1):
            raise ValueError(f"invalid bandit checkpoint: {row}")
    needs_header = not path.exists() or not path.stat().st_size
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, lineterminator="\n")
        if needs_header:
            writer.writeheader()
        for setting_index, (setting, arms) in enumerate(SETTINGS.items()):
            for run_index, (strategy, c) in enumerate(RUNS):
                prefix = (setting, strategy, "" if c is None else str(c))
                missing = {step for step in record_steps(HORIZON, len(arms))
                           if (*prefix, step) not in existing}
                if not missing:
                    continue
                seed = BASE_SEED + 100 * setting_index + run_index
                # Historical runs omitted only the initial checkpoint. Recompute that
                # exact seeded state without repeating their 100,000-pull simulations.
                horizon = len(arms) if missing == {len(arms)} else HORIZON
                recorded = simulate(arms, strategy, c, seeds=SEEDS, horizon=horizon, seed=seed)
                rows = summary_rows(setting, arms, strategy, c, recorded)
                for row in rows:
                    key = (*prefix, row["step"])
                    if key in existing:
                        expected = {k: str(v) for k, v in row.items()}
                        if existing[key] != expected:
                            raise ValueError(f"seeded replay disagrees with existing checkpoint: {key}")
                rows = [row for row in rows if row["step"] in missing]
                writer.writerows(rows)
                handle.flush()
                last = rows[-1]
                print(f"{time.perf_counter() - start:5.0f}s {setting} {strategy} c={c}: regret at "
                      f"{last['step']} = {last['mean_regret']} +- {last['ci95']}, wrong arm "
                      f"{last['wrong_arm_share']}", flush=True)
    print("RESULT: resumed without replacing existing rows:", path, flush=True)


if __name__ == "__main__":
    main()
