"""Tree-policy formulas: how MCTS scores a child during selection.

Every formula has the shape ``exploitation + exploration`` and receives
``(child, parent_n, log_parent_n, c)``. Only children with at least one visit are
scored, because unvisited moves are always expanded first.
"""
from math import sqrt


def ucb1(child, parent_n, log_n, c):
    """The assignment's UCT: W/N + c * sqrt(ln(N_p) / N)."""
    return child.w / child.n + c * sqrt(log_n / child.n)


def no_sqrt(child, parent_n, log_n, c):
    """Without the square root: W/N + c * ln(N_p) / N. Exploration fades much faster."""
    return child.w / child.n + c * log_n / child.n


def no_log(child, parent_n, log_n, c):
    """Without the logarithm: W/N + c * sqrt(N_p / N). Exploration stays polynomial."""
    return child.w / child.n + c * sqrt(parent_n / child.n)


def polynomial(child, parent_n, log_n, c):
    """Polynomial UCT (Shah, Xie & Xu, 2020): W/N + c * N_p^(1/4) / sqrt(N)."""
    return child.w / child.n + c * parent_n**0.25 / sqrt(child.n)


def ucb1_tuned(child, parent_n, log_n, c):
    """UCB1-Tuned (Auer et al., 2002): scales exploration by the observed variance."""
    mean = child.w / child.n
    ratio = log_n / child.n
    variance = max(0.0, child.w2 / child.n - mean * mean)
    return mean + c * sqrt(ratio * min(0.25, variance + sqrt(2.0 * ratio)))


def progressive_bias(child, parent_n, log_n, c):
    """UCB1 plus a heuristic term that fades with visits (Chaslot et al., 2008)."""
    return (
        child.w / child.n
        + c * sqrt(log_n / child.n)
        + child.prior / (child.n + 1)
    )


FORMULAS = {
    "ucb1": ucb1,
    "no_sqrt": no_sqrt,
    "no_log": no_log,
    "polynomial": polynomial,
    "ucb1_tuned": ucb1_tuned,
    "progressive_bias": progressive_bias,
}
