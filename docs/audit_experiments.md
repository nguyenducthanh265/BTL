# Experiment audit ? final frozen snapshot

Snapshot captured at **2026-11-06 08:47:05 UTC (15:47:05 Asia/Saigon)**. All tables, figures and counts below use `results/source_data/raw/`, with source paths, byte counts and SHA256 in `results/source_data/manifest.json`. Live `results/raw/gomoku9.csv` continued growing under a pre-existing experiment process. No second Gomoku/nodes/bandit writer was launched. Each CSV was captured once; capture is per-file, not a transaction across external writers. The final frozen snapshot was not refreshed after this audit.

## Match coverage

| Suite | Frozen valid rows | Planned identities matched | Missing planned games | Supplementary games | Pairings with ?50 games | Balanced first/second pairings |
|---|---:|---:|---:|---:|---:|---:|
| 3x3 | 43,000 | 43,000/43,000 | 0 | 0 | 215/215 | 215/215 |
| Five-in-row 9x9 | 4,590 | 4,590/6,700 | 2,110 | 0 | 46/46 observed | 46/46 observed |
| Xiangqi | 150 | 50/3,200 | 3,150 | 100 | 3/3 observed | 3/3 observed |

Balanced observed groups are not evidence that absent planned groups exist. The partially collected Gomoku formula pairing has 90/100 games; all other observed Gomoku pairings have 100. Pairing indices, rather than only row counts, determine completion.

| Experiment | 3x3 matched/planned | Five-in-row matched/planned | Xiangqi matched/planned |
|---|---:|---:|---:|
| curve | 7,200/7,200 | 1,600/2,400 | 0/1,200 |
| curve_perfect | 7,200/7,200 | ? | ? |
| WDL | 600/600 | 300/600 | 0/300 (+100 supplementary) |
| AB ladder | ? | 500/600 | 0/300 |
| AB self/sanity | ? | ? | 50/100 |
| rollout | 2,000/2,000 | 400/400 | 0/100 |
| rollout against AB | ? | 300/300 | 0/150 |
| final N versus W/N | 2,000/2,000 | 200/300 | 0/50 |
| UCT formula variants | 24,000/24,000 | 1,290/2,000 | 0/1,000 |
| radius | ? | 0/100 | ? |

The plan includes c={0.5,1,1.4,2} and iterations={100,200,500,1000,2000,5000}; 3x3 also includes lower budgets. These are planned ranges, not a claim that all three games have measured all points. Xiangqi currently has no measured c/iteration curve or UCT/rollout/final-rule comparison.

## New bounded Xiangqi measurements

All use the default game constructor (200-ply cap, repetition/no-capture draw rules) and 25 games per starting role. Existing game/search parameters were not weakened.

| Pairing | Plan status | W | D | L | Score | Run wall time, 4 workers |
|---|---|---:|---:|---:|---:|---:|
| MCTS cutoff100 vs random | supplementary WDL | 33 | 14 | 3 | .800 | 78s |
| MCTS cutoff100 vs AB depth1 | supplementary WDL | 7 | 0 | 43 | .140 | 29s |
| AB depth2 vs random | planned ab_self | 50 | 0 | 0 | 1.000 | 28s |

The two MCTS100 pairings are deliberately not counted toward the plan?s MCTS1000/5000 WDL requirement. Across 150 Xiangqi games, 15 reached 200 plies and 14 of those were draws: reaching the ply threshold alone does not imply a draw. The current CSV does not encode a draw-reason field, so cap-caused versus other draw reasons cannot be established individually.

## Auxiliary coverage

| Dataset | Actual coverage | Status |
|---|---|---|
| nodes.csv | 114/173 planned searches, all present rows `ok` | partial; missing 45 Gomoku and 14 Xiangqi searches |
| nodes 3x3 | 9/9 searches | complete |
| nodes Gomoku | 75/120 searches | partial |
| nodes Xiangqi | 30/44 searches | partial |
| root_stats.csv | 1,905 child rows across 60/60 position?iteration?seed searches | complete |
| verify_quality.csv | 27/27 iteration?seed runs; 4,520 reachable nonterminal positions/run | complete |
| verify_exhaustive.csv | 280/280 iteration?role?seed runs | complete |
| bandit.csv | 897 checkpoint rows, 15/18 setting?strategy?c runs | partial; missing two_arms epsilon_greedy, ucb1 c=.5, no_sqrt c=.5 |

Root groups all have sum(child N)=iterations, exactly one chosen child, and W/N rounding error ?0.00005. Existing bandit data omit the initial arm-pull checkpoint due to the prior simulator behavior; the simulator now records it for future runs. That edit does not change or fabricate existing rewards/regret rows. Minimax/AB agreement is checked only on positions with at least two finished searches; incomplete depths are omitted from plotted means.

