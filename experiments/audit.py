"""Replay frozen match logs and count exact planned identities, without generating data.

    python -m experiments.audit --raw results/source_data/raw --out results/integrity.json
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from experiments.data import game_key, valid_game
from experiments.plan import SUITES, build_suite, row_key
from experiments.runner import GAME_FACTORIES


def audit(raw):
    from experiments.runner import match_seed

    result = {}
    for suite in SUITES:
        path = raw / f"{suite}.csv"
        rows = list(csv.DictReader(path.open(encoding="utf-8", newline=""))) if path.exists() else []
        expected = {row_key(t["exp"], t["game"], t["a"], t["b"], t["index"])
                    for t in build_suite(suite)}
        valid = [r for r in rows if valid_game(r)]
        keys, errors = [game_key(r) for r in valid], Counter()
        for row in valid:
            if int(row["seed"]) != match_seed(row["exp"], row["game"], json.loads(row["a"]),
                                             json.loads(row["b"]), int(row["index"])):
                errors["seed_mismatch"] += 1
            game = GAME_FACTORIES[suite]()
            for move in json.loads(row["moves"]):
                if game.winner() is not None:
                    errors["moves_after_terminal"] += 1
                    break
                move = tuple(move) if isinstance(move, list) else move
                if move not in game.legal_moves():
                    errors["illegal_move"] += 1
                    break
                game.play(move)
            else:
                winner = game.winner()
                if winner is None:
                    errors["unfinished_game"] += 1
                else:
                    score = (winner + 1) / 2 if int(row["a_first"]) else (1 - winner) / 2
                    if score != float(row["a_score"]):
                        errors["score_mismatch"] += 1
        by_exp = {}
        for exp in sorted({k[0] for k in expected} | {r["exp"] for r in valid}):
            planned, have = {k for k in expected if k[0] == exp}, {k for k in keys if k[0] == exp}
            by_exp[exp] = dict(planned=len(planned), matched=len(planned & have),
                               missing=len(planned - have), supplementary=len(have - planned))
        groups = defaultdict(list)
        for row in valid:
            groups[game_key(row)[:4]].append(row)
        result[suite] = dict(rows=len(rows), valid=len(valid), duplicates=len(keys) - len(set(keys)),
                             planned=len(expected), matched=len(set(keys) & expected),
                             offplan=len(set(keys) - expected), errors=dict(errors), exp=by_exp,
                             pairings=len(groups), pairings_50plus=sum(len(g) >= 50 for g in groups.values()),
                             pairings_balanced=sum(sum(int(r["a_first"]) for r in g) * 2 == len(g)
                                                   for g in groups.values()),
                             agent_hours=sum(float(r["a_time"]) + float(r["b_time"]) for r in valid) / 3600)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("results/source_data/raw"))
    parser.add_argument("--out", type=Path, default=Path("results/integrity.json"))
    args = parser.parse_args()
    result = audit(args.raw)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for suite, values in result.items():
        print(f"{suite}: {values['matched']}/{values['planned']} planned, "
              f"{values['offplan']} supplementary, errors={values['errors']}", flush=True)
    if any(v["errors"] or v["valid"] != v["rows"] or v["duplicates"] for v in result.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
