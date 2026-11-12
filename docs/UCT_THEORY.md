# UCT: derivation, implementation and limits

## The score used here

For a visited child i, `ucb1` evaluates

\[
S_i = \bar X_i + c\sqrt{\frac{\ln N_p}{N_i}},\qquad
\bar X_i = W_i/N_i.
\]

Rewards are 1 for a win, 1/2 for a draw, and 0 for a loss. Thus W is accumulated reward, **not a literal count of wins**. Unvisited actions are expanded before evaluating this formula, avoiding division by zero. A child's statistics use the perspective of the player who moved into it. At an opponent node the opponent also maximizes its own reward; the implementation does not mistakenly cooperate with the root player.

## Where the square root and logarithm come from

For independent rewards X in [0,1], the one-sided Hoeffding bound is

\[
\Pr(\mu_i-\bar X_{i,n}\ge\epsilon)\le e^{-2n\epsilon^2}.
\]

Set the right-hand side to t^-4, then solve for epsilon:

\[
\epsilon=\sqrt{2\ln(t)/n}.
\]

Adding this radius to the sample mean gives the UCB1 index with c=sqrt(2). The square root reflects the sampling-error scale; log(t) lets uncertainty grow slowly for an arm whose sample count is unchanged. General c is a tunable exploration parameter; the UCB1 theoretical constant does not establish a universal best setting for adversarial tree search. Adaptive sample counts also require the full proof's summations/union bounds, not only this fixed-n sketch. Auer et al. give the bandit analysis [1].

UCT transfers the index idea to nodes of a search tree [2]. That transfer is a method, not permission to regard all downstream rollout rewards as stationary IID arm samples: descendants change as search learns. In this coursework the concentration argument motivates the formula; it does not prove finite-budget perfection in either game.

## Ablations and modifications implemented

| Name | Exploration or additional term | Interpretation |
|---|---|---|
| `ucb1` | c sqrt(log(Np)/Ni) | reference |
| `no_sqrt` | c log(Np)/Ni | faster decay in Ni |
| `no_log` | c sqrt(Np/Ni) | much stronger dependence on parent visits |
| `polynomial` | c Np^(1/4)/sqrt(Ni) | polynomial exploration candidate; no new guarantee claimed here |
| `ucb1_tuned` | c sqrt(log(Np)/Ni * min(1/4, variance + sqrt(2 log(Np)/Ni))) | empirical-variance adaptation |
| `progressive_bias` | UCB1 + prior/(Ni+1) | decaying hand-written move prior |

Changing the functional form also changes its scale. Compare all candidate c values, not only c=1.4. A practical improvement requires replicated game-level evidence; implementing a variant does not show it is better. The Bernoulli bandit experiment is an explanatory control and does not stand in for game evaluation.

## Final decision and rollout

Selection during search maximizes the exploration index. The final played move instead uses either the most visited child (`robust`, tie by accumulated reward), or the largest empirical mean (`max_ratio`, tie by visits). The largest mean may come from a lucky, rarely visited child. More visits provide stronger support, but neither rule guarantees correctness. The two rules need direct comparison at the same budget.

Heuristic placement rollouts inspect recent threats and prefer nearby free cells; they are local rules and can miss older threats. Cutoff rollouts map a hand-written board evaluation through a sigmoid. This is analogous to using a value estimate in place of a completed simulation, but there is no learned value network. Equal iterations do not imply equal compute because policies have different costs; time-matched comparisons need measured timing.

## Interpreting a 3x3 verification

1. Exact enumeration finds 5,478 reachable legal boards, including 958 terminal boards and 4,520 boards requiring a decision.
2. For each nonterminal board, compare the chosen MCTS move to a full-tree optimal-action oracle. A blunder lowers the exact game-theoretic value.
3. Separately branch over every legal opponent reply while fixing MCTS randomness by seed. This tests those particular random realizations and decision paths, not every possible random trajectory.
4. Any observed loss refutes a universal never-lose statement for that configuration. Zero observed losses remains conditional evidence. Opponent paths share prefixes and are dependent; a binomial confidence bound treating paths as independent games is inappropriate.

Full-depth Minimax/Alpha-Beta can establish non-loss on 3x3 from a draw-valued start when all chosen moves preserve the exact value. This result belongs to the exact algorithms and must not be relabeled as a proof about ordinary finite-budget MCTS.

## Primary references

1. P. Auer, N. Cesa-Bianchi, and P. Fischer, "Finite-time Analysis of the Multiarmed Bandit Problem," Machine Learning, vol. 47, pp. 235-256, 2002. [Publisher](https://doi.org/10.1023/A:1013689704352), [paper](https://people.eecs.berkeley.edu/~russell/classes/cs294/s11/readings/Auer%2Bal:2002.pdf).
2. L. Kocsis and C. Szepesvari, "Bandit based Monte-Carlo Planning," ECML, pp. 282-293, 2006. [Paper](https://aima.cs.berkeley.edu/~russell/classes/cs294/s11/readings/Kocsis%2BSzepesvari:2006.pdf).

References checked on 2026-11-06. The explanations of this repository's conventions and evidence are based on its code and CSVs.
