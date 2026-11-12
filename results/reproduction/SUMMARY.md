# Results summary

OK 15, PARTIAL 14, MISSING 8. PARTIAL means some planned games or searches are absent; they are marked in the table, not filled in. MISSING means no file was produced. Each table is a .md and a .tex file, each figure a .png and a .pdf.

## Data found

- ttt3: 43000 of 43000 planned games (complete).
- gomoku9: 4590 of 6700 planned games (PARTIAL).
- xiangqi: 50 of 3200 planned games (PARTIAL).
- 100 games belong to pairings that are not in experiments/plan.py.
- xiangqi: 15 of 150 games reached 200 plies; 14 of those ended as draws. Draw reasons are not recorded in CSV.
- nodes.csv: found.
- root_stats.csv: found.
- bandit.csv: found.
- verify_quality.csv: found.
- verify_exhaustive.csv: found.

## How to read the numbers

- Score = (W + 0.5 D) / games, from agent a's side. a_score already is from a's side, so who moved first does not change W, D or L.
- The interval is a nominal 95% Wilson interval applied to fractional scores. "interval includes 0.5 (descriptive)" is only a display flag meaning that interval contains 0.5; it is not a pairwise test between configurations, proof of equality, or an adjustment for multiple comparisons.
- With draws, scores are not Bernoulli observations, so these Wilson intervals are an approximation without guaranteed 95% coverage. An all-draw cell still shows a wide interval around 0.5. Seeds alternate first/second roles; these are not identical game distributions.
- Many configurations are summarized with no correction; rankings and interval flags are descriptive, and selecting the highest observed score can overstate performance.
- Partial cells may lean towards short games, because the runner writes games as they finish. Treat them as provisional.
- Node counts: `search()` widens the root window to find ALL equally best moves, so Alpha-Beta visits more nodes than the textbook version that keeps one best move. Midgame positions come from seeded random play, not from strong games, and Minimax entries above the node limit are marked skipped.
- Zero observed losses is evidence, not proof. The rule of three says: with zero failures in N independent trials, the failure rate is below about 3/N with 95% confidence. The lines of one exhaustive run share the agent's decisions, so they are not independent and 3/lines is only a heuristic, not a valid 95% bound; 3/runs treats each whole run as one trial and is the safer approximate figure (under independent run seeds). Neither excludes a rarer failure, because MCTS is randomised and only a finite number of runs exists.
- Timing was measured with other games running in parallel, so it is only a rough guide.

## Tables

