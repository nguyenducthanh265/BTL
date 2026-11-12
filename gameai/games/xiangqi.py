"""Xiangqi (Chinese chess) rules, evaluation and rollouts.

Board: flat list of 90 cells, index = row * 9 + col. Row 0 is Black's back rank and
row 9 is Red's. Red is player +1 and moves first. A piece is ``player * kind``.
A move is the tuple ``(from_cell, to_cell)``.

Simplifications, stated in the report: threefold repetition is a plain draw (the full
Asian rules on perpetual check and chase are not implemented), and a game with no
capture for ``no_capture_limit`` plies or reaching ``max_plies`` is a draw.
"""
import math
import random

GENERAL, ADVISOR, ELEPHANT, HORSE, CHARIOT, CANNON, SOLDIER = range(1, 8)
ROWS, COLS, CELLS = 10, 9, 90
START_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w"
FEN_KINDS = {
    "k": GENERAL, "a": ADVISOR, "b": ELEPHANT, "n": HORSE,
    "r": CHARIOT, "c": CANNON, "p": SOLDIER,
}
PIECE_VALUE = (0, 0, 200, 200, 400, 900, 450, 100)
WIN_SCORE = 1_000_000

RANDOM_ROLLOUT_LIMIT = 200
CUTOFF_DEPTH = 16
CUTOFF_SCALE = 400.0
GREEDY_CAPTURE_PROBABILITY = 0.8


def cell(row, col):
    return row * COLS + col


def _on_board(row, col):
    return 0 <= row < ROWS and 0 <= col < COLS


def _in_palace(row, col, player):
    rows = range(7, 10) if player == 1 else range(0, 3)
    return row in rows and 3 <= col <= 5


def _own_side(row, player):
    return row >= 5 if player == 1 else row <= 4


def _build_rays():
    rays = []
    for index in range(CELLS):
        row, col = divmod(index, COLS)
        rays.append(
            (
                tuple(cell(r, col) for r in range(row - 1, -1, -1)),  # up
                tuple(cell(r, col) for r in range(row + 1, ROWS)),  # down
                tuple(cell(row, c) for c in range(col - 1, -1, -1)),  # left
                tuple(cell(row, c) for c in range(col + 1, COLS)),  # right
            )
        )
    return rays


def _build_horse():
    table = []
    for index in range(CELLS):
        row, col = divmod(index, COLS)
        moves = []
        for d_row, d_col, leg_row, leg_col in (
            (-2, -1, -1, 0), (-2, 1, -1, 0), (2, -1, 1, 0), (2, 1, 1, 0),
            (-1, -2, 0, -1), (1, -2, 0, -1), (-1, 2, 0, 1), (1, 2, 0, 1),
        ):
            if _on_board(row + d_row, col + d_col):
                moves.append((cell(row + d_row, col + d_col), cell(row + leg_row, col + leg_col)))
        table.append(tuple(moves))
    return table


