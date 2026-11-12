"""The report must read the data correctly and must never invent numbers."""
import csv
import json

from experiments.plan import RANDOM, mcts
from experiments.report import NS, BETTER, build
from experiments.runner import FIELDS
from experiments.stats import wilson_interval

MCTS_1000 = mcts(1000)


def game_row(exp, game, a, b, index, score, plies=9):
    return {"exp": exp, "game": game, "a": json.dumps(a, sort_keys=True),
            "b": json.dumps(b, sort_keys=True), "index": index, "a_first": int(index % 2 == 0),
            "a_score": score, "plies": plies, "a_time": 0.5, "b_time": 0.1, "a_nodes": 10,
            "b_nodes": 0, "seed": index, "moves": json.dumps(list(range(plies)))}


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def wdl_rows(scores, exp="wdl", game="ttt3", a=MCTS_1000, b=RANDOM):
    return [game_row(exp, game, a, b, i, score) for i, score in enumerate(scores)]


def run(tmp_path, files):
    raw, out = tmp_path / "raw", tmp_path / "out"
    raw.mkdir(exist_ok=True)
    for name, rows in files.items():
        write_csv(raw / name, rows, FIELDS if name == "ttt3.csv" else None)
    build(raw, out)
    return out


def table_row(out, name, *needles):
    """The one row of a markdown table that contains every needle."""
    text = (out / "tables" / f"{name}.md").read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if all(needle in line for needle in needles)]
    assert len(rows) == 1, rows
    return [cell.strip() for cell in rows[0].strip("|").split("|")]


def test_wilson_bounds_appear_in_the_table_and_the_tex(tmp_path):
    out = run(tmp_path, {"ttt3.csv": wdl_rows([1.0] * 150 + [0.5] * 20 + [0.0] * 30)})
    low, high = wilson_interval(150 + 0.5 * 20, 200)
    expected = f"[{low:.3f}, {high:.3f}]"
    row = table_row(out, "wdl_ttt3", "Random")
    assert expected in row
    assert "0.800" in row
    assert BETTER in row
    assert expected in (out / "tables" / "wdl_ttt3.tex").read_text(encoding="utf-8")


def test_interval_containing_half_is_flagged(tmp_path):
    out = run(tmp_path, {"ttt3.csv": wdl_rows([1.0] * 52 + [0.0] * 48)})
    assert NS in table_row(out, "wdl_ttt3", "Random")


def test_wdl_counts_and_sides_when_a_first_alternates(tmp_path):
    # Even index means a moved first: a wins all of those and loses or draws the others.
    scores = [1.0, 0.0, 1.0, 0.5, 1.0, 0.0, 1.0, 0.5]
    out = run(tmp_path, {"ttt3.csv": wdl_rows(scores)})
    headers = (out / "tables" / "wdl_ttt3.md").read_text(encoding="utf-8").splitlines()[2]
    assert "| W | D | L |" in headers
    row = table_row(out, "wdl_ttt3", "Random")
    assert row[2:6] == ["8/200 (partial)", "4", "2", "2"]
    assert "1.00 / 0.25" in row


def test_missing_files_do_not_crash_and_are_flagged(tmp_path):
    out = run(tmp_path, {})
    summary = (out / "SUMMARY.md").read_text(encoding="utf-8")
    assert "MISSING" in summary
    for name in ("wdl_ttt3", "nodes_xiangqi", "verify_exhaustive", "bandit_regret", "root_stats"):
        assert f"**MISSING** `{name}`" in summary
    assert not list((out / "tables").iterdir())
    assert not list((out / "figures").iterdir())


def test_nothing_is_produced_for_a_missing_experiment(tmp_path):
    out = run(tmp_path, {"ttt3.csv": wdl_rows([1.0] * 200)})
    assert (out / "tables" / "wdl_ttt3.md").exists()
    assert not (out / "tables" / "rollout_ttt3.md").exists()
    assert not (out / "figures" / "curve_ttt3.png").exists()
    summary = (out / "SUMMARY.md").read_text(encoding="utf-8")
    assert "**MISSING** `rollout_ttt3`" in summary


def test_planned_pairing_without_games_says_no_data(tmp_path):
    out = run(tmp_path, {"ttt3.csv": wdl_rows([1.0] * 200)})
    assert "no data" in table_row(out, "wdl_ttt3", "Perfect")
    assert "**PARTIAL** `tables/wdl_ttt3`" in (out / "SUMMARY.md").read_text(encoding="utf-8")


def test_broken_and_repeated_rows_are_not_counted(tmp_path):
    rows = wdl_rows([1.0, 0.0])
    rows.append(rows[0])  # the same game written twice
    rows.append({**game_row("wdl", "ttt3", MCTS_1000, RANDOM, 2, 1.0), "moves": ""})  # cut short
    out = run(tmp_path, {"ttt3.csv": rows})
    assert table_row(out, "wdl_ttt3", "Random")[2:6] == ["2/200 (partial)", "1", "0", "1"]
    assert "1 unusable rows" in (out / "SUMMARY.md").read_text(encoding="utf-8")


def test_curve_leaves_a_gap_instead_of_interpolating(tmp_path):
    rows = []
    for iterations in (10, 50):  # 25 lies between them and has no games
        rows += wdl_rows([1.0] * 200, "curve", "ttt3", mcts(iterations, 1.4))
    out = run(tmp_path, {"ttt3.csv": rows})
    assert "no data" in table_row(out, "curve_ttt3", "| 25 |")
    assert (out / "figures" / "curve_ttt3.png").exists()
    assert (out / "figures" / "curve_ttt3.pdf").exists()


