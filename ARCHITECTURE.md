# Architecture

This is an offline search-algorithm coursework project, not a trained model or an API-backed AI application. The local `hackathon-kit` roles are adapted accordingly: `ml_engineer` owns search and controlled experiments, `fullstack_dev` owns the demo, and the coordinator owns integration and documentation. No training split, paid API, or public deployment is needed.

## Components and contracts

- `gameai/games/`: mutable game positions with `clone`, `play`, `undo`, `legal_moves`, `winner`, `evaluate`, `move_prior`, and `simulate`. Player +1 maximizes the evaluation. A winner is +1/-1, a draw is 0, and an unfinished game returns `None`.
- `gameai/search/minimax.py`: deterministic Minimax and Alpha-Beta return a value, all equally best moves, and visited-node count. Depth-limited values are heuristic; only full search on the complete legal tree establishes an exact result.
- `gameai/search/mcts.py`: a fresh tree per decision; one child is expanded per iteration. Child reward belongs to the player who moved into that child. Draw reward is 0.5. Rollout mutates a private cloned position.
- `gameai/search/selection.py`: selection formulas share `(child, parent_n, log_parent_n, c)`. Standard UCT and five alternatives use the same search implementation.
- `gameai/agents.py`: `choose(game, rng) -> move`; the caller supplies randomness. `gameai/match.py` records a complete game, timing and nodes.
- `experiments/plan.py`: the predefined parameter grid. `runner.py` derives stable seeds from configuration and game index, alternates first player, and appends resumable CSV rows. One coordinator writes each CSV.
- `experiments/report.py`: derived Markdown/LaTeX tables and PNG/PDF figures; incomplete experiments remain explicitly partial or missing.
- `gameai/demo/`: a standard-library HTTP server on `127.0.0.1:8000`. `GET /api/config` supplies controls; `POST /api/play` replays a move history, validates legal moves, and optionally computes one AI reply. The browser owns history; reset/undo do not mutate server sessions.

## Rules and limits

The five-in-a-row game uses freestyle rules: an unbroken run of at least five wins; there are no Renju restrictions or blocked-end rules. The demo also offers 15x15; the predefined experiment suite uses 9x9.

Xiangqi tree search uses legal moves, including self-check prevention. Threefold repetition, 120 non-capture plies, and a 200-ply game cap are simplified draw rules. Rollouts deliberately use pseudo-legal moves and may end by general capture; they are a simulation approximation, not another implementation of tournament play.

Candidate-radius pruning on large placement boards changes the searched action set. An Alpha-Beta result is exact only for its chosen depth and action set. Finite-budget MCTS is stochastic and has no universal never-lose guarantee.

## Integration boundaries

The engine, experiment/report, and demo workers have non-overlapping file ownership. The coordinator reruns the complete suite after integration, records checks in `docs/PROGRESS.md`, and updates `PLAN.md` using evidence rather than file existence.
