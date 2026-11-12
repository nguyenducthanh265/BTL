"""Minimax and Alpha-Beta search.

Values are always from the point of view of player +1: player +1 maximises and
player -1 minimises. A win scores ``WIN_SCORE - ply`` so that faster wins and slower
losses are preferred. ``depth=None`` searches to the end of the game.
"""
from dataclasses import dataclass
from math import inf

WIN_SCORE = 1_000_000


@dataclass
class SearchResult:
    value: int
    best_moves: list
    nodes: int


class _Searcher:
    def __init__(self, moves, order):
        self.moves = moves or (lambda state: state.legal_moves())
        self.order = order
        self.nodes = 0

    def _moves_of(self, game):
        moves = self.moves(game) or game.legal_moves()
        if self.order:
            moves = sorted(moves, key=game.move_prior, reverse=True)
        return moves

    @staticmethod
    def _terminal_value(result, ply):
        return 0 if result == 0 else result * (WIN_SCORE - ply)

    def minimax(self, game, depth, ply):
        """Plain Minimax: visit every child of every node."""
        self.nodes += 1
        result = game.winner()
        if result is not None:
            return self._terminal_value(result, ply)
        if depth == 0:
            return game.evaluate()
        next_depth = None if depth is None else depth - 1
        values = []
        for move in self._moves_of(game):
            game.play(move)
            values.append(self.minimax(game, next_depth, ply + 1))
            game.undo()
        return max(values) if game.to_play == 1 else min(values)

    def alphabeta(self, game, depth, alpha, beta, ply):
        """Minimax that stops examining a node once its value cannot matter.

        alpha: best value the maximiser can already force on the path to this node.
        beta:  best value the minimiser can already force on the path to this node.
        When alpha >= beta the parent will never allow this node, so we cut.
        """
        self.nodes += 1
        result = game.winner()
        if result is not None:
            return self._terminal_value(result, ply)
        if depth == 0:
            return game.evaluate()
        next_depth = None if depth is None else depth - 1
        if game.to_play == 1:
            value = -inf
            for move in self._moves_of(game):
                game.play(move)
                value = max(value, self.alphabeta(game, next_depth, alpha, beta, ply + 1))
                game.undo()
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        value = inf
        for move in self._moves_of(game):
            game.play(move)
            value = min(value, self.alphabeta(game, next_depth, alpha, beta, ply + 1))
            game.undo()
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value


def search(game, depth=None, pruning=True, moves=None, order=False):
    """Search ``game`` and report the value, all equally best moves and the node count.

    Scores are integers, so the root searches each move with a window one point wider
    than the best value so far. A move that ties the best is then evaluated exactly
    and is not confused with a move that was merely cut off at that bound.
    """
    if depth is not None and (not isinstance(depth, int) or depth < 0):
        raise ValueError("depth must be a nonnegative integer or None")
    result = game.winner()
    if result is not None:
        return SearchResult(_Searcher._terminal_value(result, 0), [], 1)
    if depth == 0:
        return SearchResult(game.evaluate(), [], 1)
    searcher = _Searcher(moves, order)
    searcher.nodes = 1
    root_moves = searcher._moves_of(game)
    next_depth = None if depth is None else depth - 1
    maximising = game.to_play == 1
    best_value = -inf if maximising else inf
    best_moves = []
    for move in root_moves:
        game.play(move)
        if not pruning:
            value = searcher.minimax(game, next_depth, 1)
        elif maximising:
            value = searcher.alphabeta(game, next_depth, best_value - 1, inf, 1)
        else:
            value = searcher.alphabeta(game, next_depth, -inf, best_value + 1, 1)
        game.undo()
        if value == best_value:
            best_moves.append(move)
        elif (value > best_value) == maximising:
            best_value = value
            best_moves = [move]
    return SearchResult(best_value, best_moves, searcher.nodes)


def solve(game, _memo=None):
    """Exact game-theoretic value for player +1: +1 win, 0 draw, -1 loss."""
    memo = {} if _memo is None else _memo
    key = game.key()
    if key in memo:
        return memo[key]
    result = game.winner()
    if result is not None:
        return result
    values = []
    for move in game.legal_moves():
        game.play(move)
        values.append(solve(game, memo))
        game.undo()
    value = max(values) if game.to_play == 1 else min(values)
    memo[key] = value
    return value


def optimal_moves(game, memo=None):
    """All moves that keep the game-theoretic value of the position."""
    memo = {} if memo is None else memo
    target = solve(game, memo)
    moves = []
    for move in game.legal_moves():
        game.play(move)
        if solve(game, memo) == target:
            moves.append(move)
        game.undo()
    return moves
