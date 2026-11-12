# Game AI: technical release 1.1.0

Local Vietnamese web demo and reproducible search experiments for Tic-Tac-Toe, freestyle five-in-a-row and simplified Xiangqi. The current scope is code, runtime, tests and validated data. Report authorship, report revision and GitHub publication are deferred by the owner.

## Install and play

Requires Python 3.10+. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m gameai.demo
```

Open http://127.0.0.1:8000. Choose a game, side and algorithm. Xiangqi uses piece selection followed by a highlighted destination. The demo works offline after installation. Use `--port 8765` to change ports. Begin larger games with a modest search budget; high iteration/depth values can require substantial computation.

The mobile layout is tested with emulated touch viewports. Dense boards preserve reachable targets using board-local horizontal scrolling. A visible hint identifies when the board can be swiped. Browser emulation does not certify physical touch hardware; exact evidence is in [final demo QA](docs/final_demo.md).

Reset/undo discard obsolete browser responses. They do not cancel Python computation already running on the server. This server is intended for local demonstration, not an Internet-facing multi-user service.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q
python -m experiments.audit --raw results/source_data/raw --out results/integrity.json
python -m experiments.audit_auxiliary --raw results/source_data/raw --out results/auxiliary_integrity.json
```

See [technical status](docs/TECHNICAL_STATUS.md) and [test output](docs/verification-technical.log) for the final verified count. Tests cover game rules/apply-undo, independent exact 3x3 values, Minimax/Alpha-Beta equivalence, MCTS formulas/rewards, Xiangqi perft, HTTP requests, CSV resume and truthful data coverage.

## Experiment data

The frozen technical snapshot contains **53,000 valid unique games**: **43,000/43,000** planned 3x3 games, **6,700/6,700** planned 9x9 games, **3,200/3,200** planned Xiangqi games, plus 100 supplementary Xiangqi games. Full rule replay checks moves, terminal outcomes, scores, deterministic seeds and duplicate identities. Four fresh seeded game regenerations additionally match current search results; this is sampled producer-code verification, not a rerun of all historical AI decisions.

All 173 node-experiment configurations have records: **162 successful measurements, ten node-limit skips and one timeout**. These statuses remain visible. Bandit controls cover all 18 runs. Root statistics and both 3x3 verification grids have complete planned identities. Generated output is **35 OK / 2 PARTIAL / 0 MISSING**; the two partial outputs expose bounded node measurements, not missing match suites.

- Fixed inputs: `results/source_data/raw/`; byte counts and SHA256 in its [manifest](results/source_data/manifest.json).
- Match checks: [integrity](results/integrity.json); auxiliary checks: [auxiliary integrity](results/auxiliary_integrity.json).
- Derived tables/figures: [results summary](results/SUMMARY.md).
- Superseded review evidence is retained under `results/archive/review-20261106/` in the workspace.
- [Experiment completion](docs/final_experiments.md) and [independent data cross-checks](docs/final_findings.md) explain scope and limitations.

## Reproduce or resume

```powershell
python -m experiments.runner --suite ttt3 --workers 4
python -m experiments.runner --suite gomoku9 --workers 4
python -m experiments.runner --suite xiangqi --workers 4
python -m experiments.nodes
python -m experiments.bandit
```

Match suites skip valid completed identities. Node/bandit runners append only missing configurations/checkpoints and retain prior successes, skips and failures. Completed auxiliary reruns preserve input bytes. Use one writer per CSV. To rerun an already recorded node failure with another budget, use a new output path and retain the original evidence.

`python -m experiments.root_stats` and `python -m experiments.verify_3x3 --workers 4` regenerate their own auxiliary files; preserve the frozen snapshot and avoid concurrent writers.

To reproduce derived output without changing the delivered snapshot:

```powershell
python -m experiments.report --raw results/source_data/raw --out results/reproduction
```

This freezes a separate input copy before deriving figures/tables. Do not set the output so that its snapshot directory is the same as its input directory. Historical reports/PDFs in the workspace are not updated by this technical release.

## Algorithm limits

- Finite-budget MCTS can lose even at 3x3; exact full-depth Minimax/Alpha-Beta provides a separate non-losing baseline from the empty 3x3 board.
- Node W is total reward (win=1, draw=0.5, loss=0). W in a W/D/L table is a literal win count.
- Fractional-score Wilson intervals are approximate descriptive displays, not guaranteed 95% score intervals or significance tests. Opponent-tree leaf paths are dependent.
- Placement games use square boards, runs of at least k and freestyle rules. Candidate-radius search discards legal actions; depth-limited evaluation is approximate.
- Xiangqi tree decisions use legal moves, with simplified repetition/no-capture/ply-cap draws. Faster rollouts use pseudo-legal actions and omit full draw adjudication. No tournament-strength claim is made.
- Recorded wall times reflect parallel machine load. Equal iteration counts need not mean equal compute.

## Deliverables

`output/packages/` contains the runtime wheel and the portable technical source ZIP. The ZIP includes code, tests, fixed CSVs, audit evidence and a per-file SHA256 manifest. It excludes build tools, caches, archives and the deferred report outputs. The `paper/build.py` module is included only to support its existing data-loader regression test; report authoring assets are outside this bundle.

To rebuild the runtime wheel on a normally provisioned machine:

```powershell
python -m pip wheel . --no-deps --wheel-dir dist
```

To rebuild the technical source bundle after checks:

```powershell
python scripts/package_release.py
```

See [PLAN.md](PLAN.md) for technical completion and the explicitly deferred academic/publication work.