- **OK** `tables/nodes_ttt3`: 9 searches, 0 not run or stopped (marked as skipped k/n). 0 planned searches have no CSV row. Finished algorithms agree on value and best moves in 3 comparable cases; 0 cases have only one finished algorithm. Nodes are means over positions, which vary a lot: see nodes.csv. Ratios use only positions where both searches finished. Ordering increased nodes at: centre (d=full).
- **PARTIAL** `tables/nodes_gomoku9`: 75 searches, 0 not run or stopped (marked as skipped k/n). 45 planned searches have no CSV row. Finished algorithms agree on value and best moves in 25 comparable cases; 0 cases have only one finished algorithm. Nodes are means over positions, which vary a lot: see nodes.csv. Ratios use only positions where both searches finished.
- **PARTIAL** `tables/nodes_xiangqi`: 30 searches, 0 not run or stopped (marked as skipped k/n). 14 planned searches have no CSV row. Finished algorithms agree on value and best moves in 10 comparable cases; 0 cases have only one finished algorithm. Nodes are means over positions, which vary a lot: see nodes.csv. Ratios use only positions where both searches finished.
- **OK** `tables/curve_ttt3`: At 5000 iterations (200 games): highest c=0.5 0.985, lowest c=2.0 0.963: intervals overlap (descriptive).
- **OK** `tables/curve_perfect_ttt3`: At 5000 iterations (200 games): highest c=0.5 0.000, lowest c=0.5 0.000: intervals overlap (descriptive).
- **OK** `tables/wdl_ttt3`: 3 of 3 pairings have games; 1 intervals above 0.5, 0 below 0.5, 2 include 0.5 (descriptive). Highest score: MCTS(1000, c=1.4) vs Random, 0.978 [0.946, 0.991]. Against a perfect player 0.5 is the best possible score.
- **OK** `tables/rollout_ttt3`: 10 of 10 pairings have games; 0 intervals above 0.5, 10 below 0.5, 0 include 0.5 (descriptive). Highest score: MCTS(200, c=1.4, heuristic) vs Perfect, 0.425 [0.359, 0.494]. Against a perfect player 0.5 is the best possible score.
- **OK** `tables/final_ttt3`: 10 of 10 pairings have games; 0 intervals above 0.5, 10 below 0.5, 0 include 0.5 (descriptive). Highest score: MCTS(200, c=1.4) vs Perfect, 0.415 [0.349, 0.484]. Against a perfect player 0.5 is the best possible score.
- **OK** `tables/formula_ttt3`: 120 of 120 pairings have games; 0 intervals above 0.5, 118 below 0.5, 2 include 0.5 (descriptive). Highest score: MCTS(200, c=0.5, progressive_bias) vs Perfect, 0.438 [0.371, 0.507]. Against a perfect player 0.5 is the best possible score.
- **PARTIAL** `tables/curve_gomoku9`: At 1000 iterations (100 games): highest c=0.5 0.870, lowest c=2.0 0.640: intervals do not overlap (descriptive). Self-play check (MCTS(500, c=1.4) against itself): 0.590 [0.492, 0.681], which should contain 0.5.
- **PARTIAL** `tables/wdl_gomoku9`: 3 of 6 pairings have games; 1 intervals above 0.5, 2 below 0.5, 0 include 0.5 (descriptive). Highest score: MCTS(1000, c=1.4) vs Random, 1.000 [0.963, 1.000].
- **PARTIAL** `tables/ab_ladder_gomoku9`: 5 of 6 pairings have games; 0 intervals above 0.5, 5 below 0.5, 0 include 0.5 (descriptive). Highest score: MCTS(100, c=1.4) vs AB(d=2, r=2), 0.000 [0.000, 0.037]. No measured iteration count has a score interval wholly above 0.5.
- **OK** `tables/rollout_gomoku9`: 4 of 4 pairings have games; 3 intervals above 0.5, 0 below 0.5, 1 include 0.5 (descriptive). Highest score: MCTS(1000, c=1.4, cutoff) vs MCTS(1000, c=1.4), 0.990 [0.946, 0.998].
- **OK** `tables/rollout_vs_ab_gomoku9`: 3 of 3 pairings have games; 0 intervals above 0.5, 3 below 0.5, 0 include 0.5 (descriptive). Highest score: MCTS(1000, c=1.4, cutoff) vs AB(d=2, r=2), 0.015 [0.003, 0.062].
- **PARTIAL** `tables/final_gomoku9`: 2 of 3 pairings have games; 1 intervals above 0.5, 0 below 0.5, 1 include 0.5 (descriptive). Highest score: MCTS(500, c=1.4, max_ratio) vs MCTS(500, c=1.4), 0.610 [0.512, 0.700].
- **PARTIAL** `tables/formula_gomoku9`: 13 of 20 pairings have games; 1 intervals above 0.5, 3 below 0.5, 9 include 0.5 (descriptive). Highest score: MCTS(1000, c=0.5, ucb1_tuned) vs MCTS(1000, c=1.4), 0.811 [0.718, 0.879].
- **MISSING** `radius_gomoku9`: no games for exp "radius", game gomoku9
- **MISSING** `curve_xiangqi`: no games for exp "curve", game xiangqi
- **PARTIAL** `tables/wdl_xiangqi`: 2 of 8 pairings have games; 1 intervals above 0.5, 1 below 0.5, 0 include 0.5 (descriptive). Highest score: MCTS(100, c=1.4, cutoff) vs Random, 0.800 [0.670, 0.888].
- **MISSING** `ab_ladder_xiangqi`: no games for exp "ab_ladder", game xiangqi
- **PARTIAL** `tables/ab_self_xiangqi`: 1 of 2 pairings have games; 1 intervals above 0.5, 0 below 0.5, 0 include 0.5 (descriptive). Highest score: AB(d=2) vs Random, 1.000 [0.929, 1.000].
- **MISSING** `rollout_xiangqi`: no games for exp "rollout", game xiangqi
- **MISSING** `rollout_vs_ab_xiangqi`: no games for exp "rollout_vs_ab", game xiangqi
- **MISSING** `final_xiangqi`: no games for exp "final", game xiangqi
- **MISSING** `formula_xiangqi`: no games for exp "formula", game xiangqi
- **OK** `tables/root_stats`: Statistics shown for seed 0, c=1.4; 'Chosen' counts seeds over all 5 seeds. Assignment position, seeds choosing the only non-losing cell 8: 100 it: 5/5 seeds; 1000 it: 5/5 seeds; 5000 it: 5/5 seeds. Missing planned position/iteration/seed searches: 0.
- **OK** `tables/verify_quality`: Blunder = a move that worsens the exact game value. Only 3191 of 4520 positions allow a blunder; the last column uses those as the denominator. Lowest iteration count with zero blunders: 2000.
- **OK** `tables/verify_exhaustive`: Iterations with zero losses against every opponent line: [2000, 5000]. Zero observed losses is evidence, not proof: see the notes above.
- **PARTIAL** `tables/bandit_regret`: easy, regret at T=100000: no_sqrt(c=0.5) 25 [wrong 0.000], ucb1(c=0.5) 51 [wrong 0.000], no_sqrt(c=1.4) 66 [wrong 0.000], ucb1(c=1.4) 355 [wrong 0.000], epsilon_greedy 2,620 [wrong 0.000], no_log(c=1.4) 23,170 [wrong 0.000]. hard, regret at T=100000: no_sqrt(c=1.4) 75 [wrong 0.000], ucb1(c=0.5) 133 [wrong 0.001], no_sqrt(c=0.5) 447 [wrong 0.081], epsilon_greedy 792 [wrong 0.000], ucb1(c=1.4) 806 [wrong 0.000], no_log(c=1.4) 6,835 [wrong 0.000]. 95% bands overlap (descriptive): epsilon_greedy and ucb1(c=1.4). two_arms, regret at T=100000: no_sqrt(c=1.4) 127 [wrong 0.048], ucb1(c=1.4) 338 [wrong 0.000], no_log(c=1.4) 990 [wrong 0.000]. 3 planned strategy/setting/c runs are missing. A ratio near 1.25 fits ln T; near 10 means linear. Wrong arm = share of seeds whose most-pulled arm at the end is not the best arm.
- **OK** `tables/timing`: Per move of the agent itself (about half of the plies). Measured while many games ran in parallel, so compare within this table only.

