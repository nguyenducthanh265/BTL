**Rollout policies against Alpha-Beta: five-in-a-row 9x9**

| Agent a | Opponent b | Games | W | D | L | Score | Approx. 95% score interval | Flag |
|---|---|---|---|---|---|---|---|---|
| MCTS(1000, c=1.4) | AB(d=2, r=2) | 100 | 0 | 0 | 100 | 0.000 | [0.000, 0.037] | interval below 0.5 (descriptive) |
| MCTS(1000, c=1.4, heuristic) | AB(d=2, r=2) | 100 | 0 | 0 | 100 | 0.000 | [0.000, 0.037] | interval below 0.5 (descriptive) |
| MCTS(1000, c=1.4, cutoff) | AB(d=2, r=2) | 100 | 1 | 1 | 98 | 0.015 | [0.003, 0.062] | interval below 0.5 (descriptive) |
