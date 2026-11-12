# Integration ledger - 2026-11-06

## Starting evidence

- Existing code and CSVs were preserved; the workspace has no Git repository.
- Kit read: `../hackathon-kit/AGENTS.md`, roles and profile guidance. None of the four supplied profiles exactly describes search coursework. Adaptation: offline experiment roles without training, external API or deployment requirements.
- Independent workers: search/engine correctness; experiments/report; demo/HTTP. Coordinator: requirements, architecture, theory, paper, README, integration checks.
- Existing data: 43,000 3x3 games, 2,556 9x9 games, 27 move-quality records, 280 opponent-enumeration records, 114 node measurements, 1,905 root-stat rows, 897 bandit rows. These counts are a starting snapshot, not provenance verification.

## Decisions

- Preserve the predefined experimental grid and partial CSV evidence. Do not shorten games, invent scores, or mark the full suite complete when data is absent.
- Do not silently replace MCTS by an exact solver to satisfy the never-lose wording.
- Produce a reviewable local paper and source; author identities and GitHub publication remain owner actions.

## Checks

- Engine worker: 115 tests including Xiangqi perft4, independent 5,478-state exact-action checks and finite-budget MCTS counterexample. Additional generalized-score regression failed before the fix and passed after it.
- Demo worker: 149 backend/HTTP tests; browser flows for 3x3, 9x9 and Xiangqi, reset/undo/late responses and narrow-board overflow. Browser tests were at a minimum observed width of 500px, not a touch-device certification.
- Experiment worker: 40 tests; frozen replay audit of 47,740 games with no illegal moves, score/seed mismatches or duplicate identities. See `results/integrity.json`.
- Final independent kit `code_reviewer`: three MEDIUM findings (generalized heuristic exceeding terminal value, paper loader counting invalid/duplicate rows, incorrect README reproduction output path). All fixed and scoped recheck APPROVE; no remaining finding in that scope.
- Paper loader regression: legacy implementation failed; shared validated loader passed. The paper now uses the same canonical game identities as the report.
- Final integrated command: `python -m pytest -p no:cacheprovider -q` -> **312 passed in 165.16s**, exit 0. Full output: `docs/verification-tests-final.log`.
- Five-page PDF generated with PyMuPDF and all pages visually inspected; abstract 113 words. Snapshot hashes matched all eight files; metrics matched the final frozen source. IEEEtran source supplied; LaTeX compilation not verified because no compiler is installed.
- Runtime wheel built; HTML asset and engine module present, isolated imports passed. Final wheel engine/frontend bytes match current source. Build required workspace-local setuptools and elevated execution because pip-created package directories were unreadable inside the sandbox; no project code change was needed for that environment issue.

## Final handoff boundary

- Frozen report input: capture `2026-11-06T08:47:05.677181+00:00` (15:47:05 Asia/Saigon), with 43,000/43,000 planned 3x3 games, 4,590/6,700 planned 9x9 games, 50/3,200 planned Xiangqi games, and 100 supplementary Xiangqi games.
- Report: 15 OK / 14 PARTIAL / 8 MISSING; 23 tables and six figures. Overall assignment remains PARTIAL.
- The owner selected **delivery of verified work**, rather than the full hours-long Xiangqi run. A briefly started supervisor PID 54460 and its runner PID 33116/worker tree were terminated, and its receipt was marked `stopped_by_user`. No new full-suite completion is claimed. The existing 9x9 process was preserved.
- `results/jobs/xiangqi_full.json` records that stopped job; `scripts/run_xiangqi_full.py` remains an optional explicit resume command. Frozen CSVs and derived review results were not refreshed from the live files.
- Outstanding: remaining match grid and auxiliary measurements, final report authors/IEEE compilation, and owner-selected GitHub publication. No remote repository was created or published.

## Technical completion pass - 2026-11-06

The owner resumed completion, then explicitly narrowed the task to technical work; report writing, author metadata and GitHub publication are deferred. Current live data had already completed all planned matches and auxiliary identities. No new long match job was needed.

Final experiment QA froze and replayed 53,000 games, validated all auxiliary identities, preserved prior 77 archived artifacts and the eight raw CSVs, and regenerated technical data products. Node statuses retain 162 successes, ten node-limit skips and one timeout. Mobile QA covers real 390x844/360x800 emulation, DOM/geometry interactions, actual HTTP/AI,44px targets and board-local scrolling; physical input remains unverified.

A final integrated run found an intermittent Win10053 during POST to an unknown path (317 passed,1failed); its full log is retained as docs/verification-technical-failed-http.log. The HTTP close/body handling is under investigation; release is not marked verified until that gate is resolved.

### Technical verification resolved

A real fragmented POST confirmed the unread-body condition. Bounded draining and six regression cases were added; implementerHTTP155 passed and scoped reviewerAPPROVE. Exact originalWin10053cause remains unproven and its log retained. Final full command after the fix:324 passed in93.25s,exit0. Wheel1.1.0 rebuilt; allPython/HTML bytes match finalsource; isolatedHTTP config/MCTS/404smoke passed. Technicalstatus is recorded in docs/TECHNICAL_STATUS.md; report/authors/GitHub remain deferred per owner.

Finalsourcebundle PASS:152filehashes,isolatedimports,allthreesuitesresumezero,exactUTF8HTMLasset andactualXiangqiHTTP. Initialpackagingcheck had a shell-encoding assertion issue; byte-equality/UTF8check replaced that fragile shellliteral. No productsource changed. FinalZIPreceipt and SHA256SUMS bind the delivered artifacts.
