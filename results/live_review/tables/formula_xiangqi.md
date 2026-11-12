**UCT variants: Xiangqi**

| Agent a | Opponent b | Games | W | D | L | Score | Approx. 95% score interval | Flag |
|---|---|---|---|---|---|---|---|---|
| MCTS(500, c=0.5, no_sqrt, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 29 | 4 | 17 | 0.620 | [0.482, 0.741] | interval includes 0.5 (descriptive) |
| MCTS(500, c=1.0, no_sqrt, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 27 | 7 | 16 | 0.610 | [0.472, 0.733] | interval includes 0.5 (descriptive) |
| MCTS(500, c=1.4, no_sqrt, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 19 | 7 | 24 | 0.450 | [0.321, 0.587] | interval includes 0.5 (descriptive) |
| MCTS(500, c=2.0, no_sqrt, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 17 | 6 | 27 | 0.400 | [0.276, 0.538] | interval includes 0.5 (descriptive) |
| MCTS(500, c=0.5, no_log, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 15 | 5 | 30 | 0.350 | [0.233, 0.489] | interval below 0.5 (descriptive) |
| MCTS(500, c=1.0, no_log, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 21 | 8 | 21 | 0.500 | [0.366, 0.634] | interval includes 0.5 (descriptive) |
| MCTS(500, c=1.4, no_log, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 17 | 4 | 29 | 0.380 | [0.259, 0.518] | interval includes 0.5 (descriptive) |
| MCTS(500, c=2.0, no_log, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 15 | 5 | 30 | 0.350 | [0.233, 0.489] | interval below 0.5 (descriptive) |
| MCTS(500, c=0.5, polynomial, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 30 | 1 | 19 | 0.610 | [0.472, 0.733] | interval includes 0.5 (descriptive) |
| MCTS(500, c=1.0, polynomial, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 21 | 6 | 23 | 0.480 | [0.348, 0.615] | interval includes 0.5 (descriptive) |
| MCTS(500, c=1.4, polynomial, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 19 | 6 | 25 | 0.440 | [0.312, 0.577] | interval includes 0.5 (descriptive) |
| MCTS(500, c=2.0, polynomial, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 19 | 11 | 20 | 0.490 | [0.357, 0.624] | interval includes 0.5 (descriptive) |
| MCTS(500, c=0.5, ucb1_tuned, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 45 | 2 | 3 | 0.920 | [0.812, 0.968] | interval above 0.5 (descriptive) |
| MCTS(500, c=1.0, ucb1_tuned, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 29 | 6 | 15 | 0.640 | [0.501, 0.759] | interval above 0.5 (descriptive) |
| MCTS(500, c=1.4, ucb1_tuned, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 26 | 8 | 16 | 0.600 | [0.462, 0.724] | interval includes 0.5 (descriptive) |
| MCTS(500, c=2.0, ucb1_tuned, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 22 | 6 | 22 | 0.500 | [0.366, 0.634] | interval includes 0.5 (descriptive) |
| MCTS(500, c=0.5, progressive_bias, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 40 | 2 | 8 | 0.820 | [0.692, 0.902] | interval above 0.5 (descriptive) |
| MCTS(500, c=1.0, progressive_bias, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 28 | 7 | 15 | 0.630 | [0.491, 0.750] | interval includes 0.5 (descriptive) |
| MCTS(500, c=1.4, progressive_bias, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 28 | 5 | 17 | 0.610 | [0.472, 0.733] | interval includes 0.5 (descriptive) |
| MCTS(500, c=2.0, progressive_bias, cutoff) | MCTS(500, c=1.4, cutoff) | 50 | 30 | 6 | 14 | 0.660 | [0.522, 0.776] | interval above 0.5 (descriptive) |
