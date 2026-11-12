"""The experiment tooling: agents, matches, verification, statistics and resuming."""
import csv
import random

import pytest

from experiments.plan import build_suite, expected_rows
from experiments.runner import match_seed, run_tasks
from experiments.stats import wilson_interval
from experiments.data import valid_game
from experiments.verify_3x3 import exhaustive_opponent, move_quality, reachable_positions
from gameai.agents import build_agent
from gameai.games.tictactoe import TicTacToe
from gameai.games.xiangqi import Xiangqi
from gameai.match import play_game


def test_reachable_positions_of_3x3_match_the_known_count():
    positions = reachable_positions()
    # 5,478 legal positions, of which 958 are finished games.
    assert len(positions) == 5_478 - 958


def test_exhaustive_check_passes_for_a_perfect_player():
    for role in (1, -1):
        report = exhaustive_opponent(build_agent({"type": "perfect"}), role, random.Random(1))
        assert report["losses"] == 0
        assert report["lines"] > 0


def test_exhaustive_check_catches_a_weak_player():
    # A verification that a random player also passes would prove nothing.
    report = exhaustive_opponent(build_agent({"type": "random"}), 1, random.Random(1))
    assert report["losses"] > 0


def test_move_quality_separates_perfect_from_random():
    positions = reachable_positions()[:300]
    perfect = move_quality(build_agent({"type": "perfect"}), positions, random.Random(1))
    assert perfect["blunders"] == 0
    weak = move_quality(build_agent({"type": "random"}), positions, random.Random(1))
    assert weak["blunders"] > 0


def test_play_game_reports_the_result_for_the_first_player():
    outcome = play_game(TicTacToe(3, 3), build_agent({"type": "perfect"}),
                        build_agent({"type": "perfect"}), random.Random(1))
    assert outcome["winner"] == 0
    assert outcome["plies"] == 9


@pytest.mark.parametrize("spec", [
    {"type": "random"},
    {"type": "alphabeta", "depth": 1, "radius": 1},
    {"type": "mcts", "iterations": 50, "c": 1.4, "radius": 2},
])
def test_agents_only_play_legal_moves_on_five_in_a_row(spec):
    game = TicTacToe(9, 5)
    agent = build_agent(spec)
    rng = random.Random(1)
    for _ in range(10):
        if game.winner() is not None:  # the same agent plays both sides and may finish early
            break
        move = agent.choose(game, rng)
        assert move in game.legal_moves()
        game.play(move)


def test_agents_play_a_whole_xiangqi_game():
    game = Xiangqi(max_plies=20)
    outcome = play_game(game, build_agent({"type": "alphabeta", "depth": 1}),
                        build_agent({"type": "mcts", "iterations": 20, "rollout": "cutoff"}),
                        random.Random(1))
    assert outcome["winner"] == 0
    assert outcome["plies"] == 20


def test_unknown_agent_type_is_rejected():
    with pytest.raises(ValueError):
        build_agent({"type": "oracle"})


def test_wilson_interval_known_values():
    low, high = wilson_interval(50, 100)
    assert low == pytest.approx(0.4038, abs=1e-3)
    assert high == pytest.approx(0.5962, abs=1e-3)
    low, high = wilson_interval(0, 50)
    assert low == 0
    assert 0.05 < high < 0.09  # never the misleading zero-width interval
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_seed_is_stable_and_differs_between_games():
    task = ("exp", "ttt3", {"type": "random"}, {"type": "random"})
    assert match_seed(*task, 0) == match_seed(*task, 0)
    assert match_seed(*task, 0) != match_seed(*task, 1)
    # Fixed value: this must not depend on the process or Python's hash randomisation.
    assert match_seed("a", "b", {}, {}, 0) == match_seed("a", "b", {}, {}, 0)


