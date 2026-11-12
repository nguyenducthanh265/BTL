**UCT variants: five-in-a-row 9x9**

| Agent a | Opponent b | Games | W | D | L | Score | Approx. 95% score interval | Flag |
|---|---|---|---|---|---|---|---|---|
| MCTS(1000, c=0.5, no_sqrt) | MCTS(1000, c=1.4) | 100 | 59 | 0 | 41 | 0.590 | [0.492, 0.681] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=1.0, no_sqrt) | MCTS(1000, c=1.4) | 100 | 58 | 0 | 42 | 0.580 | [0.482, 0.672] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=1.4, no_sqrt) | MCTS(1000, c=1.4) | 100 | 52 | 0 | 48 | 0.520 | [0.423, 0.615] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=2.0, no_sqrt) | MCTS(1000, c=1.4) | 100 | 49 | 0 | 51 | 0.490 | [0.394, 0.587] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=0.5, no_log) | MCTS(1000, c=1.4) | 100 | 39 | 0 | 61 | 0.390 | [0.300, 0.488] | interval below 0.5 (descriptive) |
| MCTS(1000, c=1.0, no_log) | MCTS(1000, c=1.4) | 100 | 44 | 0 | 56 | 0.440 | [0.347, 0.538] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=1.4, no_log) | MCTS(1000, c=1.4) | 100 | 38 | 0 | 62 | 0.380 | [0.291, 0.478] | interval below 0.5 (descriptive) |
| MCTS(1000, c=2.0, no_log) | MCTS(1000, c=1.4) | 100 | 24 | 0 | 76 | 0.240 | [0.167, 0.332] | interval below 0.5 (descriptive) |
| MCTS(1000, c=0.5, polynomial) | MCTS(1000, c=1.4) | 100 | 55 | 0 | 45 | 0.550 | [0.452, 0.644] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=1.0, polynomial) | MCTS(1000, c=1.4) | 100 | 46 | 0 | 54 | 0.460 | [0.366, 0.557] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=1.4, polynomial) | MCTS(1000, c=1.4) | 100 | 47 | 0 | 53 | 0.470 | [0.375, 0.567] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=2.0, polynomial) | MCTS(1000, c=1.4) | 100 | 46 | 0 | 54 | 0.460 | [0.366, 0.557] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=0.5, ucb1_tuned) | MCTS(1000, c=1.4) | 100 | 81 | 0 | 19 | 0.810 | [0.722, 0.875] | interval above 0.5 (descriptive) |
| MCTS(1000, c=1.0, ucb1_tuned) | MCTS(1000, c=1.4) | 100 | 61 | 0 | 39 | 0.610 | [0.512, 0.700] | interval above 0.5 (descriptive) |
| MCTS(1000, c=1.4, ucb1_tuned) | MCTS(1000, c=1.4) | 100 | 68 | 0 | 32 | 0.680 | [0.583, 0.763] | interval above 0.5 (descriptive) |
| MCTS(1000, c=2.0, ucb1_tuned) | MCTS(1000, c=1.4) | 100 | 53 | 0 | 47 | 0.530 | [0.433, 0.625] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=0.5, progressive_bias) | MCTS(1000, c=1.4) | 100 | 75 | 0 | 25 | 0.750 | [0.657, 0.825] | interval above 0.5 (descriptive) |
| MCTS(1000, c=1.0, progressive_bias) | MCTS(1000, c=1.4) | 100 | 53 | 0 | 47 | 0.530 | [0.433, 0.625] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=1.4, progressive_bias) | MCTS(1000, c=1.4) | 100 | 58 | 0 | 42 | 0.580 | [0.482, 0.672] | interval includes 0.5 (descriptive) |
| MCTS(1000, c=2.0, progressive_bias) | MCTS(1000, c=1.4) | 100 | 37 | 0 | 63 | 0.370 | [0.282, 0.468] | interval below 0.5 (descriptive) |
