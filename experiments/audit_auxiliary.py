"""Check auxiliary CSV configuration coverage and numeric invariants, without new searches.

    python -m experiments.audit_auxiliary --raw results/source_data/raw
"""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from experiments import bandit, nodes, root_stats, verify_3x3


def audit(raw):
    errors = []

    def rows(name):
        path = raw / f"{name}.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def coverage(name, actual, expected):
        actual = list(actual)
        detail = dict(rows=len(actual), planned=len(expected), matched=len(set(actual) & expected),
                      missing=len(expected - set(actual)), offplan=len(set(actual) - expected),
                      duplicates=len(actual) - len(set(actual)))
        if detail["missing"] or detail["offplan"] or detail["duplicates"]:
            errors.append(f"{name}: incomplete or duplicate identities")
        return detail

    node_rows = nodes.existing_rows(raw / "nodes.csv")
    planned_nodes = list(nodes.entries())
    node_detail = coverage("nodes", node_rows, set(map(nodes.entry_key, planned_nodes)))
    node_detail["status"] = dict(Counter(r["status"] for r in node_rows.values()))
    for entry in planned_nodes:
        row = node_rows.get(nodes.entry_key(entry))
        if row is None:
            continue
        _, factory, _, moves, radius, _, _ = entry
        game = nodes.replay(factory, moves)
        legal = game.candidate_moves(radius) if radius else game.legal_moves()
        if int(row["root_moves"]) != len(legal):
            errors.append(f"nodes: root move count disagrees: {nodes.entry_key(entry)}")
        if row["status"] == "ok":
            best = [tuple(m) if isinstance(m, list) else m for m in json.loads(row["best_moves"])]
            if not best or any(m not in legal for m in best) or not math.isfinite(float(row["value"])):
                errors.append(f"nodes: invalid completed result: {nodes.entry_key(entry)}")

    root = rows("root_stats")
    definitions = {p[0]: p for p in root_stats.positions()}
    groups = defaultdict(list)
    for r in root:
        groups[(r["position"], int(r["iterations"]), int(r["seed"]))].append(r)
    root_detail = coverage("root_stats", groups,
        {(p, it, seed) for p in definitions for it in root_stats.ITERATIONS for seed in root_stats.SEEDS})
    root_detail["child_rows"] = len(root)
    for (position, iterations, seed), group in groups.items():
        _, game_name, factory, moves, rollout = definitions[position]
        game = nodes.replay(factory, moves)
        legal = game.legal_moves()
        identities = [r["move"] for r in group]
        if (len(set(identities)) != len(group) or sum(int(r["N"]) for r in group) != iterations
                or sum(int(r["chosen"]) for r in group) != 1):
            errors.append(f"root_stats: invalid child counts: {position}/{iterations}/{seed}")
        for r in group:
            move = json.loads(r["move"])
            move = tuple(move) if isinstance(move, list) else move
            n, w = int(r["N"]), float(r["W"])
            # Both stored W and the displayed mean/UCT were independently
            # rounded to four decimals: propagate W's error through division.
            tolerance = 0.00005 * (1 + 1 / max(n, 1)) + 1e-12
            if (move not in legal or r["game"] != game_name or r["rollout"] != rollout
                    or float(r["c"]) != root_stats.C or n < 1 or not 0 <= w <= n
                    or int(r["chosen"]) not in (0, 1)
                    or any(not math.isfinite(float(r[k])) for k in ("W_over_N", "UCT"))
                    or abs(w / n - float(r["W_over_N"])) > tolerance
                    or abs(w / n + root_stats.C * math.sqrt(math.log(iterations) / n)
                           - float(r["UCT"])) > tolerance):
                errors.append(f"root_stats: invalid child result: {position}/{iterations}/{seed}")

    quality = rows("verify_quality")
    quality_detail = coverage("verify_quality", ((int(r["iterations"]), int(r["seed"])) for r in quality),
        {(it, seed) for it in verify_3x3.TTT_ITERATIONS for seed in range(verify_3x3.QUALITY_SEEDS)})
    positions = len(verify_3x3.reachable_positions())
    quality_detail["positions_per_run"] = positions
    if any(int(r["positions"]) != positions or not 0 <= int(r["blunders"]) <= positions for r in quality):
        errors.append("verify_quality: invalid position or blunder count")

    exhaustive = rows("verify_exhaustive")
    exhaustive_detail = coverage("verify_exhaustive",
        ((int(r["iterations"]), int(r["role"]), int(r["seed"])) for r in exhaustive),
        {(it, role, seed) for it in verify_3x3.EXHAUSTIVE_ITERATIONS for role in (1, -1)
         for seed in range(verify_3x3.EXHAUSTIVE_SEEDS)})
    if any(int(r["lines"]) < 1 or any(int(r[k]) < 0 for k in ("wins", "draws", "losses"))
           or sum(int(r[k]) for k in ("wins", "draws", "losses")) != int(r["lines"])
           for r in exhaustive):
        errors.append("verify_exhaustive: inconsistent outcome counts")

    controls = rows("bandit")
    bandit_detail = coverage("bandit",
        ((r["setting"], r["strategy"], r["c"], int(r["step"])) for r in controls),
        {(s, strategy, "" if c is None else str(c), step)
         for s, arms in bandit.SETTINGS.items() for strategy, c in bandit.RUNS
         for step in bandit.record_steps(bandit.HORIZON, len(arms))})
    bandit_detail["runs"] = len({(r["setting"], r["strategy"], r["c"]) for r in controls})
    bandit_detail["seeds_per_run"] = bandit.SEEDS
    for r in controls:
        if (int(r["seeds"]) != bandit.SEEDS
                or r["arms"] != " ".join(map(str, bandit.SETTINGS[r["setting"]]))
                or r["epsilon"] != (str(bandit.EPSILON) if r["strategy"] == "epsilon_greedy" else "")
                or any(not math.isfinite(float(r[k])) or float(r[k]) < 0 for k in
                       ("mean_regret", "ci95", "median_regret", "p95_regret", "max_regret"))
                or not 0 <= float(r["wrong_arm_share"]) <= 1):
            errors.append("bandit: invalid parameters or numeric summary")
    return dict(nodes=node_detail, root_stats=root_detail, verify_quality=quality_detail,
                verify_exhaustive=exhaustive_detail, bandit=bandit_detail, errors=errors,
                note="Coverage and stored numeric invariants; not a rerun of every seeded search. "
                     "Explicit node skips/timeouts are retained and do not become successful searches.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("results/source_data/raw"))
    parser.add_argument("--out", type=Path, default=Path("results/auxiliary_integrity.json"))
    args = parser.parse_args()
    result = audit(args.raw)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
