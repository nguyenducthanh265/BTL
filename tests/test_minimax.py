"""Minimax and Alpha-Beta must agree on values; pruning may only reduce the node count."""
import random

import pytest

from gameai.games.tictactoe import TicTacToe, WIN_SCORE
from gameai.search.minimax import optimal_moves, search, solve


def position(moves, size=3, k=3):
    game = TicTacToe(size, k)
    for move in moves:
        game.play(move)
    return game


def random_positions(size, k, count, seed, max_plies):
    rng = random.Random(seed)
    positions = []
    while len(positions) < count:
        game = TicTacToe(size, k)
        for _ in range(rng.randint(0, max_plies)):
            moves = game.legal_moves()
            if not moves:
                break
            game.play(rng.choice(moves))
        if game.winner() is None:
            positions.append(game)
    return positions


def test_plain_minimax_visits_the_whole_3x3_tree():
    result = search(TicTacToe(3, 3), depth=None, pruning=False)
    assert result.nodes == 549_946
    assert result.value == 0  # perfect play is a draw


def test_alpha_beta_prunes_most_of_the_3x3_tree_and_keeps_the_value():
    result = search(TicTacToe(3, 3), depth=None, pruning=True)
    assert result.value == 0
    assert result.nodes < 549_946 / 10


def test_alpha_beta_matches_minimax_on_random_3x3_positions():
    for game in random_positions(3, 3, 40, seed=1, max_plies=6):
        plain = search(game, depth=None, pruning=False)
        pruned = search(game, depth=None, pruning=True)
        assert pruned.value == plain.value, game.key()
        assert pruned.nodes <= plain.nodes


def test_root_ties_are_identical_with_and_without_pruning():
    # Pruned bounds must not be mistaken for exact values at the root.
    for game in random_positions(3, 3, 40, seed=2, max_plies=6):
        plain = search(game, depth=None, pruning=False)
        pruned = search(game, depth=None, pruning=True)
        assert sorted(pruned.best_moves) == sorted(plain.best_moves), game.key()


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_alpha_beta_matches_minimax_on_five_in_a_row(depth):
    for game in random_positions(9, 5, 8, seed=depth, max_plies=12):
        moves = lambda state: state.candidate_moves(1)
        plain = search(game, depth=depth, pruning=False, moves=moves)
        pruned = search(game, depth=depth, pruning=True, moves=moves)
        assert pruned.value == plain.value, game.key()
        assert sorted(pruned.best_moves) == sorted(plain.best_moves), game.key()


def test_move_ordering_keeps_value_and_reduces_nodes_on_average():
    plain_nodes = ordered_nodes = 0
    for game in random_positions(9, 5, 8, seed=3, max_plies=12):
        moves = lambda state: state.candidate_moves(1)
        base = search(game, depth=3, pruning=True, moves=moves, order=False)
        ordered = search(game, depth=3, pruning=True, moves=moves, order=True)
        assert ordered.value == base.value
        plain_nodes += base.nodes
        ordered_nodes += ordered.nodes
    assert ordered_nodes <= plain_nodes


def test_search_takes_a_win_in_one():
    # X holds 0 and 1, cell 2 wins immediately.
    game = position([0, 3, 1, 4])
    result = search(game, depth=None)
    assert result.best_moves == [2]
    assert result.value > WIN_SCORE - 10


def test_search_blocks_the_position_from_the_assignment():
    # O X .
    # . O .
    # X . .   X to move: only cell 8 stops the diagonal.
    game = position([1, 0, 6, 4])
    assert search(game, depth=None).best_moves == [8]


def test_search_prefers_the_faster_win():
    # X can win now on 2 or start a slower win; only the immediate win is best.
    game = position([0, 3, 1, 4, 8, 7])
    result = search(game, depth=None)
    assert result.best_moves == [2]


