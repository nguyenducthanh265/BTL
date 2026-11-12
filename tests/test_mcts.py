"""MCTS mechanics, the UCT arithmetic from the assignment, and the rollout policies."""
import random

import pytest

from gameai.games.tictactoe import TicTacToe
from gameai.search.mcts import FORMULAS, MCTS, Node, final_move


def position(moves, size=3, k=3):
    game = TicTacToe(size, k)
    for move in moves:
        game.play(move)
    return game


def scored(w, n, parent_n, c, name="ucb1"):
    import math

    node = Node(None, None, [], 1, 0.0)
    node.w, node.n, node.w2 = w, n, w
    return FORMULAS[name](node, parent_n, math.log(parent_n), c)


def test_uct_values_from_the_assignment_example():
    assert scored(7, 10, 21, 1.41) == pytest.approx(0.7 + 1.41 * (3.0445 / 10) ** 0.5, abs=1e-3)
    assert scored(7, 10, 21, 1.41) == pytest.approx(1.478, abs=1e-3)
    assert scored(0, 1, 21, 1.41) == pytest.approx(2.460, abs=1e-3)
    # The under-explored move outranks the good one, as the assignment explains.
    assert scored(0, 1, 21, 1.41) > scored(7, 10, 21, 1.41)


@pytest.mark.parametrize("name", sorted(FORMULAS))
def test_every_formula_grows_for_a_neglected_child(name):
    # Exploration: score rises with the parent's visits while the child is ignored.
    assert scored(1, 2, 1000, 1.4, name) > scored(1, 2, 10, 1.4, name)


@pytest.mark.parametrize("name", sorted(FORMULAS))
def test_every_formula_shrinks_the_bonus_as_a_child_is_visited(name):
    # Same win rate, more visits: less exploration bonus.
    assert scored(5, 10, 100, 1.4, name) < scored(1, 2, 100, 1.4, name)


def test_root_visits_equal_iterations():
    root = MCTS(iterations=500, rng=random.Random(1)).search(TicTacToe(3, 3))
    assert root.n == 500
    assert sum(child.n for child in root.children) == 500


def test_every_move_is_tried_before_any_is_repeated():
    root = MCTS(iterations=9, rng=random.Random(1)).search(TicTacToe(3, 3))
    assert sorted(child.move for child in root.children) == list(range(9))
    assert all(child.n == 1 for child in root.children)


def test_visits_of_children_add_up_at_every_expanded_node():
    root = MCTS(iterations=2000, rng=random.Random(2)).search(TicTacToe(3, 3))
    stack = [root]
    while stack:
        node = stack.pop()
        if node.children:
            # The node's first visit is its own rollout, the rest went to children.
            assert sum(child.n for child in node.children) == node.n - (node is not root)
            stack.extend(node.children)


def test_wins_are_counted_for_the_player_who_moved_into_the_node():
    # X plays 2 and wins at once: that child is a certain win for X.
    game = position([0, 3, 1, 4])
    root = MCTS(iterations=300, rng=random.Random(3)).search(game)
    winning = next(child for child in root.children if child.move == 2)
    assert winning.w == winning.n


def test_same_seed_gives_the_same_tree():
    stats = []
    for _ in range(2):
        root = MCTS(iterations=300, rng=random.Random(7)).search(TicTacToe(3, 3))
        stats.append(sorted((c.move, c.n, c.w) for c in root.children))
    assert stats[0] == stats[1]


def test_search_does_not_change_the_given_position():
    game = position([0, 4])
    before = game.key()
    MCTS(iterations=100, rng=random.Random(1)).search(game)
    assert game.key() == before


def test_mcts_blocks_the_position_from_the_assignment():
    game = position([1, 0, 6, 4])
    for seed in range(10):
        assert MCTS(iterations=2000, rng=random.Random(seed)).best_move(game) == 8


def test_mcts_takes_a_win_on_the_big_board():
    game = position([40, 0, 41, 1, 42, 2, 43, 3], size=9, k=5)
    move = MCTS(iterations=3000, radius=2, rng=random.Random(1)).best_move(game)
    assert move in (39, 44)


def test_final_move_rules_differ_on_a_lucky_child():
    # A child tried once and won has the best W/N but no statistical support.
    lucky = Node("lucky", None, [], 1, 0.0)
    lucky.n, lucky.w = 1, 1.0
    solid = Node("solid", None, [], 1, 0.0)
    solid.n, solid.w = 100, 70.0
    assert final_move([lucky, solid], "robust") is solid
    assert final_move([lucky, solid], "max_ratio") is lucky


@pytest.mark.parametrize("name", sorted(FORMULAS))
def test_every_formula_runs_a_full_search(name):
    mcts = MCTS(iterations=200, formula=name, rng=random.Random(1))
    assert mcts.best_move(TicTacToe(3, 3)) in range(9)


def test_radius_restricts_the_tree_to_cells_near_stones():
    game = position([40], size=9, k=5)
    root = MCTS(iterations=200, radius=1, rng=random.Random(1)).search(game)
    assert sorted(c.move for c in root.children) == [30, 31, 32, 39, 41, 48, 49, 50]


def test_unknown_options_are_rejected():
    with pytest.raises(ValueError):
        MCTS(iterations=10, formula="nope")
    with pytest.raises(ValueError):
        MCTS(iterations=0)
    with pytest.raises(ValueError):
        TicTacToe(3, 3).simulate("nope", random.Random(1))


@pytest.mark.parametrize("policy", ["random", "heuristic", "cutoff"])
def test_rollout_reward_is_a_probability(policy):
    rng = random.Random(1)
    for _ in range(50):
        reward = position([40], size=9, k=5).simulate(policy, rng)
        assert 0.0 <= reward <= 1.0


def test_heuristic_rollout_always_takes_an_available_win():
    # X to move with four in a row and an open end.
    rng = random.Random(1)
    for _ in range(50):
        game = position([40, 0, 41, 80, 42, 8, 43, 72], size=9, k=5)
        assert game.simulate("heuristic", rng) == 1.0


def test_heuristic_rollout_uses_the_block_on_the_first_ply():
    # O threatens to complete 0-3 at cell 4 and X is to move with nothing better.
    rng = random.Random(9)
    wins_for_o = 0
    for _ in range(200):
        game = position([80, 0, 70, 1, 60, 2, 50, 3], size=9, k=5)
        wins_for_o += game.simulate("random", rng) == 0.0
    blocked = 0
    for _ in range(200):
        game = position([80, 0, 70, 1, 60, 2, 50, 3], size=9, k=5)
        blocked += game.simulate("heuristic", rng) == 0.0
    assert blocked < wins_for_o


def test_simulating_a_finished_game_returns_its_result():
    game = position([0, 3, 1, 4, 2])
    assert game.simulate("random", random.Random(1)) == 1.0


def test_finite_mcts_budget_can_choose_a_forced_loss():
    """A reproducible counterexample to an unconditional MCTS never-lose claim."""
    from gameai.search.minimax import solve

    game = position([1, 0, 6, 4])
    assert solve(game) == 0
    move = MCTS(iterations=1, rng=random.Random(1)).best_move(game)
    assert move != 8  # the only move preserving the draw
    game.play(move)
    assert solve(game) == -1
