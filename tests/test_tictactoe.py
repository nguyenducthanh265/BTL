"""Rules of the m,n,k game, checked against published game-tree counts."""
import random

import pytest

from gameai.games.tictactoe import TicTacToe


def count_tree(game):
    """Return (nodes, x_wins, o_wins, draws) for the full game tree."""
    result = game.winner()
    if result is not None:
        return (1, int(result == 1), int(result == -1), int(result == 0))
    nodes, x_wins, o_wins, draws = 1, 0, 0, 0
    for move in game.legal_moves():
        game.play(move)
        n, x, o, d = count_tree(game)
        game.undo()
        nodes += n
        x_wins += x
        o_wins += o
        draws += d
    return nodes, x_wins, o_wins, draws


def test_3x3_tree_matches_known_counts():
    # 255,168 distinct games: 131,184 X wins, 77,904 O wins, 46,080 draws.
    nodes, x_wins, o_wins, draws = count_tree(TicTacToe(3, 3))
    assert (x_wins, o_wins, draws) == (131_184, 77_904, 46_080)
    assert nodes == 549_946


def test_x_moves_first_and_turns_alternate():
    game = TicTacToe(3, 3)
    assert game.to_play == 1
    game.play(4)
    assert game.to_play == -1
    assert game.board[4] == 1


def test_undo_restores_position_exactly():
    game = TicTacToe(3, 3)
    game.play(0)
    game.play(4)
    game.undo()
    assert game.board[4] == 0
    assert game.to_play == -1
    assert game.winner() is None
    assert 4 in game.legal_moves()


def test_undo_clears_a_win():
    game = TicTacToe(3, 3)
    for cell in [0, 3, 1, 4, 2]:
        game.play(cell)
    assert game.winner() == 1
    game.undo()
    assert game.winner() is None


def test_five_in_a_row_wins_on_every_direction():
    directions = {
        "horizontal": [40 + i for i in range(5)],
        "vertical": [4 + 9 * i for i in range(5)],
        "diagonal": [i * 10 for i in range(5)],
        "anti_diagonal": [8 + 8 * i for i in range(5)],
    }
    for name, line in directions.items():
        game = TicTacToe(9, 5)
        spare = [c for c in range(81) if c not in line]
        filler = iter(random.Random(0).sample(spare, 4))  # O has too few stones to win
        for i, cell in enumerate(line):
            assert game.winner() is None, name
            game.play(cell)
            if i < 4:
                game.play(next(filler))
        assert game.winner() == 1, name


def test_four_in_a_row_is_not_a_win_with_k5():
    game = TicTacToe(9, 5)
    for cell, reply in zip([0, 1, 2, 3], [80, 70, 60, 50]):
        game.play(cell)
        game.play(reply)
    assert game.winner() is None


def test_line_does_not_wrap_around_the_board_edge():
    game = TicTacToe(9, 5)
    # Cells 7, 8 end row 0 and 9, 10, 11 start row 1: consecutive indices only.
    for move in [7, 40, 8, 50, 9, 60, 10, 70, 11]:
        game.play(move)
    assert game.winner() is None


def test_full_board_without_line_is_a_draw():
    game = TicTacToe(3, 3)
    for cell in [0, 1, 2, 4, 3, 5, 7, 6, 8]:
        game.play(cell)
    assert game.winner() == 0
    assert game.legal_moves() == []


def test_finished_game_has_no_legal_moves():
    game = TicTacToe(3, 3)
    for cell in [0, 3, 1, 4, 2]:
        game.play(cell)
    assert game.legal_moves() == []


def test_clone_is_independent():
    game = TicTacToe(3, 3)
    game.play(0)
    copy = game.clone()
    copy.play(1)
    assert game.board[1] == 0
    assert game.to_play == -1
    assert copy.to_play == 1


def test_candidate_moves_only_returns_cells_close_to_stones():
    game = TicTacToe(9, 5)
    assert game.candidate_moves(radius=1) == [40]  # empty board: centre only
    game.play(40)
    assert sorted(game.candidate_moves(radius=1)) == [30, 31, 32, 39, 41, 48, 49, 50]


def test_threat_cell_finds_the_completing_square():
    game = TicTacToe(9, 5)
    for cell, reply in zip([0, 1, 2, 3], [80, 70, 60, 50]):
        game.play(cell)
        game.play(reply)
    # X holds cells 0-3; cell 4 completes five. X's newest stone is cell 3.
    assert game.threat_cell(3) == 4


def test_threat_cell_returns_none_without_a_threat():
    game = TicTacToe(9, 5)
    game.play(40)
    assert game.threat_cell(40) is None


def test_four_in_a_row_heuristic_supports_general_k():
    game = TicTacToe(4, 4)
    game.play(5)
    assert game.evaluate() > 0


@pytest.mark.parametrize("size,k", [(0, 3), (3, 0), (3, 4), (3.5, 3), (1000, 3)])
def test_invalid_geometry_is_rejected(size, k):
    with pytest.raises(ValueError):
        TicTacToe(size, k)


def test_single_cell_game_has_a_finite_move_prior():
    game = TicTacToe(1, 1)
    assert game.move_prior(0) == 0.0
    game.play(0)
    assert game.winner() == 1


def test_match_counts_both_seats_separately_with_one_agent_instance():
    from gameai.match import play_game

    class FirstAvailable:
        nodes = 1

        def choose(self, game, rng):
            return game.legal_moves()[0]

    agent = FirstAvailable()
    result = play_game(TicTacToe(), agent, agent, random.Random(1))
    assert result["plies"] == 7
    assert result["first_nodes"] == 4
    assert result["second_nodes"] == 3


@pytest.mark.parametrize("sign", [1, -1])
def test_generalized_evaluation_is_strictly_below_the_latest_terminal(sign):
    from gameai.games.tictactoe import WIN_SCORE

    game = TicTacToe(9, 9)
    for line, filler in zip(range(8), (9, 11, 13, 15, 17, 19, 21, 23)):
        pair = (line, filler) if sign == 1 else (filler, line)
        for move in pair:
            game.play(move)
    assert game.winner() is None
    assert game.evaluate() == sign * (WIN_SCORE - 9 * 9 - 1)


@pytest.mark.parametrize("size,k,centre,expected", [(3, 3, 4, 4), (9, 5, 40, 20)])
def test_normal_3x3_and_five_in_a_row_keep_their_evaluation_scale(size, k, centre, expected):
    game = TicTacToe(size, k)
    game.play(centre)
    assert game.evaluate() == expected
