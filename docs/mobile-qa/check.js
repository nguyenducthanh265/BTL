// Paste into the demo tab's DevTools console, then run: await runMobileQA()
// Use device emulation with a coarse pointer at 390x844 or 360x800 first.
async function runMobileQA() {
  const until = async predicate => {
    for (let i = 0; i < 1000 && !predicate(); i++) {
      await new Promise(resolve => setTimeout(resolve, 20));
    }
    if (!predicate()) throw new Error('Timed out waiting for the demo');
  };
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  const idle = () => until(() => !S.busy);
  const click = index => $('board').querySelector(`[data-i="${index}"]`)
    .dispatchEvent(new MouseEvent('click', { bubbles: true }));
  const results = {
    viewport: { width: innerWidth, height: innerHeight, maxTouchPoints: navigator.maxTouchPoints,
      coarsePointer: matchMedia('(pointer: coarse)').matches },
    interaction: 'DOM click events in a real browser; real local HTTP/AI; not physical touch',
    boards: [], controls: [], races: [], errors: [],
  };
  check(results.viewport.coarsePointer, 'Enable mobile/touch device emulation first');
  $('side').value = '1';
  $('kind').value = 'mcts';
  for (const [game, center, last] of [
    ['ttt3', 4, 8], ['five9', 40, 80], ['five15', 112, 224], ['xiangqi', null, 89],
  ]) {
    $('game').value = game;
    $('game').dispatchEvent(new Event('change'));
    await idle();
    $('iterations').value = 100;
    const board = $('board');
    const target = board.querySelector('button,.hit').getBoundingClientRect();
    const range = board.scrollWidth - board.clientWidth;
    board.scrollLeft = range;
    const right = board.querySelector(`[data-i="${last}"]`).getBoundingClientRect();
    const bounds = board.getBoundingClientRect();
    const edgeReachable = right.left >= bounds.left && right.right <= bounds.right + 1;
    board.scrollLeft = 0;
    check(target.width >= 44 && target.height >= 44, game + ': small target');
    check(document.documentElement.scrollWidth === innerWidth, game + ': page overflow');
    check(edgeReachable, game + ': unreachable right edge');
    if (game === 'xiangqi') { click(70); click(67); }
    else click(center);
    await idle();
    check(S.pos.moves.length === 2 && S.analysis?.type === 'mcts', game + ': AI reply missing');
    const played = S.pos.moves.slice();
    check($('analysis').scrollWidth === $('analysis').clientWidth, game + ': analysis overflow');
    const controls = [...document.querySelectorAll('select,input,button.action')]
      .filter(e => e.getBoundingClientRect().height)
      .map(e => ({ id: e.id, height: e.getBoundingClientRect().height }));
    check(controls.every(e => e.height >= 44), game + ': small control');
    $('undo').click();
    await idle();
    check(S.pos.moves.length === 0, game + ': undo failed');
    $('new').click();
    await idle();
    check(S.pos.moves.length === 0, game + ': reset failed');
    results.boards.push({ game, targetWidth: target.width, targetHeight: target.height,
      pageWidth: document.documentElement.scrollWidth, boardScrollRange: range,
      rightEdgeReachable: edgeReachable, scrollHint: !$('board-help').hidden,
      played, undoEmpty: true, resetEmpty: true, analysisOverflow: 0, controls });
  }
  $('game').value = 'ttt3';
  $('game').dispatchEvent(new Event('change'));
  await idle();
  $('iterations').value = 100;
  $('c').value = 1.8;
  for (const formula of S.config.formulas) {
    $('formula').value = formula;
    $('formula').dispatchEvent(new Event('input'));
    click(4); await idle();
    check(S.analysis.options.formula === formula && S.analysis.options.c === 1.8, 'Formula mismatch');
    results.controls.push({ formula, used: S.analysis.options.formula, c: S.analysis.options.c });
    $('new').click(); await idle();
  }
  for (const rollout of S.config.rollouts) {
    $('rollout').value = rollout;
    click(4); await idle();
    check(S.analysis.options.rollout === rollout, 'Rollout mismatch');
    results.controls.push({ rollout, used: S.analysis.options.rollout });
    $('new').click(); await idle();
  }
  $('kind').value = 'alphabeta';
  $('kind').dispatchEvent(new Event('input'));
  $('depth').value = 9;
  click(4); await idle();
  check(S.analysis.type === 'alphabeta' && S.analysis.options.depth === 9, 'Alpha-Beta mismatch');
  results.controls.push({ type: S.analysis.type, depth: S.analysis.options.depth,
    value: S.analysis.value, hiddenMctsOptions: $('mcts-options').hidden });
  $('side').value = '-1';
  $('side').dispatchEvent(new Event('change'));
  await idle();
  check(S.pos.moves.length === 1 && S.pos.to_play === -1 && $('undo').disabled, 'AI opening failed');
  results.controls.push({ humanSide: S.side, aiOpening: S.pos.moves.slice(), undoDisabled: true });
  $('side').value = '1';
  $('kind').value = 'mcts';
  $('kind').dispatchEvent(new Event('input'));
  $('new').click(); await idle();
  const originalFetch = window.fetch;
  let held = 0;
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    if (args[1] && JSON.parse(args[1].body).agent) {
      held++;
      await new Promise(resolve => setTimeout(resolve, 600));
      held--;
    }
    return response;
  };
  try {
    for (const action of ['undo', 'new']) {
      click(4);
      await until(() => S.thinking && held > 0);
      check(!$('undo').disabled, 'Undo unavailable during AI search');
      const pendingMoves = S.pos.moves.slice();
      $(action).click();
      await idle();
      const token = S.token;
      await until(() => held === 0);
      await new Promise(resolve => setTimeout(resolve, 30));
      check(S.pos.moves.length === 0 && S.token === token, 'Late response replaced ' + action);
      results.races.push({ action, pendingMoves, after: S.pos.moves.slice(), staleResponseIgnored: true });
    }
  } finally { window.fetch = originalFetch; }
  const invalid = document.createElement('option');
  invalid.value = 'invalid-qa-formula';
  $('formula').append(invalid);
  $('formula').value = invalid.value;
  let errorStatus;
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    if (!response.ok) errorStatus = response.status;
    return response;
  };
  try { click(4); await idle(); } finally { window.fetch = originalFetch; }
  results.errors.push({ httpStatus: errorStatus, message: S.error, moves: S.pos.moves.slice(),
    undoEnabled: !$('undo').disabled });
  check(errorStatus === 400 && S.error === 'Công thức không hợp lệ'
    && S.pos.moves.length === 1, 'Error not recoverable');
  $('formula').value = 'ucb1';
  invalid.remove();
  $('undo').click(); await idle();
  check(!S.error && S.pos.moves.length === 0, 'Error recovery failed');
  results.errors.push({ recovery: 'undo', message: S.error, moves: S.pos.moves.slice() });
  results.result = 'PASS';
  return results;
}