## Figures

- **PARTIAL** `figures/nodes_depth`: Mean nodes against depth. A depth is drawn only when every position finished, so partly skipped depths are absent. Numbers are in the nodes tables.
- **OK** `figures/curve_ttt3`: At 5000 iterations (200 games): highest c=0.5 0.985, lowest c=2.0 0.963: intervals overlap (descriptive).
- **OK** `figures/curve_perfect_ttt3`: At 5000 iterations (200 games): highest c=0.5 0.000, lowest c=0.5 0.000: intervals overlap (descriptive).
- **PARTIAL** `figures/curve_gomoku9`: At 1000 iterations (100 games): highest c=0.5 0.870, lowest c=2.0 0.640: intervals do not overlap (descriptive). Self-play check (MCTS(500, c=1.4) against itself): 0.590 [0.492, 0.681], which should contain 0.5.
- **PARTIAL** `figures/formula_heatmap_gomoku9`: 13 of 20 formula x c cells have games (90 to 100 games each); 9 intervals include 0.5 (descriptive). Highest: ucb1_tuned at c=0.5, 0.811. With this many cells the largest observed score can reflect selection noise; no pairwise significance test is made.
- **MISSING** `curve_xiangqi`: no games for exp "curve", game xiangqi
- **PARTIAL** `figures/bandit_regret`: c=1.4. easy, regret at T=100000: no_sqrt(c=0.5) 25 [wrong 0.000], ucb1(c=0.5) 51 [wrong 0.000], no_sqrt(c=1.4) 66 [wrong 0.000], ucb1(c=1.4) 355 [wrong 0.000], epsilon_greedy 2,620 [wrong 0.000], no_log(c=1.4) 23,170 [wrong 0.000]. hard, regret at T=100000: no_sqrt(c=1.4) 75 [wrong 0.000], ucb1(c=0.5) 133 [wrong 0.001], no_sqrt(c=0.5) 447 [wrong 0.081], epsilon_greedy 792 [wrong 0.000], ucb1(c=1.4) 806 [wrong 0.000], no_log(c=1.4) 6,835 [wrong 0.000]. 95% bands overlap (descriptive): epsilon_greedy and ucb1(c=1.4). two_arms, regret at T=100000: no_sqrt(c=1.4) 127 [wrong 0.048], ucb1(c=1.4) 338 [wrong 0.000], no_log(c=1.4) 990 [wrong 0.000]. 3 planned strategy/setting/c runs are missing.

Input snapshot: `results\reproduction\source_data\raw`; capture UTC 2026-11-06T08:56:50.947953+00:00. Hashes and source path are in `results\reproduction\source_data\manifest.json`. Live raw CSVs may contain later rows.
