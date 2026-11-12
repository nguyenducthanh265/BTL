**Rollout policies against Alpha-Beta: Xiangqi**

| Agent a | Opponent b | Games | W | D | L | Score | Approx. 95% score interval | Flag |
|---|---|---|---|---|---|---|---|---|
| MCTS(1000, c=1.4) | AB(d=1) | 50 | 3 | 1 | 46 | 0.070 | [0.026, 0.175] | interval below 0.5 (descriptive) |
| MCTS(1000, c=1.4, heuristic) | AB(d=1) | 50 | 13 | 0 | 37 | 0.260 | [0.159, 0.396] | interval below 0.5 (descriptive) |
| MCTS(1000, c=1.4, cutoff) | AB(d=1) | 50 | 29 | 0 | 21 | 0.580 | [0.442, 0.706] | interval includes 0.5 (descriptive) |
