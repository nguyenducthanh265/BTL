# Mobile browser evidence — 2026-11-06

Chrome device emulation, not a physical phone. The measured CSS viewports were
390×844 and 360×800, device scale factor 1, mobile enabled, touch enabled.
Both runs reported `navigator.maxTouchPoints === 1` and a coarse pointer.

- [390×844 measurements](390x844.json): PASS.
- [360×800 measurements](360x800.json): PASS.
- [390px Xiangqi screenshot](390-xiangqi.png): full page after a human cannon move
  and a real AI reply, board scrolled horizontally by 40 CSS pixels.
- [360px 15×15 screenshot](360-five15.png): full page after center placement and
  a real AI reply, board scrolled horizontally by 170 CSS pixels.
- [Repeatable browser checks](check.js).

To repeat, start `python -m gameai.demo --port 8765` from the project root, open
the printed local URL in Chrome, and enable the DevTools device toolbar. Set
390×844 with a mobile/touch device type, reload, paste `check.js` into the console,
then run `await runMobileQA()`. Repeat at 360×800. The function returns the data
saved in the measurement files. It resets the demo and intentionally produces one
HTTP 400 by sending an invalid formula; it restores `fetch` and recovers by undo.
Random AI moves and timing may differ across runs.

The script dispatches DOM click events and changes `scrollLeft`; this verifies
event handlers, real HTTP/AI, board geometry and reachable edges. It does not
verify trusted pointer gestures, finger accuracy, native swipe inertia, hardware
input, Safari, or screen readers. Separately, Chrome's native browser-click tool
activated the 3×3 center cell and Undo at 390×844 successfully. This is still
browser automation under emulation, not a physical touch test.

Race tests delay delivery of real AI HTTP responses by 600ms, then reset or undo
before delivery. They do not replace the AI response with a mock. The JSON files
record the actual error HTTP status, recovery state, formulas/rollouts passed
through to analysis, control heights, board targets and horizontal scroll range.

Screenshots were inspected for readable pieces, controls, coordinate headings,
analysis and the horizontal-scroll instruction. Dense boards intentionally extend
beyond the visible board area; the entire page stays within the viewport width.

## HTTP rejection diagnostic

`diagnose_unknown_path.py` instruments a real fragmented two-byte POST. Run from the project root with `python -c "import runpy; runpy.run_path('docs/mobile-qa/diagnose_unknown_path.py')"` so the project package is on the import path. `unknown-path-before.json` records the original early404 with unread body; `unknown-path-after.json` records complete body consumption before404. `integrated-failure-before-body-fix.log` preserves the original Win10053, whose exact cause was not independently reproduced.
