# Technical release1.1.0 - 6 November2026

Technical implementation and verification completed within the coursework model. Report writing, authorship and GitHub publication are explicitly deferred by the owner.

- Final integrated tests: **324 passed in93.25s**, exit0. Exact log: verification-technical.log. This is the post-fix run, not a retry of unchanged failing code.
- Independent technical review and scoped HTTP/release-gate recheck: APPROVE, zero open findings.
- Match snapshot: **53,000** valid unique games; all43,000 3x3,6,700 Gomoku and3,200 planned Xiangqi identities plus100 supplementary Xiangqi games. Full legality/outcome/seed replay has zero errors.
- Auxiliary coverage is complete by planned identity. Nodes retain162 successful measurements,ten explicit node-limit skips and one timeout; no skipped measurement is described as successful. Bandit18runs/root60groups/quality27runs/exhaustive280runs have complete identities and no stored-invariant errors.
- Demo verified through real localHTTP and browser emulation at390x844 and360x800. Touch/coarse-pointer targets are44px minimum; dense boards scroll locally. JSON/screenshots and repeatable checks are under mobile-qa/.
- A deterministic fragmentedPOST regression established that the original unknown-route handler could close with an unread body. The handler now drains bounded bodies with a one-second absolute deadline. Six new HTTPcases pass. Original Win10053 log and before/after instrumentation remain preserved; its exact historical cause was not established.
- Runtime wheel1.1.0 built and every Python/HTML payload matched current source. Isolated subprocess imported the extracted wheel, served config, calculated an actual MCTS reply and returned JSON404 for an unknownPOST.
- Packaging refuses a failed integrated test log, audit errors, incomplete planned match coverage or raw/snapshot hash drift. The source bundle embeds a SHA256 manifest and fixed input data; external receipts identify the delivered archive and wheel.

## Boundaries

This is a local demo using simplified Xiangqi draw rules and pseudo-legal rollout approximation. Finite-budget MCTS has no universal non-loss guarantee. Physical touch/swipe hardware, Safari, screen readers and public deployment are not certified by browser emulation. Root-level reports/PDFs have not been revised for this technical release and must not be presented as updated conclusions.

Final evidence: final_experiments.md,final_demo.md,final_findings.md; results/integrity.json,results/auxiliary_integrity.json,results/snapshot_integrity.json and results/source_data/manifest.json. Prior failures/data artifacts are preserved in the workspace archive. No paid API or remote publication was used.
