"""Players. An agent turns a position into a move with ``choose(game, rng)``."""
from gameai.search.mcts import MCTS, final_move
from gameai.search.minimax import optimal_moves, search


class RandomAgent:
    nodes = 0

    def choose(self, game, rng):
        return rng.choice(game.legal_moves())


class AlphaBetaAgent:
    """Depth-limited Alpha-Beta with move ordering; ties are broken at random."""

    def __init__(self, depth, radius=None):
        self.depth = depth
        self.radius = radius
        self.nodes = 0

    def _moves(self):
        if self.radius is None:
            return None
        return lambda state: state.candidate_moves(self.radius)

    def choose(self, game, rng):
        result = search(game, depth=self.depth, pruning=True, moves=self._moves(), order=True)
        self.nodes = result.nodes
        return rng.choice(result.best_moves)


class PerfectAgent:
    """Plays any move that keeps the exact game value; only feasible on 3x3."""

    nodes = 0

    def __init__(self):
        self.memo = {}

    def choose(self, game, rng):
        return rng.choice(optimal_moves(game, self.memo))


class MCTSAgent:
    def __init__(self, iterations, c=1.4, formula="ucb1", rollout="random",
                 final_rule="robust", radius=None):
        self.options = dict(iterations=iterations, c=c, formula=formula, rollout=rollout,
                            final_rule=final_rule, radius=radius)
        self.nodes = 0
        self.root = None

    def choose(self, game, rng):
        mcts = MCTS(rng=rng, **self.options)
        self.root = mcts.search(game)
        self.nodes = mcts.nodes_created
        return final_move(self.root.children, self.options["final_rule"]).move


def build_agent(spec):
    """Create an agent from a plain dictionary, as stored with every experiment row."""
    kind = spec["type"]
    options = {key: value for key, value in spec.items() if key != "type"}
    if kind == "random":
        return RandomAgent()
    if kind == "perfect":
        return PerfectAgent()
    if kind == "alphabeta":
        return AlphaBetaAgent(**options)
    if kind == "mcts":
        return MCTSAgent(**options)
    raise ValueError(f"unknown agent type: {kind}")
