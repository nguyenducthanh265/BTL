# PLAN - technical release 1.1.0

Current scope: finish technical implementation, QA and runtime delivery. The owner explicitly deferred report writing, author details and GitHub publication.

- [x] Square placement-game engines, generalized k, geometry validation and bounded evaluation
- [x] Minimax / Alpha-Beta, exact 3x3 tablebase and all-best-action checks
- [x] MCTS-UCT, five alternatives, three rollouts and finite-budget failure regressions
- [x] Xiangqi legal tree, documented simplified draw/rollout model, perft depths 1-4
- [x] Complete planned 3x3 grid: 43,000 / 43,000 games
- [x] Complete planned 9x9 grid: 6,700 / 6,700 games
- [x] Complete planned Xiangqi grid: 3,200 / 3,200 games, plus 100 supplementary games
- [x] Full replay audit of 53,000 records; zero rule/outcome/seed/duplicate errors
- [x] Node configurations: 173 / 173 recorded, with 162 successes, ten node-limit skips and one timeout explicitly retained
- [x] Bandit controls: all 18 runs; 1,092 checkpoint records
- [x] Complete root-stat, move-quality and exhaustive-opponent verification identities
- [x] Append-only node/bandit resume; deterministic overlap checks and byte-preserving no-op reruns
- [x] Preserve old snapshot, freeze final inputs with SHA256 and regenerate technical tables/figures
- [x] Real HTTP demo tests, emulated-touch QA at 390x844 and 360x800, 44px coarse-pointer targets and board-local scrolling
- [x] Final integrated test command:324 passed; independent release review:0 open findings
- [x] Runtime wheel1.1.0 and source ZIP verified:source parity,isolatedHTTP/MCTS/Xiangqi,all planned suites resume0 and per-file hashes

## Deferred by the owner

- Report revision/IEEE compilation and author metadata
- GitHub repository choice/publication
- Optional second practical AI problem

Physical-device touch is not certified by browser emulation. Tournament Xiangqi adjudication is outside the implemented simplified model. Explicit benchmark skips/timeouts remain evidence, not successful measurements. These documented limits do not imply missing game-suite identities.
