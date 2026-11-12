**Win/draw/loss: Xiangqi**

| Agent a | Opponent b | Games | W | D | L | Score | As 1st / 2nd | Approx. 95% score interval | Flag |
|---|---|---|---|---|---|---|---|---|---|
| MCTS(1000, c=1.4, cutoff) | Random | 50 | 47 | 3 | 0 | 0.970 | 0.94 / 1.00 | [0.880, 0.993] | interval above 0.5 (descriptive) |
| MCTS(1000, c=1.4, cutoff) | AB(d=1) | 50 | 27 | 1 | 22 | 0.550 | 0.62 / 0.48 | [0.413, 0.679] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=1.4, cutoff) | AB(d=2) | 50 | 0 | 0 | 50 | 0.000 | 0.00 / 0.00 | [0.000, 0.071] | interval below 0.5 (descriptive) |
| MCTS(5000, c=1.4, cutoff) | Random | 50 | 50 | 0 | 0 | 1.000 | 1.00 / 1.00 | [0.929, 1.000] | interval above 0.5 (descriptive) |
| MCTS(5000, c=1.4, cutoff) | AB(d=1) | 50 | 46 | 1 | 3 | 0.930 | 0.90 / 0.96 | [0.825, 0.974] | interval above 0.5 (descriptive) |
| MCTS(5000, c=1.4, cutoff) | AB(d=2) | 50 | 4 | 3 | 43 | 0.110 | 0.10 / 0.12 | [0.050, 0.226] | interval below 0.5 (descriptive) |
| MCTS(100, c=1.4, cutoff) | Random | 50 | 33 | 14 | 3 | 0.800 | 0.82 / 0.78 | [0.670, 0.888] | interval above 0.5 (descriptive) |
| MCTS(100, c=1.4, cutoff) | AB(d=1) | 50 | 7 | 0 | 43 | 0.140 | 0.16 / 0.12 | [0.070, 0.262] | interval below 0.5 (descriptive) |
