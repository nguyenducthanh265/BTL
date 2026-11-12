"""Monte Carlo Tree Search with pluggable selection formulas and rollout policies.

Each iteration performs the four classic steps:

1. Selection       walk down with the selection formula while nodes are fully expanded
2. Expansion       add one untried move as a new child
3. Simulation      finish the game with the rollout policy
4. Backpropagation add the result to every node on the path

``child.w`` counts rewards for the player who moved into the child, so the parent
(whose turn it is to choose) always wants the child with the highest W/N.
"""
import math
import random

from gameai.search.selection import FORMULAS

FINAL_RULES = ("robust", "max_ratio")


class Node:
    __slots__ = ("move", "parent", "children", "untried", "mover", "prior", "n", "w", "w2")

    def __init__(self, move, parent, untried, mover, prior):
        self.move = move
        self.parent = parent
        self.untried = untried
        self.mover = mover
        self.prior = prior
        self.children = []
        self.n = 0
        self.w = 0.0
        self.w2 = 0.0


def final_move(children, rule="robust"):
    """Pick the move to actually play from the root's children.

    robust     the most visited child: its statistics have the most support
    max_ratio  the child with the best W/N: exposed to children with few visits
    """
    if rule == "robust":
        return max(children, key=lambda child: (child.n, child.w))
    if rule == "max_ratio":
        return max(children, key=lambda child: (child.w / child.n, child.n))
    raise ValueError(f"unknown final-move rule: {rule}")


class MCTS:
    def __init__(
        self,
        iterations,
        c=math.sqrt(2),
        formula="ucb1",
        rollout="random",
        final_rule="robust",
        radius=None,
        rng=None,
    ):
        if iterations < 1:
            raise ValueError("iterations must be positive")
        if formula not in FORMULAS:
            raise ValueError(f"unknown formula: {formula}")
        if final_rule not in FINAL_RULES:
            raise ValueError(f"unknown final-move rule: {final_rule}")
        self.iterations = iterations
        self.c = c
        self.formula = FORMULAS[formula]
        self.rollout = rollout
        self.final_rule = final_rule
        self.radius = radius
        self.rng = rng or random.Random()
        self.nodes_created = 0

    def _moves(self, state):
        if self.radius is None:
            return state.legal_moves()
        return state.candidate_moves(self.radius) or state.legal_moves()

    def search(self, game):
        """Run all iterations on a private copy of ``game`` and return the root node."""
        rng = self.rng
        root = Node(None, None, self._moves(game), -game.to_play, 0.0)
        self.nodes_created = 1
        for _ in range(self.iterations):
            state = game.clone()
            node = root

            # 1. Selection
            while not node.untried and node.children:
                node = self._select(node)
                state.play(node.move)

            # 2. Expansion
            if node.untried:
                index = int(rng.random() * len(node.untried))
                move = node.untried[index]
                node.untried[index] = node.untried[-1]
                node.untried.pop()
                prior = state.move_prior(move)
                mover = state.to_play
                state.play(move)
                child = Node(move, node, self._moves(state), mover, prior)
                node.children.append(child)
                node = child
                self.nodes_created += 1

            # 3. Simulation: reward of player +1
            reward = state.simulate(self.rollout, rng)

            # 4. Backpropagation
            while node is not None:
                gained = reward if node.mover == 1 else 1.0 - reward
                node.n += 1
                node.w += gained
                node.w2 += gained * gained
                node = node.parent
        return root

    def _select(self, node):
        parent_n = node.n
        log_n = math.log(parent_n)
        formula = self.formula
        c = self.c
        best = None
        best_score = -math.inf
        for child in node.children:
            score = formula(child, parent_n, log_n, c)
            if score > best_score:
                best_score = score
                best = child
        return best

    def best_move(self, game):
        return final_move(self.search(game).children, self.final_rule).move
