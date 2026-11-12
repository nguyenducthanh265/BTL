"""Xiangqi rules: published perft counts plus one test for each special rule."""
import random

import pytest

from gameai.games.xiangqi import Xiangqi, cell
from gameai.search.mcts import MCTS
from gameai.search.minimax import WIN_SCORE, search


def perft(game, depth):
    if depth == 0:
        return 1
    total = 0
    for move in game.legal_moves():
        game.play(move)
        total += perft(game, depth - 1)
        game.undo()
    return total


def targets(game, row, col):
    origin = cell(row, col)
    return sorted(to for frm, to in game.legal_moves() if frm == origin)


@pytest.mark.parametrize("depth,count", [(1, 44), (2, 1_920), (3, 79_666)])
def test_perft_from_the_start_position(depth, count):
    assert perft(Xiangqi(), depth) == count


@pytest.mark.slow
def test_perft_depth_four():
    assert perft(Xiangqi(), 4) == 3_290_240


def test_red_moves_first():
    assert Xiangqi().to_play == 1


def test_generals_may_not_face_each_other():
    game = Xiangqi("3k5/9/9/9/9/9/9/9/9/4K4 w")
    # Stepping left onto the file of the black general is illegal.
    assert targets(game, 9, 4) == sorted([cell(8, 4), cell(9, 5)])


def test_pinned_piece_may_not_leave_the_line():
    game = Xiangqi("3k5/9/9/9/9/4r4/9/9/4N4/4K4 w")
    assert game.legal_moves() == [(cell(9, 4), cell(9, 5))]


def test_horse_is_blocked_by_its_leg():
    free = Xiangqi("3k5/9/9/9/9/4N4/9/9/9/5K3 w")
    assert len(targets(free, 5, 4)) == 8
    blocked = Xiangqi("3k5/9/9/9/4P4/4N4/9/9/9/5K3 w")
    found = targets(blocked, 5, 4)
    assert len(found) == 6
    assert cell(3, 3) not in found and cell(3, 5) not in found


def test_elephant_stays_home_and_is_blocked_by_its_eye():
    free = Xiangqi("3k5/9/9/9/9/2B6/9/9/9/5K3 w")
    assert targets(free, 5, 2) == sorted([cell(7, 0), cell(7, 4)])
    blocked = Xiangqi("3k5/9/9/9/9/2B6/3P5/9/9/5K3 w")
    assert targets(blocked, 5, 2) == [cell(7, 0)]


def test_advisor_stays_in_the_palace():
    game = Xiangqi("3k5/9/9/9/9/9/9/9/4A4/5K3 w")
    assert targets(game, 8, 4) == sorted(
        [cell(7, 3), cell(7, 5), cell(9, 3)]  # cell(9, 5) holds the general
    )
    corner = Xiangqi("3k5/9/9/9/9/9/9/9/9/3A1K3 w")
    assert targets(corner, 9, 3) == [cell(8, 4)]


def test_general_stays_in_the_palace():
    game = Xiangqi("3k5/9/9/9/9/9/9/9/9/5K3 w")
    assert targets(game, 9, 5) == sorted([cell(8, 5), cell(9, 4)])


def test_chariot_stops_at_the_first_piece():
    game = Xiangqi("3k5/9/9/9/9/9/9/9/R1P6/5K3 w")
    found = targets(game, 8, 0)
    assert cell(8, 1) in found
    assert cell(8, 2) not in found and cell(8, 3) not in found


def test_cannon_moves_like_a_chariot_and_captures_over_one_screen():
    game = Xiangqi("3k5/r8/n8/9/9/P8/9/9/9/C4K3 w")
    found = targets(game, 9, 0)
    assert cell(8, 0) in found and cell(6, 0) in found
    assert cell(5, 0) not in found  # own screen
    assert cell(4, 0) not in found  # no quiet move past the screen
    assert cell(2, 0) in found  # first enemy behind the screen
    assert cell(1, 0) not in found  # second enemy behind it


def test_soldier_gains_sideways_moves_after_the_river():
    home = Xiangqi("3k5/9/9/9/9/9/P8/9/9/5K3 w")
    assert targets(home, 6, 0) == [cell(5, 0)]
    crossed = Xiangqi("3k5/9/9/9/4P4/9/9/9/9/5K3 w")
    assert targets(crossed, 4, 4) == sorted([cell(3, 4), cell(4, 3), cell(4, 5)])


def test_black_soldier_moves_down_the_board():
    game = Xiangqi("3k5/9/9/p8/9/9/9/9/9/5K3 b")
    assert targets(game, 3, 0) == [cell(4, 0)]
    crossed = Xiangqi("3k5/9/9/9/9/4p4/9/9/9/5K3 b")
    assert targets(crossed, 5, 4) == sorted([cell(6, 4), cell(5, 3), cell(5, 5)])


def test_move_must_answer_a_check():
    game = Xiangqi("3k5/9/9/9/9/9/9/9/5r3/4K2R1 w")
    # The chariot on row 8 does not attack e9, so first confirm a real check below.
    assert game.legal_moves()
    checked = Xiangqi("3k5/9/9/9/4r4/9/9/9/9/4K2R1 w")
    for frm, to in checked.legal_moves():
        checked.play((frm, to))
        assert not checked.general_attacked(1)
        checked.undo()


def test_checkmate_ends_the_game_for_the_attacker():
    game = Xiangqi("3k4R/R8/9/9/9/9/9/9/9/5K3 b")
    assert game.legal_moves() == []
    assert game.winner() == 1