def _build_elephant():
    table = {1: [], -1: []}
    for player in (1, -1):
        for index in range(CELLS):
            row, col = divmod(index, COLS)
            moves = []
            for d_row, d_col in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
                to_row, to_col = row + d_row, col + d_col
                if _on_board(to_row, to_col) and _own_side(to_row, player):
                    moves.append((cell(to_row, to_col), cell(row + d_row // 2, col + d_col // 2)))
            table[player].append(tuple(moves))
    return table


def _build_palace_steps(deltas):
    table = {1: [], -1: []}
    for player in (1, -1):
        for index in range(CELLS):
            row, col = divmod(index, COLS)
            table[player].append(
                tuple(
                    cell(row + d_row, col + d_col)
                    for d_row, d_col in deltas
                    if _in_palace(row + d_row, col + d_col, player)
                )
            )
    return table


def _build_soldier():
    table = {1: [], -1: []}
    for player in (1, -1):
        forward = -player
        for index in range(CELLS):
            row, col = divmod(index, COLS)
            moves = []
            if _on_board(row + forward, col):
                moves.append(cell(row + forward, col))
            if not _own_side(row, player):
                for d_col in (-1, 1):
                    if _on_board(row, col + d_col):
                        moves.append(cell(row, col + d_col))
            table[player].append(tuple(moves))
    return table


RAYS = _build_rays()
HORSE_MOVES = _build_horse()
HORSE_ATTACKERS = [[] for _ in range(CELLS)]
for _origin, _moves in enumerate(HORSE_MOVES):
    for _target, _leg in _moves:
        HORSE_ATTACKERS[_target].append((_origin, _leg))
ELEPHANT_MOVES = _build_elephant()
ADVISOR_MOVES = _build_palace_steps(((-1, -1), (-1, 1), (1, -1), (1, 1)))
GENERAL_MOVES = _build_palace_steps(((-1, 0), (1, 0), (0, -1), (0, 1)))
SOLDIER_MOVES = _build_soldier()


def _position_bonus(kind, player, index):
    """Small positional score for one piece, from that piece's own point of view."""
    row, col = divmod(index, COLS)
    advance = 9 - row if player == 1 else row  # rows moved up from its own back rank
    centrality = 4 - abs(col - 4)
    if kind == SOLDIER:
        crossed = advance >= 5
        return (100 + 10 * (advance - 5) + 5 * centrality) if crossed else 0
    if kind in (HORSE, CANNON):
        return 3 * centrality + 2 * min(advance, 5)
    if kind == CHARIOT:
        return 2 * min(advance, 5)
    return 0


# PIECE_SCORE[piece + 7][cell]: score of a piece on a cell for player +1.
PIECE_SCORE = [[0] * CELLS for _ in range(15)]
for _kind in range(ADVISOR, SOLDIER + 1):
    for _index in range(CELLS):
        PIECE_SCORE[_kind + 7][_index] = PIECE_VALUE[_kind] + _position_bonus(_kind, 1, _index)
        PIECE_SCORE[-_kind + 7][_index] = -(PIECE_VALUE[_kind] + _position_bonus(_kind, -1, _index))

_zobrist_rng = random.Random(20261210)
ZOBRIST = [[_zobrist_rng.getrandbits(64) for _ in range(CELLS)] for _ in range(15)]
ZOBRIST_SIDE = _zobrist_rng.getrandbits(64)
_UNKNOWN = object()


def _moves_for_player(board, player):
    """All pseudo-legal moves: piece movement only, the general may be left in danger."""
    moves = []
    append = moves.append
    for frm in range(CELLS):
        piece = board[frm]
        if piece == 0 or (piece > 0) != (player > 0):
            continue
        kind = piece if piece > 0 else -piece
        if kind == CHARIOT:
            for ray in RAYS[frm]:
                for to in ray:
                    target = board[to]
                    if target == 0:
                        append((frm, to))
                        continue
                    if (target > 0) != (player > 0):
                        append((frm, to))
                    break
        elif kind == CANNON:
            for ray in RAYS[frm]:
                screen = False
                for to in ray:
                    target = board[to]
                    if not screen:
                        if target == 0:
                            append((frm, to))
                        else:
                            screen = True
                    elif target != 0:
                        if (target > 0) != (player > 0):
                            append((frm, to))
                        break
        elif kind == HORSE:
            for to, leg in HORSE_MOVES[frm]:
                target = board[to]
                if board[leg] == 0 and (target == 0 or (target > 0) != (player > 0)):
                    append((frm, to))
        elif kind == SOLDIER:
            for to in SOLDIER_MOVES[player][frm]:
                target = board[to]
                if target == 0 or (target > 0) != (player > 0):
                    append((frm, to))
        elif kind == ELEPHANT:
            for to, eye in ELEPHANT_MOVES[player][frm]:
                target = board[to]
                if board[eye] == 0 and (target == 0 or (target > 0) != (player > 0)):
                    append((frm, to))
        elif kind == ADVISOR:
            for to in ADVISOR_MOVES[player][frm]:
                target = board[to]
                if target == 0 or (target > 0) != (player > 0):
                    append((frm, to))
        else:  # general, including the "flying general" capture along an open file
            for to in GENERAL_MOVES[player][frm]:
                target = board[to]
                if target == 0 or (target > 0) != (player > 0):
                    append((frm, to))
            for to in RAYS[frm][0 if player == 1 else 1]:
                target = board[to]
                if target == 0:
                    continue
                if target == -player * GENERAL:
                    append((frm, to))
                break
    return moves


class Xiangqi:
    __slots__ = (
        "board", "to_play", "generals", "ply", "hash", "history", "hashes",
        "quiet", "max_plies", "no_capture_limit", "_legal", "_winner",
    )

    def __init__(self, fen=START_FEN, max_plies=200, no_capture_limit=120):
        self.max_plies = max_plies
        self.no_capture_limit = no_capture_limit
        self.board = [0] * CELLS
        self.generals = {1: None, -1: None}
        rows, side = fen.split()
        for row, text in enumerate(rows.split("/")):
            col = 0
            for char in text:
                if char.isdigit():
                    col += int(char)
                    continue
                player = 1 if char.isupper() else -1
                kind = FEN_KINDS[char.lower()]
                self.board[cell(row, col)] = player * kind
                if kind == GENERAL:
                    self.generals[player] = cell(row, col)
                col += 1
        self.to_play = 1 if side == "w" else -1
        self.ply = 0
        self.quiet = 0
        self.history = []
        self.hash = self._full_hash()
        self.hashes = [self.hash]
        self._legal = None
        self._winner = _UNKNOWN

    def _full_hash(self):
        value = 0
        for index, piece in enumerate(self.board):
            if piece:
                value ^= ZOBRIST[piece + 7][index]
        return value ^ ZOBRIST_SIDE if self.to_play == -1 else value

    def clone(self):
        other = Xiangqi.__new__(Xiangqi)
        other.board = self.board[:]
        other.to_play = self.to_play
        other.generals = dict(self.generals)
        other.ply = self.ply
        other.hash = self.hash
        other.history = self.history[:]
        other.hashes = self.hashes[:]
        other.quiet = self.quiet
        other.max_plies = self.max_plies
        other.no_capture_limit = self.no_capture_limit
        other._legal = self._legal
        other._winner = self._winner
        return other

    def key(self):
        # Draw adjudication depends on the path, not just the board and side.
        # In particular, exact-solver memo entries must not leak across histories.
        return (
            tuple(self.board), self.to_play, self.ply, self.quiet,
            self.max_plies, self.no_capture_limit, tuple(self.hashes),
        )

    # ------------------------------------------------------------------ rules
    def play(self, move):
        frm, to = move
        board = self.board
        piece = board[frm]
        captured = board[to]
        self.history.append((frm, to, captured, self.quiet))
        board[to] = piece
        board[frm] = 0
        value = self.hash ^ ZOBRIST[piece + 7][frm] ^ ZOBRIST[piece + 7][to] ^ ZOBRIST_SIDE
        if captured:
            value ^= ZOBRIST[captured + 7][to]
            self.quiet = 0
            if captured in (GENERAL, -GENERAL):
                self.generals[-self.to_play] = None
        else:
            self.quiet += 1
        if piece in (GENERAL, -GENERAL):
            self.generals[self.to_play] = to
        self.hash = value
        self.hashes.append(value)
        self.to_play = -self.to_play
        self.ply += 1
        self._legal = None
        self._winner = _UNKNOWN

    def undo(self):
        frm, to, captured, quiet = self.history.pop()
        board = self.board
        piece = board[to]
        board[frm] = piece
        board[to] = captured
        self.to_play = -self.to_play
        if piece in (GENERAL, -GENERAL):
            self.generals[self.to_play] = frm
        if captured in (GENERAL, -GENERAL):
            self.generals[-self.to_play] = to
        self.quiet = quiet
        self.hashes.pop()
        self.hash = self.hashes[-1]
        self.ply -= 1
        self._legal = None
        self._winner = _UNKNOWN

    def general_attacked(self, player):
        """True if ``player``'s general stands attacked (or is gone)."""
        square = self.generals[player]
        if square is None:
            return True
        board = self.board
        enemy = -player
        enemy_chariot, enemy_cannon = enemy * CHARIOT, enemy * CANNON
        enemy_general, enemy_soldier = enemy * GENERAL, enemy * SOLDIER
        enemy_horse = enemy * HORSE
        rays = RAYS[square]
        for direction, ray in enumerate(rays):
            screen = False
            for index, to in enumerate(ray):
                target = board[to]
                if target == 0:
                    continue
                if screen:
                    if target == enemy_cannon:
                        return True
                    break
                if target == enemy_chariot:
                    return True
                if target == enemy_general and direction < 2:
                    return True
                if target == enemy_soldier and index == 0:
                    # A soldier attacks forwards and sideways, never backwards.
                    moving_towards_us = direction == (0 if player == 1 else 1)
                    if moving_towards_us or direction >= 2:
                        return True
                screen = True
        for origin, leg in HORSE_ATTACKERS[square]:
            if board[origin] == enemy_horse and board[leg] == 0:
                return True
        return False

    def _raw_legal(self):
        if self._legal is None:
            player = self.to_play
            legal = []
            for move in _moves_for_player(self.board, player):
                self.play(move)
                safe = not self.general_attacked(player)
                self.undo()
                if safe:
                    legal.append(move)
            self._legal = legal
        return self._legal

    def legal_moves(self):
        return [] if self.winner() is not None else list(self._raw_legal())

    def winner(self):
        if self._winner is _UNKNOWN:
            self._winner = self._compute_winner()
        return self._winner

    def _compute_winner(self):
        if not self._raw_legal():
            return -self.to_play  # checkmate and stalemate both lose
        if self.ply >= self.max_plies or self.quiet >= self.no_capture_limit:
            return 0
        if self.quiet >= 8:
            recent = self.hashes[-(self.quiet + 1):]
            if recent.count(self.hash) >= 3:
                return 0
        return None

    # ------------------------------------------------------- search helpers
    def evaluate(self):
        """Material plus a small positional term, from the point of view of Red."""
        total = 0
        for index, piece in enumerate(self.board):
            if piece:
                total += PIECE_SCORE[piece + 7][index]
        return total

    def move_prior(self, move):
        """Most valuable victim first, used for move ordering and progressive bias."""
        victim = self.board[move[1]]
        return PIECE_VALUE[victim if victim > 0 else -victim] / 900.0

    # ------------------------------------------------------------- rollouts
    def simulate(self, policy, rng):
        result = self.winner()
        if result is not None:
            return (result + 1) / 2
        if policy == "random":
            return self._rollout(rng, RANDOM_ROLLOUT_LIMIT, greedy=False, score_cutoff=False)
        if policy == "heuristic":
            return self._rollout(rng, RANDOM_ROLLOUT_LIMIT, greedy=True, score_cutoff=False)
        if policy == "cutoff":
            return self._rollout(rng, CUTOFF_DEPTH, greedy=True, score_cutoff=True)
        raise ValueError(f"unknown rollout policy: {policy}")

    def _rollout(self, rng, limit, greedy, score_cutoff):
        """Play pseudo-legal moves until a general is captured or the limit is reached.

        Skipping the legality test makes one step far cheaper. An illegal move simply
        exposes the general, which the opponent may then capture, ending the rollout.
        """
        board = self.board
        player = self.to_play
        random_value = rng.random
        for _ in range(limit):
            moves = _moves_for_player(board, player)
            if not moves:
                return 0.0 if player == 1 else 1.0
            move = None
            if greedy:
                best_value = 0
                for candidate in moves:
                    victim = board[candidate[1]]
                    if victim:
                        kind = victim if victim > 0 else -victim
                        if kind == GENERAL:
                            return 1.0 if player == 1 else 0.0
                        if PIECE_VALUE[kind] > best_value:
                            best_value = PIECE_VALUE[kind]
                            move = candidate
                if move is not None and random_value() > GREEDY_CAPTURE_PROBABILITY:
                    move = None
            if move is None:
                move = moves[int(random_value() * len(moves))]
            frm, to = move
            victim = board[to]
            board[to] = board[frm]
            board[frm] = 0
            if victim in (GENERAL, -GENERAL):
                return 1.0 if player == 1 else 0.0
            player = -player
        if score_cutoff:
            return 1.0 / (1.0 + math.exp(-self.evaluate() / CUTOFF_SCALE))
        return 0.5
