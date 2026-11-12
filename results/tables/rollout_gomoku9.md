**Rollout policies: five-in-a-row 9x9**

| Agent a | Opponent b | Games | W | D | L | Score | Approx. 95% score interval | Flag |
|---|---|---|---|---|---|---|---|---|
| MCTS(1000, c=1.4, heuristic) | MCTS(1000, c=1.4) | 100 | 70 | 0 | 30 | 0.700 | [0.604, 0.781] | interval above 0.5 (descriptive) |
| MCTS(1000, c=1.4, cutoff) | MCTS(1000, c=1.4) | 100 | 99 | 0 | 1 | 0.990 | [0.946, 0.998] | interval above 0.5 (descriptive) |
| MCTS(220, c=1.4, heuristic) | MCTS(1000, c=1.4) | 100 | 51 | 0 | 49 | 0.510 | [0.413, 0.606] | interval includes 0.5 (descriptive) |
| MCTS(500, c=1.4, cutoff) | MCTS(1000, c=1.4) | 100 | 93 | 0 | 7 | 0.930 | [0.863, 0.966] | interval above 0.5 (descriptive) |