## Correctness fixes

- Shared record validation now checks JSON moves, move-count/plies agreement, alternate-role parity, legal score values, nonnegative finite timings, node counts, identity and seeds as integers. Report, resume and missing-game counts use the same validation and canonical JSON identities. Invalid newline-terminated records no longer cause resume to skip the missing game.
- Full frozen game logs were replayed against game rules and independently checked for deterministic seed identity and recorded score. `results/integrity.json` records **47,740 valid match rows, zero duplicate identities, zero illegal moves, zero moves after terminal states, zero unfinished games, zero score mismatches and zero seed mismatches**.
- Missing node rows, root iteration/seed groups, quality iteration/seed/position coverage, exhaustive role/seed coverage and absent bandit runs now mark artifacts PARTIAL. A present CSV alone cannot imply suite completion.
- Fractional-score Wilson intervals are explicitly approximate/descriptive, with no guaranteed 95% coverage for draws. Flags mean only that an interval is above/below/includes .5. No pairwise significance or equality claim is made. Wilson on actual loss rates remains a Bernoulli summary.
- The correlated opponent leaf paths do not justify a 95% rule-of-three bound. `3/lines` is labeled a dependent heuristic; independent run seeds are the relevant approximate unit for `3/runs`. Zero observed failures are not proof of perfection.
- Reports first freeze input bytes and hashes, so a growing raw CSV cannot change later tables in the same build. Six figures were generated from measured data, with gaps/missing heatmap cells preserved.

## Validation and artifacts

Commands executed:

```powershell
python -X utf8 -m pytest tests/test_experiments.py tests/test_report.py -q -p no:cacheprovider
python -X utf8 -m experiments.report
python -X utf8 -m experiments.audit --raw results/source_data/raw --out results/integrity.json
```

Final targeted tests: **40 passed in 29.55s**. Initial unchanged targeted suite: 33 passed. The cache provider was disabled on final validation because the existing `.pytest_cache` directory was not writable. Replay audit exited 0. Final report: **15 OK / 14 PARTIAL / 8 MISSING**, 23 Markdown+TeX tables and six PNG+PDF figures. `nodes_depth.png` and `formula_heatmap_gomoku9.png` were visually inspected; gaps represent absent measured data.

To reproduce the frozen numbers without touching the final artifacts or following the live writer:

```powershell
python -X utf8 -m experiments.report --raw results/source_data/raw --out results/reproduction
python -X utf8 -m experiments.audit --raw results/source_data/raw --out results/reproduction/integrity.json
```

## Remaining workload and resumable commands

Do not start a second writer while a pre-existing process still owns the same live CSV. The following match runner commands are resumable after that process exits; they re-check completed valid identities before scheduling games:

```powershell
python -X utf8 -m experiments.runner --suite gomoku9 --workers 4
python -X utf8 -m experiments.runner --suite xiangqi --workers 4
# Narrow planned batches can be resumed separately:
python -X utf8 -m experiments.runner --suite xiangqi --exp wdl --workers 4
python -X utf8 -m experiments.runner --suite xiangqi --exp ab_self --workers 4
```

At the frozen snapshot, Gomoku has **2,110 planned games** remaining, totaling **7,220,000 MCTS iteration/game units**. A measured rate from the earlier frozen subset (9,280 agent-seconds / 4,604,000 units) projects roughly **4.0 aggregate agent-hours**, or about one hour on four fully available workers. This is an estimate, not a deadline: policies, longer games, contention and algorithm costs differ, and the live process may already have reduced the backlog.

Xiangqi has **3,150 planned games** remaining. The full unmeasured MCTS part totals **5,000,000 iteration/game units**. Measured cutoff100 mean agent time was 1.912s/game against AB1 versus 5.832s/game against random; linear scaling gives approximately **26.6?81 aggregate agent-hours**, or **6.6?20.3 wall hours at four workers**, before AB2/AB3 costs and nonlinear game-length changes. These rough extrapolations do not establish high-budget behavior. No hours-long suite was started during this audit.

The auxiliary `nodes.main()` and `bandit.main()` programs currently overwrite their target output and are not resumable. Do not rerun them over frozen evidence. Completing their absent entries should use a separate output path and an explicit bounded job, then merge by full configuration identity only after validation. Nodes has a 660-second total budget and per-search 60-second timeout; it can legitimately produce skip/timeout statuses. No cost estimate for absent deep searches or missing bandit runs has been measured here.

The assignment is **PARTIAL overall**. Completed 3x3 and observed ?50-game baseline cells do not substitute for absent Gomoku/Xiangqi configurations.