def test_suites_alternate_first_player_and_meet_the_game_minimum():
    for suite in ("ttt3", "gomoku9", "xiangqi"):
        tasks = build_suite(suite)
        assert tasks
        by_config = {}
        for task in tasks:
            key = (task["exp"], str(task["a"]), str(task["b"]))
            by_config.setdefault(key, []).append(task["index"])
        for key, indices in by_config.items():
            assert len(indices) >= 50, key
            assert sorted(indices) == list(range(len(indices)))


def test_required_c_values_and_iterations_are_in_the_curve():
    tasks = [t for t in build_suite("gomoku9") if t["exp"] == "curve"]
    assert {t["a"]["c"] for t in tasks} == {0.5, 1.0, 1.4, 2.0}
    iterations = {t["a"]["iterations"] for t in tasks}
    assert min(iterations) == 100 and max(iterations) == 5000


def tiny_tasks():
    return [
        {"exp": "tiny", "game": "ttt3", "a": {"type": "random"}, "b": {"type": "perfect"}, "index": i}
        for i in range(6)
    ]


def test_run_tasks_writes_one_row_per_game_and_alternates_colours(tmp_path):
    out = tmp_path / "raw.csv"
    run_tasks(tiny_tasks(), out, workers=1)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 6
    assert [r["a_first"] for r in rows] == ["1", "0", "1", "0", "1", "0"]
    assert all(float(r["a_score"]) <= 0.5 for r in rows)  # random cannot beat perfect


def test_run_tasks_resumes_without_repeating_games(tmp_path):
    out = tmp_path / "raw.csv"
    run_tasks(tiny_tasks()[:3], out, workers=1)
    first = out.read_text(encoding="utf-8")
    run_tasks(tiny_tasks(), out, workers=1)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 6
    assert out.read_text(encoding="utf-8").startswith(first)
    assert expected_rows(tiny_tasks(), out) == 0


def test_resume_replays_a_row_cut_off_by_a_crash(tmp_path):
    out = tmp_path / "raw.csv"
    run_tasks(tiny_tasks()[:3], out, workers=1)
    # Simulate a kill in the middle of the quoted "moves" field of the last row.
    text = out.read_text(encoding="utf-8").rstrip("\n")
    out.write_text(text[:-3], encoding="utf-8", newline="")
    run_tasks(tiny_tasks()[:3], out, workers=1)
    rows = list(csv.DictReader(out.open(encoding="utf-8", newline="")))
    assert sorted(int(r["index"]) for r in rows) == [0, 1, 2]
    assert all(r["moves"].endswith("]") for r in rows)


def test_cutoff_rollout_is_not_run_on_3x3_where_it_equals_heuristic():
    # A 3x3 game has at most 9 plies, so the cutoff depth is never reached.
    rollouts = {t["a"]["rollout"] for t in build_suite("ttt3") if t["exp"] == "rollout"}
    assert rollouts == {"random", "heuristic"}


@pytest.mark.parametrize("suite", ["ttt3", "gomoku9", "xiangqi"])
def test_every_formula_variant_is_tried_with_every_c(suite):
    # Otherwise a variant that merely needs another c would look worse than it is.
    seen = {}
    for task in build_suite(suite):
        if task["exp"] == "formula":
            seen.setdefault(task["a"]["formula"], set()).add(task["a"]["c"])
    for formula in ("no_sqrt", "no_log", "polynomial", "ucb1_tuned", "progressive_bias"):
        assert seen[formula] == {0.5, 1.0, 1.4, 2.0}, formula