def test_stalemate_loses_in_xiangqi():
    game = Xiangqi("3k5/R8/9/9/9/4R4/9/9/9/5K3 b")
    assert not game.general_attacked(-1)
    assert game.legal_moves() == []
    assert game.winner() == 1


def test_threefold_repetition_is_a_draw():
    game = Xiangqi("3k5/r8/9/9/9/9/9/9/8R/5K3 w")
    loop = [
        (cell(8, 8), cell(7, 8)),
        (cell(1, 0), cell(2, 0)),
        (cell(7, 8), cell(8, 8)),
        (cell(2, 0), cell(1, 0)),
    ]
    assert game.winner() is None
    for move in loop * 2:
        assert game.winner() is None
        game.play(move)
    assert game.winner() == 0
    assert game.legal_moves() == []


def test_no_capture_limit_is_a_draw():
    game = Xiangqi("3k5/r8/9/9/9/9/9/9/8R/5K3 w", no_capture_limit=3)
    game.play((cell(8, 8), cell(7, 8)))
    game.play((cell(1, 0), cell(2, 0)))
    assert game.winner() is None
    game.play((cell(7, 8), cell(6, 8)))
    assert game.winner() == 0


def test_capture_resets_the_no_capture_counter():
    game = Xiangqi("3k5/r8/9/9/9/9/9/9/R8/5K3 w", no_capture_limit=2)
    game.play((cell(8, 0), cell(1, 0)))  # takes the chariot
    assert game.winner() is None


def test_ply_limit_is_a_draw():
    game = Xiangqi("3k5/r8/9/9/9/9/9/9/8R/5K3 w", max_plies=1)
    game.play((cell(8, 8), cell(7, 8)))
    assert game.winner() == 0


def test_undo_restores_everything_after_random_play():
    rng = random.Random(1)
    game = Xiangqi()
    start = game.key()
    played = 0
    for _ in range(60):
        moves = game.legal_moves()
        if not moves:
            break
        game.play(rng.choice(moves))
        played += 1
    for _ in range(played):
        game.undo()
    assert game.key() == start
    assert game.to_play == 1
    assert len(game.legal_moves()) == 44


def test_clone_is_independent():
    game = Xiangqi()
    copy = game.clone()
    copy.play(copy.legal_moves()[0])
    assert game.to_play == 1
    assert len(game.legal_moves()) == 44
    copy.undo()
    assert copy.key() == game.key()


def test_position_key_preserves_history_dependent_draw_context():
    fen = "3k5/r8/9/9/9/9/9/9/8R/5K3 w"
    fresh = Xiangqi(fen)
    repeated = Xiangqi(fen)
    loop = [(cell(8, 8), cell(7, 8)), (cell(1, 0), cell(2, 0)),
            (cell(7, 8), cell(8, 8)), (cell(2, 0), cell(1, 0))]
    for move in loop * 2:
        repeated.play(move)
    assert fresh.board == repeated.board
    assert fresh.to_play == repeated.to_play
    assert fresh.winner() is None and repeated.winner() == 0
    assert fresh.key() != repeated.key()
    assert fresh.key() != Xiangqi(fen, max_plies=10).key()


def test_evaluation_is_zero_at_the_start_and_rewards_material():
    assert Xiangqi().evaluate() == 0
    up_a_chariot = Xiangqi("3k5/9/9/9/9/9/9/9/8R/5K3 w")
    assert up_a_chariot.evaluate() > 500
    down_a_chariot = Xiangqi("3k4r/9/9/9/9/9/9/9/9/5K3 w")
    assert down_a_chariot.evaluate() < -500


def test_evaluation_is_antisymmetric_under_a_board_flip():
    red = Xiangqi("3k5/9/9/9/9/9/9/2N6/8R/5K3 w")
    black = Xiangqi("3k5/r8/6n2/9/9/9/9/9/9/5K3 w")
    assert red.evaluate() == -black.evaluate()


@pytest.mark.parametrize("policy", ["random", "heuristic", "cutoff"])
def test_rollout_reward_is_a_probability(policy):
    rng = random.Random(1)
    for _ in range(5):
        assert 0.0 <= Xiangqi().simulate(policy, rng) <= 1.0


def test_heuristic_rollout_captures_an_exposed_general():
    rng = random.Random(1)
    for _ in range(20):
        game = Xiangqi("3k5/9/9/9/9/9/9/9/3R5/5K3 w")
        assert game.simulate("heuristic", rng) == 1.0


def test_alpha_beta_finds_the_mate_in_one():
    game = Xiangqi("3k5/R8/9/9/9/9/9/9/9/5K2R w")
    result = search(game, depth=2)
    assert result.value > WIN_SCORE - 10
    for move in result.best_moves:
        game.play(move)
        assert game.winner() == 1
        game.undo()


def test_alpha_beta_takes_the_hanging_chariot():
    game = Xiangqi("3k5/9/9/9/8r/9/9/9/8R/5K3 w")
    assert search(game, depth=1).best_moves == [(cell(8, 8), cell(4, 8))]


def test_alpha_beta_matches_minimax_at_depth_two():
    plain = search(Xiangqi(), depth=2, pruning=False)
    pruned = search(Xiangqi(), depth=2, pruning=True)
    assert pruned.value == plain.value
    assert sorted(pruned.best_moves) == sorted(plain.best_moves)
    assert pruned.nodes < plain.nodes


def test_mcts_takes_the_hanging_chariot():
    game = Xiangqi("3k5/9/9/9/8r/9/9/9/8R/5K3 w")
    move = MCTS(iterations=800, rollout="cutoff", rng=random.Random(1)).best_move(game)
    assert move == (cell(8, 8), cell(4, 8))
