# Final technical experiment QA — 2026-11-06

All planned match identities are present. The earlier audit describes an older snapshot;
the current frozen evidence is `results/source_data/raw/`, with the capture timestamp,
source paths, byte sizes and SHA256 hashes in `results/source_data/manifest.json`.
No additional match/node/bandit search was necessary in this review: the live files had
already completed their planned coverage. No budgets, seeds, roles or planned counts changed.

| Suite | Valid games | Planned matched | Supplementary | Balanced pairings |
|---|---:|---:|---:|---:|
| 3x3 | 43,000 | 43,000/43,000 | 0 | 215/215 |
| Five-in-row 9x9 | 6,700 | 6,700/6,700 | 0 | 67/67 |
| Xiangqi | 3,300 | 3,200/3,200 | 100 | 66/66 |

Full game replay checked **53,000 valid games**, with zero duplicate identities,
illegal moves, moves after terminal states, unfinished games, score mismatches or seed
mismatches. Every pairing has at least 50 games and equal first/second-player counts.
All planned indices, including the previously absent high-budget configurations, are
present. The 100 supplementary Xiangqi MCTS100 games remain separate from planned coverage.
Machine-readable details: `results/integrity.json`.

| Auxiliary | Exact planned coverage | Validation |
|---|---:|---|
| nodes | 173/173 rows | 162 completed searches; 10 `skipped_node_limit`; 1 `timeout` |
| nodes 3x3 | 9/9 | all completed |
| nodes Gomoku | 120/120 | 109 completed, 10 limit skips, 1 timeout |
| nodes Xiangqi | 44/44 | all completed |
| root statistics | 60/60 searches, 1,905 child rows | legal unique moves; sum N=iterations; one chosen move; rounded W/N and UCT consistent |
| move quality | 27/27 iteration/seed runs | 4,520 reachable nonterminal positions per run |
| exhaustive opponent | 280/280 iteration/role/seed runs | nonnegative outcome counts summing to recorded lines |
| bandit | 18/18 setting/strategy/c runs; 1,092/1,092 checkpoints | 1,000 seeds/run; 100,000-pull horizon; all initial checkpoints present |

`results/auxiliary_integrity.json` records zero absent, off-plan or duplicate auxiliary
identities and no stored-invariant errors. Root W, W/N and UCT are independently rounded
to four decimals; comparison propagates the stored W rounding error through division by N.
This auxiliary audit checks stored results and configurations; it does not repeat every search.

Node **coverage is complete**, while only **162 searches completed successfully**. The
11 bounded failures are retained. They are excluded from finished-search means, and partly
measured depths are omitted from graph lines. The generated QA summary therefore correctly
contains **35 OK / 2 PARTIAL / 0 MISSING**: `tables/nodes_gomoku9` and
`figures/nodes_depth` remain PARTIAL. No reruns with raised limits were used to erase failures.

The prior raw bytes, frozen snapshot, integrity output, tables and figures were copied to
`results/archive/review-20261106/` before regeneration. Its manifest preserves hashes of
77 archived files. All eight current raw CSVs remain byte-identical to their pre-review
archive copies and current frozen copies; `results/snapshot_integrity.json` records that check.
The current generated outputs contain 30 Markdown tables, 30 TeX table fragments, seven
PNG figures and seven PDF figures. These are reproducible technical QA artifacts.

Nodes and bandit entrypoints now resume by full configuration/checkpoint identity and
append only missing evidence. They preserve existing rows, including explicit failures,
reject duplicate or unplanned identities and unterminated records, and leave complete
files byte-identical. Bandit recovery uses the original deterministic seed for each run
and checks overlapping checkpoints against a seeded replay before appending that run.
No-op runs against both completed live files passed without changing either file.

Validation commands:

```powershell
python -X utf8 -m pytest tests/test_experiments.py tests/test_report.py -q -p no:cacheprovider
python -X utf8 -m experiments.report
python -X utf8 -m experiments.audit --raw results/source_data/raw --out results/integrity.json
python -X utf8 -m experiments.audit_auxiliary --raw results/source_data/raw --out results/auxiliary_integrity.json
```

Targeted tests: **46 passed**. Added regression checks cover append-only resumption,
preservation of skipped rows, deterministic checkpoint conflict rejection, no-op completion,
corrupt root visit counts and duplicate bandit checkpoints. Visual QA checked the nodes,
Xiangqi curve and bandit figures; bandit axes use separate lines and legends to avoid
overlapping panel labels.

Scientific limits remain: score Wilson intervals with draws are approximate/descriptive;
overlapping intervals establish no equality claim; the many formula/c cells invite selection
noise; correlated exhaustive opponent paths do not yield independent binomial trials; zero
observed losses cannot prove finite-budget MCTS perfect. Xiangqi uses the documented
simplified rules and draw limits. Technical coverage completion does not remove those limits.