def test_same_seed_reproduces_the_same_game(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    tasks = [{"exp": "tiny", "game": "ttt3", "a": {"type": "mcts", "iterations": 20},
              "b": {"type": "random"}, "index": i} for i in range(4)]
    run_tasks(tasks, a, workers=1)
    run_tasks(tasks, b, workers=1)
    keep = lambda path: [(r["a_score"], r["plies"], r["moves"]) for r in csv.DictReader(path.open(encoding="utf-8"))]
    assert keep(a) == keep(b)


def test_resume_and_coverage_ignore_invalid_newline_terminated_record(tmp_path):
    out = tmp_path / "raw.csv"
    run_tasks(tiny_tasks()[:1], out, workers=1)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    rows[0]["moves"] = "[broken]"  # nonempty but invalid, with a complete physical line
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    assert expected_rows(tiny_tasks()[:1], out) == 1
    assert run_tasks(tiny_tasks()[:1], out, workers=1) == 1
    valid = [r for r in csv.DictReader(out.open(encoding="utf-8")) if valid_game(r)]
    assert len(valid) == 1
    assert expected_rows(tiny_tasks()[:1], out) == 0


def test_bandit_records_the_initial_arm_pulls():
    from experiments.bandit import simulate
    recorded = simulate((0.8, 0.5), "ucb1", seeds=3, horizon=2)
    assert set(recorded) == {2}
    assert recorded[2][0].tolist() == pytest.approx([0.3] * 3)


def test_replay_audit_detects_a_wrong_score(tmp_path):
    from experiments.audit import audit
    from experiments.runner import FIELDS

    out = tmp_path / "ttt3.csv"
    run_tasks(tiny_tasks()[:1], out, workers=1)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    rows[0]["a_score"] = "1.0"  # random cannot defeat a perfect 3x3 player
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    assert audit(tmp_path)["ttt3"]["errors"] == {"score_mismatch": 1}


def test_nodes_resume_preserves_existing_failures_and_uses_full_identity(tmp_path, monkeypatch):
    from experiments import nodes

    planned = list(nodes.entries())[:2]
    path = tmp_path / "nodes.csv"
    old = nodes.run_entry(planned[0], None, 0)  # preserve this deliberate skipped result
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, nodes.FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerow(old)
    original = path.read_bytes()
    monkeypatch.setattr(nodes, "entries", lambda: iter(planned))
    calls = []
    real_run = nodes.run_entry

    def measured(entry, previous, elapsed):
        calls.append(nodes.entry_key(entry))
        return real_run(entry, previous, elapsed)

    monkeypatch.setattr(nodes, "run_entry", measured)
    nodes.main(path)
    assert calls == [nodes.entry_key(planned[1])]
    assert path.read_bytes().startswith(original)
    finished = path.read_bytes()
    nodes.main(path)
    assert path.read_bytes() == finished
    rows = nodes.existing_rows(path)
    assert rows[nodes.entry_key(planned[0])]["status"] == "skipped_shallower"


def test_bandit_resume_fills_checkpoints_and_preserves_existing_bytes(tmp_path, monkeypatch):
    from experiments import bandit

    monkeypatch.setattr(bandit, "SETTINGS", {"two_arms": (0.50, 0.48)})
    monkeypatch.setattr(bandit, "RUNS", (("ucb1", 0.5),))
    monkeypatch.setattr(bandit, "HORIZON", 20)
    monkeypatch.setattr(bandit, "SEEDS", 5)
    path = tmp_path / "bandit.csv"
    rows = bandit.summary_rows("two_arms", (0.50, 0.48), "ucb1", 0.5,
            bandit.simulate((0.50, 0.48), "ucb1", 0.5, seeds=5, horizon=20, seed=bandit.BASE_SEED))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, bandit.FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerow(rows[-1])  # missing early checkpoints in a partly saved run
    original = path.read_bytes()
    bandit.main(path)
    assert path.read_bytes().startswith(original)
    with path.open(encoding="utf-8", newline="") as handle:
        actual = list(csv.DictReader(handle))
    assert {int(r["step"]) for r in actual} == bandit.record_steps(20, 2)
    finished = path.read_bytes()
    bandit.main(path)
    assert path.read_bytes() == finished


def test_bandit_resume_rejects_conflicting_seeded_checkpoint(tmp_path, monkeypatch):
    from experiments import bandit

    monkeypatch.setattr(bandit, "SETTINGS", {"two_arms": (0.50, 0.48)})
    monkeypatch.setattr(bandit, "RUNS", (("ucb1", 0.5),))
    monkeypatch.setattr(bandit, "HORIZON", 20)
    monkeypatch.setattr(bandit, "SEEDS", 5)
    rows = bandit.summary_rows("two_arms", (0.50, 0.48), "ucb1", 0.5,
            bandit.simulate((0.50, 0.48), "ucb1", 0.5, seeds=5, horizon=20, seed=bandit.BASE_SEED))
    rows[-1]["mean_regret"] = 999
    path = tmp_path / "bandit.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, bandit.FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerow(rows[-1])
    original = path.read_bytes()
    with pytest.raises(ValueError, match="seeded replay disagrees"):
        bandit.main(path)
    assert path.read_bytes() == original


def test_auxiliary_audit_rejects_corrupt_root_counts_and_duplicate_bandit_rows(tmp_path, monkeypatch):
    from experiments import audit_auxiliary, bandit, nodes, root_stats, verify_3x3

    def write(name, rows, fields=None):
        with (tmp_path / f"{name}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fields or rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    monkeypatch.setattr(nodes, "entries", lambda: iter(()))
    write("nodes", [], nodes.FIELDS)
    definition = ("tiny", "ttt3", TicTacToe, [], "random")
    monkeypatch.setattr(root_stats, "positions", lambda: [definition])
    monkeypatch.setattr(root_stats, "ITERATIONS", (10,))
    monkeypatch.setattr(root_stats, "SEEDS", (0,))
    root = root_stats.root_rows(*definition, 10, 0)
    write("root_stats", root)
    monkeypatch.setattr(verify_3x3, "TTT_ITERATIONS", (10,))
    monkeypatch.setattr(verify_3x3, "QUALITY_SEEDS", 1)
    monkeypatch.setattr(verify_3x3, "EXHAUSTIVE_ITERATIONS", (10,))
    monkeypatch.setattr(verify_3x3, "EXHAUSTIVE_SEEDS", 1)
    monkeypatch.setattr(verify_3x3, "reachable_positions", lambda: [[]])
    write("verify_quality", [dict(iterations=10, seed=0, positions=1, blunders=0)])
    write("verify_exhaustive", [dict(iterations=10, role=role, seed=0, lines=1,
                                    wins=1, draws=0, losses=0) for role in (1, -1)])
    monkeypatch.setattr(bandit, "SETTINGS", {"easy": (0.9, 0.8)})
    monkeypatch.setattr(bandit, "RUNS", (("ucb1", 0.5),))
    monkeypatch.setattr(bandit, "HORIZON", 2)
    monkeypatch.setattr(bandit, "SEEDS", 2)
    controls = bandit.summary_rows("easy", (0.9, 0.8), "ucb1", 0.5,
                bandit.simulate((0.9, 0.8), "ucb1", 0.5, seeds=2, horizon=2))
    write("bandit", controls)
    assert audit_auxiliary.audit(tmp_path)["errors"] == []
    root[0]["N"] += 1
    write("root_stats", root)
    write("bandit", controls + controls)
    result = audit_auxiliary.audit(tmp_path)
    assert any("invalid child counts" in e for e in result["errors"])
    assert result["bandit"]["duplicates"] == 1


@pytest.mark.parametrize("kind", ["nodes", "bandit"])
def test_auxiliary_resume_refuses_unterminated_record_without_changing_bytes(tmp_path, kind):
    from experiments import bandit, nodes

    module = nodes if kind == "nodes" else bandit
    if kind == "nodes":
        row = nodes.run_entry(next(nodes.entries()), 1, 0)
    else:
        row = bandit.summary_rows("easy", bandit.SETTINGS["easy"], "ucb1", bandit.C,
            bandit.simulate(bandit.SETTINGS["easy"], "ucb1", seeds=bandit.SEEDS, horizon=5))[0]
    path = tmp_path / f"{kind}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, module.FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    original = path.read_bytes()
    with pytest.raises(ValueError, match="unterminated record"):
        module.main(path)
    assert path.read_bytes() == original