def test_depth_limit_uses_the_evaluation_function():
    game = TicTacToe(9, 5)
    game.play(40)
    result = search(game, depth=1, moves=lambda state: state.candidate_moves(1))
    assert abs(result.value) < WIN_SCORE
    assert result.nodes == 1 + 8


def test_solve_values_of_known_positions():
    assert solve(TicTacToe(3, 3)) == 0
    assert solve(position([0, 3, 1, 4])) == 1  # X wins next move
    assert solve(position([0, 1, 3])) == 1  # X has a double threat coming


def test_optimal_moves_never_contain_a_blunder():
    game = position([1, 0, 6, 4])
    assert optimal_moves(game) == [8]
    # All first moves of the empty board keep the draw.
    assert sorted(optimal_moves(TicTacToe(3, 3))) == list(range(9))


@pytest.mark.parametrize("pruning", [False, True])
@pytest.mark.parametrize("moves,expected", [([0, 3, 1, 4, 2], WIN_SCORE),
                                           ([0, 1, 2, 4, 3, 5, 7, 6, 8], 0)])
def test_search_terminal_root_has_finite_value_and_no_moves(pruning, moves, expected):
    result = search(position(moves), pruning=pruning)
    assert (result.value, result.best_moves, result.nodes) == (expected, [], 1)


def test_zero_depth_evaluates_root_without_searching():
    game = position([4])
    result = search(game, depth=0)
    assert (result.value, result.best_moves, result.nodes) == (game.evaluate(), [], 1)


@pytest.mark.parametrize("depth", [-1, 1.5])
def test_invalid_depth_is_rejected(depth):
    with pytest.raises(ValueError, match="depth"):
        search(TicTacToe(), depth=depth)


def test_every_3x3_search_choice_preserves_the_exact_value():
    """Exhaustive policy check against an independent tuple-based tablebase.

    Every legal opponent reply is enumerated. All tied root choices from BOTH
    search algorithms must preserve the value, so arbitrary tie breaking is safe
    from the empty board for either colour. Losing states remain losing states.
    """
    from functools import lru_cache

    lines = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
             (2, 5, 8), (0, 4, 8), (2, 4, 6))

    @lru_cache(None)
    def reference(board, player):
        for a, b, c in lines:
            if board[a] and board[a] == board[b] == board[c]:
                return board[a]
        empty = [i for i, piece in enumerate(board) if not piece]
        if not empty:
            return 0
        outcomes = [reference(board[:i] + (player,) + board[i + 1:], -player)
                    for i in empty]
        return max(outcomes) if player == 1 else min(outcomes)

    seen = set()
    game = TicTacToe()

    def visit():
        key = game.key()
        if key in seen:
            return
        seen.add(key)
        board, player = tuple(game.board), game.to_play
        target = reference(board, player)
        assert solve(game, solver_memo) == target
        if game.winner() is not None:
            return
        for pruning in (False, True):
            result = search(game, depth=None, pruning=pruning)
            assert (result.value > 0) - (result.value < 0) == target
            assert result.best_moves
            for move in result.best_moves:
                child = board[:move] + (player,) + board[move + 1:]
                assert reference(child, -player) == target, (key, pruning, move)
        for move in game.legal_moves():
            game.play(move)
            visit()
            game.undo()

    solver_memo = {}
    assert reference((0,) * 9, 1) == 0
    visit()
    assert len(seen) == 5_478


def test_solver_memo_is_not_shared_between_different_win_lengths():
    memo = {}
    assert solve(TicTacToe(3, 3), memo) == 0
    assert solve(TicTacToe(3, 1), memo) == 1


@pytest.mark.parametrize("pruning", [False, True])
def test_generalized_heuristic_cannot_outrank_an_immediate_win(pruning):
    game = position([0, 9, 1, 11, 2, 13, 3, 15, 4, 17, 5, 19, 6, 21, 7, 23],
                    size=9, k=9)
    result = search(game, depth=1, pruning=pruning)
    assert result.best_moves == [8]
    assert result.value == WIN_SCORE - 1
