**Final-move rule (W/N against most visited): five-in-a-row 9x9**

| Agent a | Opponent b | Games | W | D | L | Score | Approx. 95% score interval | Flag |
|---|---|---|---|---|---|---|---|---|
| MCTS(100, c=1.4, max_ratio) | MCTS(100, c=1.4) | 100 | 50 | 0 | 50 | 0.500 | [0.404, 0.596] | interval includes 0.5 (descriptive) |
| MCTS(500, c=1.4, max_ratio) | MCTS(500, c=1.4) | 100 | 61 | 0 | 39 | 0.610 | [0.512, 0.700] | interval above 0.5 (descriptive) |
| MCTS(2000, c=1.4, max_ratio) | MCTS(2000, c=1.4) | 0/100 | - | - | - | - | - | no data |
