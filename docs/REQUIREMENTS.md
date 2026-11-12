# Assignment requirements and acceptance map

Source: `../Bài tập lớn cho học phần AI để đánh giá giữa kỳ.docx`, read directly from its document XML on 2026-11-06 (Asia/Saigon).

Deadline stated in the source: **10 December 2026**, adjustable by the instructor. Required deliverables: an English IEEE conference-style report of at least 4-5 pages and a GitHub repository; oral examination/code questions for approximately 10-15 minutes and demos of Tic-Tac-Toe and Xiangqi.

| Requirement | Implementation / evidence |
|---|---|
| Five-in-a-row game, Minimax and Alpha-Beta, evaluation function | `gameai/games/tictactoe.py`, `gameai/search/minimax.py`, engine tests |
| MCTS with UCT and four search stages | `gameai/search/mcts.py`, `selection.py`, MCTS tests |
| Investigate the claim that 3x3 never loses | `experiments/verify_3x3.py`, exact reachable-state oracle, fixed-seed opponent-tree enumeration; finite-budget failures must be reported |
| c = 0.5, 1.0, 1.4, 2.0; iterations from 100 to 5000 | `experiments/plan.py`; actual coverage in `results/SUMMARY.md` and audit |
| At least 50 games per configuration and alternate who moves first | predefined suites use 200/100/50 games for 3x3/9x9/Xiangqi; report labels unfinished cells |
| W/D/L, nodes, time, iteration curves | raw CSV, generated tables/figures |
| Root W, N, W/N and final move chosen by visits vs mean reward | `root_stats.py`, `final` experiments, report |
| Random vs heuristic rollout | `rollout` and `rollout_vs_ab` experiments |
| Xiangqi extension and demo | `gameai/games/xiangqi.py`, perft/rules tests, local web demo; simplified draw/rollout rules documented |
| Bonus: mathematical UCT analysis, formula ablations/improvements | `docs/UCT_THEORY.md`, selection variants and `bandit.py`; unfinished variants remain outstanding |
| Bonus: another practical AI problem | Not implemented; optional extension, not claimed complete |
| IEEE report: abstract <=200 words, introduction, formal problem, methods, experiments, results, discussion | `paper/`; generated from real data; distinguish incomplete evidence from findings |
| GitHub repository | Local source available; remote creation/publication requires the owner's repository/account choice |

The assignment text's informal statement about never losing is a question to test, not permission to turn a finite stochastic observation into a proof. Perfect full-tree Minimax/Alpha-Beta supplies a separate exact baseline.