def test_verify_quality_rate_and_interval(tmp_path):
    rows = [{"iterations": 50, "seed": seed, "positions": 100, "blunders": 5} for seed in range(3)]
    out = run(tmp_path, {"verify_quality.csv": rows})
    low, high = wilson_interval(15, 300)
    row = table_row(out, "verify_quality", "| 50 |")
    assert row[1:5] == ["3", "300", "15", "0.0500"]
    assert row[5] == f"[{low:.3f}, {high:.3f}]"
    assert row[6] == "n/a"  # not every reachable position was tested


def test_rule_of_three_only_when_there_are_no_losses(tmp_path):
    rows = [{"iterations": it, "role": role, "seed": 0, "lines": 100, "wins": 20,
             "draws": 80 - losses, "losses": losses}
            for it, losses in ((500, 0), (50, 3)) for role in (1, -1)]
    out = run(tmp_path, {"verify_exhaustive.csv": rows})
    clean = table_row(out, "verify_exhaustive", "| 500 |")
    assert clean[-2:] == [f"{3 / 200:.5f}", f"{3 / 2:.4f}"]
    assert table_row(out, "verify_exhaustive", "| 50 |")[-2:] == ["losses observed"] * 2
    assert "evidence, not proof" in (out / "SUMMARY.md").read_text(encoding="utf-8")


def test_skipped_nodes_are_shown_and_ratios_use_common_positions(tmp_path):
    def nodes_row(position, algorithm, nodes):
        return {"game": "gomoku9", "position": position, "radius": 1, "depth": 4,
                "algorithm": algorithm, "status": "ok" if nodes else "skipped_node_limit",
                "nodes": nodes or "", "wall_s": 1.0 if nodes else "", "value": 0, "best_moves": "[1]"}
    rows = [nodes_row("p1", "minimax", 1000), nodes_row("p1", "alphabeta", 100),
            nodes_row("p1", "alphabeta_ordered", 50), nodes_row("p2", "minimax", None),
            nodes_row("p2", "alphabeta", 900), nodes_row("p2", "alphabeta_ordered", 300)]
    out = run(tmp_path, {"nodes.csv": rows})
    row = table_row(out, "nodes_gomoku9", "| 4 |")
    assert row[3] == "1,000 (skipped 1/2)"  # the skipped position is not averaged in
    assert row[6] == "10.0"  # 1000/100: position p2 cannot be compared
    assert (out / "SUMMARY.md").read_text(encoding="utf-8").count("**PARTIAL** `tables/nodes_gomoku9`") == 1


def test_equivalent_json_is_deduplicated_and_bad_record_is_rejected(tmp_path):
    rows = wdl_rows([1.0, 0.0])
    rows.append({**rows[0], "a": json.dumps(MCTS_1000, separators=(",", ":"))})
    rows.append({**game_row("wdl", "ttt3", MCTS_1000, RANDOM, 2, 1.0), "moves": "[bad]"})
    rows.append({**game_row("wdl", "ttt3", MCTS_1000, RANDOM, 3, 1.0), "a_first": 1})
    out = run(tmp_path, {"ttt3.csv": rows})
    assert table_row(out, "wdl_ttt3", "Random")[2:6] == ["2/200 (partial)", "1", "0", "1"]
    assert "2 unusable rows" in (out / "SUMMARY.md").read_text(encoding="utf-8")


def test_missing_node_rows_are_partial_even_if_all_present_searches_finished(tmp_path):
    row = {"game": "ttt3", "position": "empty", "radius": "", "depth": "full",
           "algorithm": "minimax", "status": "ok", "nodes": 100,
           "wall_s": 0.1, "value": 0, "best_moves": "[0]"}
    out = run(tmp_path, {"nodes.csv": [row]})
    summary = (out / "SUMMARY.md").read_text(encoding="utf-8")
    assert "**PARTIAL** `tables/nodes_ttt3`" in summary
    assert "8 planned searches have no CSV row" in summary


def test_root_requires_all_iteration_seed_groups(tmp_path):
    rows = [{"position": position, "game": "ttt3", "rollout": "random", "iterations": 100,
             "c": 1.4, "seed": 0, "move": "8", "N": 100, "W": 50, "W_over_N": .5,
             "UCT": .8, "chosen": 1}
            for position in ("assignment", "empty_3x3", "midgame_12", "xiangqi_start")]
    out = run(tmp_path, {"root_stats.csv": rows})
    summary = (out / "SUMMARY.md").read_text(encoding="utf-8")
    assert "**PARTIAL** `tables/root_stats`" in summary
    assert "Missing planned position/iteration/seed searches: 56" in summary


def test_cap_reached_does_not_imply_the_game_was_drawn(tmp_path):
    rows = wdl_rows([1.0, 0.5], game="xiangqi", a=mcts(100, rollout="cutoff"))
    for row in rows:
        row.update(plies=200, moves=json.dumps([[0, 1]] * 200))
    out = run(tmp_path, {"xiangqi.csv": rows})
    summary = (out / "SUMMARY.md").read_text(encoding="utf-8")
    assert "2 of 2 games reached 200 plies; 1 of those ended as draws" in summary
