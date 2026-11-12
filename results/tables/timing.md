**Mean time per move, measured under parallel load**

| Game | Agent | Agent-games | Moves | ms per move |
|---|---|---|---|---|
| gomoku9 | AB(d=1, r=1) | 200 | 1098 | 2.12 |
| gomoku9 | AB(d=2, r=2) | 1100 | 6564 | 38.12 |
| gomoku9 | MCTS(100, c=1.4) | 300 | 3588 | 14.10 |
| gomoku9 | MCTS(200, c=1.4) | 200 | 1747 | 31.91 |
| gomoku9 | MCTS(220, c=1.4, heuristic) | 100 | 988 | 173.99 |
| gomoku9 | MCTS(500, c=1.4, cutoff) | 100 | 639 | 239.81 |
| gomoku9 | MCTS(500, c=1.4) | 2700 | 27424 | 84.94 |
| gomoku9 | MCTS(1000, c=1.4, cutoff) | 200 | 1314 | 427.08 |
| gomoku9 | MCTS(1000, c=1.4, heuristic) | 200 | 1371 | 870.59 |
| gomoku9 | MCTS(1000, c=1.4) | 3100 | 26939 | 184.68 |
| gomoku9 | MCTS(2000, c=1.4) | 300 | 2232 | 364.29 |
| gomoku9 | MCTS(5000, c=1.4) | 500 | 3262 | 953.73 |
| ttt3 | AB(d=full) | 200 | 896 | 29.00 |
| ttt3 | MCTS(10, c=1.4, heuristic) | 200 | 748 | 0.71 |
| ttt3 | MCTS(10, c=1.4) | 1000 | 3510 | 0.31 |
| ttt3 | MCTS(25, c=1.4, heuristic) | 200 | 787 | 1.54 |
| ttt3 | MCTS(25, c=1.4) | 1000 | 3691 | 0.81 |
| ttt3 | MCTS(50, c=1.4, heuristic) | 200 | 832 | 3.05 |
| ttt3 | MCTS(50, c=1.4) | 1000 | 3890 | 1.40 |
| ttt3 | MCTS(100, c=1.4, heuristic) | 200 | 857 | 6.17 |
| ttt3 | MCTS(100, c=1.4) | 1000 | 4003 | 3.47 |
| ttt3 | MCTS(200, c=1.4, heuristic) | 200 | 873 | 9.11 |
| ttt3 | MCTS(200, c=1.4) | 1000 | 4105 | 6.13 |
| ttt3 | MCTS(500, c=1.4) | 400 | 1536 | 13.52 |
| ttt3 | MCTS(1000, c=1.4) | 1000 | 3992 | 28.20 |
| ttt3 | MCTS(2000, c=1.4) | 400 | 1556 | 66.27 |
| ttt3 | MCTS(5000, c=1.4) | 400 | 1562 | 147.58 |
| xiangqi | AB(d=1) | 300 | 8581 | 6.29 |
| xiangqi | AB(d=2) | 500 | 16179 | 59.24 |
| xiangqi | AB(d=3) | 50 | 1544 | 577.95 |
| xiangqi | MCTS(100, c=1.4, cutoff) | 200 | 9410 | 64.58 |
| xiangqi | MCTS(200, c=1.4, cutoff) | 100 | 3976 | 108.42 |
| xiangqi | MCTS(500, c=1.4, cutoff) | 2400 | 115668 | 250.03 |
| xiangqi | MCTS(500, c=1.4, heuristic) | 50 | 2957 | 364.48 |
| xiangqi | MCTS(500, c=1.4) | 100 | 5357 | 1416.59 |
| xiangqi | MCTS(1000, c=1.4, cutoff) | 300 | 10695 | 539.25 |
| xiangqi | MCTS(1000, c=1.4, heuristic) | 50 | 1310 | 616.13 |
| xiangqi | MCTS(1000, c=1.4) | 50 | 1543 | 2443.76 |
| xiangqi | MCTS(2000, c=1.4, cutoff) | 100 | 4042 | 1014.24 |
| xiangqi | MCTS(5000, c=1.4, cutoff) | 250 | 9034 | 2462.64 |
