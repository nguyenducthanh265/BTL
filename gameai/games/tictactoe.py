"""Generalised Tic-Tac-Toe: a square board where k stones in a line win.

TicTacToe(3, 3) is the classic game. TicTacToe(9, 5) is the five-in-a-row variant
from the assignment; lines longer than k also win (free-style rule).

The board is a flat list of ``size * size`` cells holding 0, +1 (X) or -1 (O).
"""
import math

DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))
WINDOW_SCORES = {3: (0, 1, 8), 5: (0, 1, 8, 64, 512)}
WIN_SCORE = 1_000_000
CUTOFF_DEPTH = 12
CUTOFF_SCALE = 64.0

_tables = {}


class _Tables:
    """Geometry that depends only on (size, k), computed once and shared."""

    def __init__(self, size, k):
        self.rays = [self._cell_rays(cell, size, k) for cell in range(size * size)]
        self.windows = self._all_windows(size, k)
        self.neighbours = {}
        self.size = size

    @staticmethod
    def _walk(row, col, d_row, d_col, size, steps):
        cells = []
        for _ in range(steps):
            row, col = row + d_row, col + d_col
            if not (0 <= row < size and 0 <= col < size):
                break
            cells.append(row * size + col)
        return tuple(cells)

    @classmethod
    def _cell_rays(cls, cell, size, k):
        """For each direction: the cells walking backwards and forwards from ``cell``."""
        row, col = divmod(cell, size)
        return tuple(
            (
                cls._walk(row, col, -d_row, -d_col, size, k),
                cls._walk(row, col, d_row, d_col, size, k),
            )
            for d_row, d_col in DIRECTIONS
        )

    @staticmethod
    def _all_windows(size, k):
        windows = []
        for row in range(size):
            for col in range(size):
                for d_row, d_col in DIRECTIONS:
                    end_row, end_col = row + d_row * (k - 1), col + d_col * (k - 1)
                    if 0 <= end_row < size and 0 <= end_col < size:
                        windows.append(
                            tuple(
                                (row + d_row * i) * size + col + d_col * i for i in range(k)
                            )
                        )
        return tuple(windows)

    def near(self, radius):
        """cell -> cells within Chebyshev distance ``radius``, excluding itself."""
        if radius not in self.neighbours:
            size = self.size
            table = []
            for cell in range(size * size):
                row, col = divmod(cell, size)
                table.append(
                    tuple(
                        r * size + c
                        for r in range(max(0, row - radius), min(size, row + radius + 1))
                        for c in range(max(0, col - radius), min(size, col + radius + 1))
                        if (r, c) != (row, col)
                    )
                )
            self.neighbours[radius] = table
        return self.neighbours[radius]


def _tables_for(size, k):
    key = (size, k)
    if key not in _tables:
        _tables[key] = _Tables(size, k)
    return _tables[key]


class TicTacToe:
    __slots__ = ("size", "k", "board", "to_play", "history", "_winner", "_tables", "_rays")

    def __init__(self, size=3, k=3):
        if not isinstance(size, int) or not isinstance(k, int) or not 1 <= k <= size:
            raise ValueError("size and k must be integers with 1 <= k <= size")
        if size * size >= WIN_SCORE:
            raise ValueError("board area must be smaller than WIN_SCORE")
        self.size = size
        self.k = k
        self.board = [0] * (size * size)
        self.to_play = 1
        self.history = []
        self._winner = None
        self._tables = _tables_for(size, k)
        self._rays = self._tables.rays

    # ------------------------------------------------------------------ rules
    def clone(self):
        other = TicTacToe.__new__(TicTacToe)
        other.size = self.size
        other.k = self.k
        other.board = self.board[:]
        other.to_play = self.to_play
        other.history = self.history[:]
        other._winner = self._winner
        other._tables = self._tables
        other._rays = self._rays
        return other

    def legal_moves(self):
        if self._winner is not None:
            return []
        return [cell for cell, stone in enumerate(self.board) if stone == 0]

    def play(self, cell):
        player = self.to_play
        self.board[cell] = player
        self.history.append(cell)
        if self._completes_line(cell, player):
            self._winner = player
        elif len(self.history) == len(self.board):
            self._winner = 0
        self.to_play = -player

    def undo(self):
        cell = self.history.pop()
        self.board[cell] = 0
        self.to_play = -self.to_play
        self._winner = None

    def winner(self):
        return self._winner

    def key(self):
        return (tuple(self.board), self.to_play, self.size, self.k)

    def _completes_line(self, cell, player):
        board = self.board
        k = self.k
        for backward, forward in self._rays[cell]:
            count = 1
            for other in backward:
                if board[other] != player:
                    break
                count += 1
            for other in forward:
                if board[other] != player:
                    break
                count += 1
            if count >= k:
                return True
        return False

    # ------------------------------------------------------- search helpers
    def candidate_moves(self, radius=2):
        """Empty cells near an existing stone, the standard big-board reduction."""
        if self._winner is not None:
            return []
        if not self.history:
            return [(self.size // 2) * self.size + self.size // 2]
        near = self._tables.near(radius)
        board = self.board
        cells = set()
        for stone in self.history:
            for cell in near[stone]:
                if board[cell] == 0:
                    cells.add(cell)
        return sorted(cells)

    def threat_cell(self, cell):
        """Empty cell that would complete k in a row through the stone on ``cell``."""
        board = self.board
        player = board[cell]
        k = self.k
        for backward, forward in self._rays[cell]:
            run = 1
            gap_back = gap_forward = None
            extra_back = extra_forward = 0
            for i, other in enumerate(backward):
                stone = board[other]
                if stone == player:
                    run += 1
                    continue
                if stone == 0:
                    gap_back = other
                    for beyond in backward[i + 1:]:
                        if board[beyond] != player:
                            break
                        extra_back += 1
                break
            for i, other in enumerate(forward):
                stone = board[other]
                if stone == player:
                    run += 1
                    continue
                if stone == 0:
                    gap_forward = other
                    for beyond in forward[i + 1:]:
                        if board[beyond] != player:
                            break
                        extra_forward += 1
                break
            if gap_back is not None and run + extra_back + 1 >= k:
                return gap_back
            if gap_forward is not None and run + extra_forward + 1 >= k:
                return gap_forward
        return None

    def evaluate(self):
        """Sum over all k-windows that contain stones of one player only."""
        if self._winner is not None:
            return self._winner * WIN_SCORE
        board = self.board
        scores = WINDOW_SCORES.get(self.k)
        if scores is None:
            scores = (0,) + tuple(8 ** (count - 1) for count in range(1, self.k))
        total = 0
        for window in self._tables.windows:
            x_stones = o_stones = 0
            for cell in window:
                stone = board[cell]
                if stone == 1:
                    x_stones += 1
                elif stone:
                    o_stones += 1
            if not o_stones:
                total += scores[x_stones]
            elif not x_stones:
                total -= scores[o_stones]
        # Search scores a terminal result as WIN_SCORE - ply. Even the latest
        # possible terminal (size**2 plies from an empty board) must outrank
        # every heuristic leaf, including large k with exponential weights.
        limit = WIN_SCORE - len(board) - 1
        return max(-limit, min(limit, total))

    def move_prior(self, cell):
        """Share of neighbouring cells already occupied, a measure of local activity."""
        near = self._tables.near(1)[cell]
        board = self.board
        occupied = sum(1 for other in near if board[other])
        return occupied / len(near) if near else 0.0

    # ------------------------------------------------------------- rollouts
    def simulate(self, policy, rng):
        if self._winner is not None:
            return (self._winner + 1) / 2
        if policy == "random":
            return self._rollout_random(rng)
        if policy == "heuristic":
            return self._rollout_heuristic(rng, None)
        if policy == "cutoff":
            return self._rollout_heuristic(rng, CUTOFF_DEPTH)
        raise ValueError(f"unknown rollout policy: {policy}")

    def _rollout_random(self, rng):
        """Both sides place stones uniformly at random until the game ends."""
        board = self.board
        rays = self._rays
        k = self.k
        player = self.to_play
        cells = [cell for cell, stone in enumerate(board) if stone == 0]
        rng.shuffle(cells)
        for cell in cells:
            board[cell] = player
            for backward, forward in rays[cell]:
                count = 1
                for other in backward:
                    if board[other] != player:
                        break
                    count += 1
                for other in forward:
                    if board[other] != player:
                        break
                    count += 1
                if count >= k:
                    return 1.0 if player == 1 else 0.0
            player = -player
        return 0.5

    def _rollout_heuristic(self, rng, max_plies):
        """Take a win, else block a loss, else play near the last stone.

        Threats are read from the last two stones only. This is a local policy, not a
        complete win/block check: a step stays cheap, but a threat made by an older
        stone is missed, which is common on random positions.
        With ``max_plies`` the rollout stops early and the position is scored by
        ``evaluate`` squashed into [0, 1]: a hand-written value function.
        """
        history = self.history
        near = self._tables.near(1)
        board = self.board
        cells = [cell for cell, stone in enumerate(board) if stone == 0]
        rng.shuffle(cells)
        position = 0
        plies = 0
        while self._winner is None:
            if max_plies is not None and plies >= max_plies:
                return 1.0 / (1.0 + math.exp(-_clamp(self.evaluate() / CUTOFF_SCALE)))
            move = None
            if len(history) >= 2:
                move = self.threat_cell(history[-2])  # my own winning cell
            if move is None and history:
                move = self.threat_cell(history[-1])  # block the opponent
            if move is None and history:
                free = [cell for cell in near[history[-1]] if board[cell] == 0]
                if free:
                    move = free[int(rng.random() * len(free))]
            if move is None:
                while board[cells[position]] != 0:
                    position += 1
                move = cells[position]
            self.play(move)
            plies += 1
        return (self._winner + 1) / 2


def _clamp(value, limit=30.0):
    return max(-limit, min(limit, value))
