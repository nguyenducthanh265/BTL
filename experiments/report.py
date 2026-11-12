"""Turn results/raw/*.csv into tables, figures and results/SUMMARY.md.

Every number is read or computed from a CSV. A planned match without games is shown as
"no data", never filled in. An experiment with no data gets no file, only a MISSING line
in the summary. Each run first deletes the old tables and figures, so nothing stale stays.

    python -m experiments.report [--raw results/raw] [--out results]
"""
import argparse
import csv
import json
import math
import hashlib
from datetime import datetime, timezone
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (the backend must be chosen first)
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from experiments.data import game_key, valid_game  # noqa: E402
from experiments.nodes import entries as node_entries  # noqa: E402
from experiments.bandit import SETTINGS, RUNS, HORIZON, SEEDS as BANDIT_SEEDS  # noqa: E402
from experiments.plan import C_VALUES, SUITES, VARIANTS  # noqa: E402
from experiments.root_stats import GOMOKU_POSITION, ITERATIONS as ROOT_ITERATIONS, SEEDS as ROOT_SEEDS  # noqa: E402
from experiments.runner import FIELDS, RAW_DIR  # noqa: E402
from experiments.stats import wilson_interval  # noqa: E402
from experiments.verify_3x3 import (  # noqa: E402
    EXHAUSTIVE_ITERATIONS, EXHAUSTIVE_SEEDS, QUALITY_SEEDS, TTT_ITERATIONS, _replay, reachable_positions,
)
from gameai.search.minimax import optimal_moves  # noqa: E402

NS = "interval includes 0.5 (descriptive)"
BETTER = "interval above 0.5 (descriptive)"
WORSE = "interval below 0.5 (descriptive)"
GAME_NAMES = {"ttt3": "Tic-Tac-Toe 3x3", "gomoku9": "five-in-a-row 9x9", "xiangqi": "Xiangqi"}
XIANGQI_PLY_CAP = 200
ROOT_TOP_MOVES = 3
FIGURE_C = "1.4"
EXPERIMENTS = {
    "wdl": "Win/draw/loss",
    "ab_self": "Alpha-Beta against weaker opponents (sanity baseline)",
    "rollout": "Rollout policies",
    "rollout_vs_ab": "Rollout policies against Alpha-Beta",
    "final": "Final-move rule (W/N against most visited)",
    "formula": "UCT variants",
    "radius": "Restricting the tree to cells near stones",
    "ab_ladder": "MCTS iterations against Alpha-Beta",
}

# Palette from the dataviz skill, checked with its validator. Yellow and aqua are below
# 3:1 contrast, which the skill allows only with a table view: every figure has one here.
INK, SECONDARY, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
MARKERS = "osD^"
LINE_STYLES = ("-", (0, (4, 1.5)), (0, (1, 1)), (0, (4, 1, 1, 1)))  # still readable in print
DIVERGING = LinearSegmentedColormap.from_list("score", ["#e34948", "#f0efec", "#2a78d6"])
COLUMN, DOUBLE = (3.5, 2.5), (7.16, 2.7)  # IEEE column and page widths, in inches
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 8, "axes.edgecolor": AXIS, "axes.linewidth": 0.6,
    "axes.labelcolor": SECONDARY, "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": SECONDARY, "ytick.labelcolor": SECONDARY, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.5, "axes.spines.top": False,
    "axes.spines.right": False, "axes.axisbelow": True, "legend.frameon": False,
    "savefig.dpi": 300, "savefig.bbox": "tight",
    "pdf.fonttype": 42, "ps.fonttype": 42,  # IEEE PDF checks reject Type 3 fonts
})


# ---------------------------------------------------------------------------- reading
def read_csv(path):
    """All rows of a CSV, or [] when the file does not exist or is empty."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_games(raw):
    """One row per game from every match file, and how many rows were unusable."""
    games, dropped = {}, 0
    for path in sorted(raw.glob("*.csv")):
        rows = read_csv(path)
        if not rows or not set(FIELDS) <= set(rows[0]):
            continue
        for row in rows:
            if not valid_game(row):
                dropped += 1
                continue
            key = game_key(row)
            row = {**row, "a": key[2], "b": key[3], "index": str(key[4])}
            games.setdefault(key, row)
    return list(games.values()), dropped


def planned_games():
    """{(exp, game, a, b): number of games}, in the order of experiments/plan.py."""
    plan = Counter()
    for suite, build in SUITES.items():
        for task in build():
            plan[(task["exp"], task["game"], json.dumps(task["a"], sort_keys=True),
                  json.dumps(task["b"], sort_keys=True))] += 1
    return plan


def label(spec):
    """Short readable name of an agent."""
    kind = spec["type"]
    if kind != "mcts" and kind != "alphabeta":
        return kind.capitalize()
    if kind == "alphabeta":
        depth = "full" if spec.get("depth") is None else spec["depth"]
        radius = spec.get("radius")
        return f"AB(d={depth}" + (f", r={radius})" if radius else ")")
    parts = [str(spec["iterations"]), f"c={spec.get('c', 1.4)}"]
    defaults = {"formula": "ucb1", "rollout": "random", "final_rule": "robust", "radius": None}
    parts += [str(spec[k]) if k != "radius" else f"r={spec[k]}" for k, default in defaults.items()
              if spec.get(k, default) != default]
    return f"MCTS({', '.join(parts)})"


@dataclass
class Cell:
    """All games of one pairing of agents in one experiment."""
    exp: str
    game: str
    a: dict
    b: dict
    planned: int  # 0 when the plan does not contain this pairing
    rows: list = field(default_factory=list)

    @property
    def n(self):
        return len(self.rows)

    def count(self, score):
        return sum(float(row["a_score"]) == score for row in self.rows)

    @property
    def score(self):
        return (self.count(1.0) + 0.5 * self.count(0.5)) / self.n

    @property
    def interval(self):
        return wilson_interval(self.count(1.0) + 0.5 * self.count(0.5), self.n)

    @property
    def partial(self):
        return bool(self.planned) and {int(row["index"]) for row in self.rows} != set(range(self.planned))

    def games_text(self):
        return f"{self.n}/{self.planned} (partial)" if self.partial else str(self.n)

    def flag(self):
        low, high = self.interval
        if low <= 0.5 <= high:
            return NS
        return BETTER if low > 0.5 else WORSE


def interval_text(low, high):
    return f"[{low:.3f}, {high:.3f}]"


def tex_escape(text):
    text = str(text)
    for char in "&%$#_{}":
        text = text.replace(char, "\\" + char)
    return text.replace("±", r"$\pm$")


def is_number(text):
    return str(text).replace(",", "").replace(".", "", 1).isdigit()


# ---------------------------------------------------------------------------- figures
def end_labels(ax, ends):
    """Name each series beside its last point, only if the ends are far enough apart.

    A label pushed away from its line would point at the wrong one, so when the lines end
    close together the legend and the different markers carry the identity alone.
    """
    to_axes = ax.transData + ax.transAxes.inverted()
    placed = sorted((to_axes.transform((x, y))[1], text) for x, y, text in ends)
    heights = [height for height, _ in placed]
    if any(upper - lower < 0.07 for lower, upper in zip(heights, heights[1:])):
        return
    for height, text in placed:
        ax.annotate(text, (1.02, height), xycoords="axes fraction", va="center",
                    color=SECONDARY, annotation_clip=False)


def iterations_axis(ax, ticks):
    ax.set_xscale("log")
    ax.set_xticks(ticks, [str(tick) for tick in ticks])
    ax.minorticks_off()
    ax.set_xlabel("MCTS iterations per move (log scale)")


def legend_above(ax, columns=4):
    if ax.get_legend_handles_labels()[0]:
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=columns, handlelength=2.2,
                  columnspacing=1.0, borderaxespad=0.2, fontsize=7.5)


# ----------------------------------------------------------------------------- report
class Report:
    def __init__(self, raw, out):
        self.raw, self.out = Path(raw), Path(out)
        self.tables, self.figures = self.out / "tables", self.out / "figures"
        for folder, kinds in ((self.tables, ("*.md", "*.tex")), (self.figures, ("*.png", "*.pdf"))):
            folder.mkdir(parents=True, exist_ok=True)
            for kind in kinds:
                for old in folder.glob(kind):
                    old.unlink()
        self.entries = []  # (status, kind, name, reading)
        self.games, self.dropped = load_games(self.raw)
        self.plan = planned_games()
        self.by_cell = defaultdict(list)
        for row in self.games:
            self.by_cell[(row["exp"], row["game"], row["a"], row["b"])].append(row)

    def cells(self, exp, game):
        """Planned pairings in plan order, then any pairing that only the data contains."""
        keys = [key for key in self.plan if key[:2] == (exp, game)]
        keys += [key for key in self.by_cell if key[:2] == (exp, game) and key not in self.plan]
        return [Cell(exp, game, json.loads(key[2]), json.loads(key[3]), self.plan.get(key, 0),
                     self.by_cell.get(key, [])) for key in keys]

    def missing(self, kind, name, why):
        self.entries.append(("MISSING", kind, name, why))

    def write_table(self, name, caption, headers, rows, reading, partial=False):
        lines = [f"**{caption}**", "", "| " + " | ".join(headers) + " |",
                 "|" + "---|" * len(headers)]
        lines += ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
        (self.tables / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        columns = "".join("r" if all(is_number(row[i]) for row in rows) else "l"
                          for i in range(len(headers)))
        tex = [r"\begin{table*}[!t]", r"\centering", rf"\caption{{{tex_escape(caption)}}}",
               rf"\label{{tab:{name}}}", r"\small", rf"\begin{{tabular}}{{{columns}}}", r"\toprule",
               " & ".join(tex_escape(h) for h in headers) + r" \\", r"\midrule"]
        tex += [" & ".join(tex_escape(value) for value in row) + r" \\" for row in rows]
        tex += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
        (self.tables / f"{name}.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")
        self.entries.append(("PARTIAL" if partial else "OK", "table", name, reading))

    def save_figure(self, fig, name, reading, partial=False):
        for extension in ("png", "pdf"):
            fig.savefig(self.figures / f"{name}.{extension}")
        plt.close(fig)
        self.entries.append(("PARTIAL" if partial else "OK", "figure", name, reading))

    # ------------------------------------------------------------------ match tables
    def match_table(self, exp, game):
        name, cells = f"{exp}_{game}", self.cells(exp, game)
        played = [cell for cell in cells if cell.n]
        if not played:
            self.missing("table", name, f'no games for exp "{exp}", game {game}')
            return
        wdl = exp == "wdl"
        headers = ["Agent a", "Opponent b", "Games", "W", "D", "L", "Score", "Approx. 95% score interval", "Flag"]
        if wdl:
            headers.insert(7, "As 1st / 2nd")
        rows = []
        for cell in cells:
            if not cell.n:
                row = [label(cell.a), label(cell.b), f"0/{cell.planned}", "-", "-", "-", "-", "-",
                       "no data"]
                rows.append(row[:7] + ["-"] + row[7:] if wdl else row)
                continue
            row = [label(cell.a), label(cell.b), cell.games_text(), cell.count(1.0),
                   cell.count(0.5), cell.count(0.0), f"{cell.score:.3f}",
                   interval_text(*cell.interval), cell.flag()]
            if wdl:
                row.insert(7, _sides_text(cell))
            rows.append(row)
        flags = Counter(cell.flag() for cell in played)
        best = max(played, key=lambda cell: cell.score)
        reading = (f"{len(played)} of {len(cells)} pairings have games; {flags[BETTER]} intervals above 0.5, "
                   f"{flags[WORSE]} below 0.5, {flags[NS]} include 0.5 (descriptive). Highest score: {label(best.a)} "
                   f"vs {label(best.b)}, {best.score:.3f} {interval_text(*best.interval)}.")
        if any(cell.b["type"] == "perfect" for cell in played):
            reading += " Against a perfect player 0.5 is the best possible score."
        if exp == "ab_ladder":
            reading += " " + _ladder_note(played)
        partial = any(cell.partial or not cell.n for cell in cells)
        self.write_table(name, f"{EXPERIMENTS.get(exp, exp)}: {GAME_NAMES.get(game, game)}", headers,
                         rows, reading, partial)

    # ------------------------------------------------------------------------ curves
    def curve(self, exp, game, point, y_label, flag_half, name=None):
        """Figure and wide table of ``point(cell)`` against iterations, one line per c."""
        name = name or f"{exp}_{game}"
        cells = [cell for cell in self.cells(exp, game) if cell.a.get("c") in C_VALUES]
        if not any(cell.n for cell in cells):
            self.missing("figure", name, f'no games for exp "{exp}", game {game}')
            self.missing("table", name, f'no games for exp "{exp}", game {game}')
            return
        ticks = sorted({cell.a["iterations"] for cell in cells})
        table = {(cell.a["c"], cell.a["iterations"]): cell for cell in cells}
        fig, ax = plt.subplots(figsize=COLUMN)
        ends = []
        for slot, c in enumerate(C_VALUES):
            # A planned point without games is NaN: the line breaks there, nothing is interpolated.
            lines = [point(table[(c, it)]) if (c, it) in table and table[(c, it)].n else (math.nan,) * 3
                     for it in ticks]
            values, lows, highs = zip(*lines)
            ax.fill_between(ticks, lows, highs, color=SERIES[slot], alpha=0.14, linewidth=0)
            ax.plot(ticks, values, color=SERIES[slot], linestyle=LINE_STYLES[slot], linewidth=1.5,
                    marker=MARKERS[slot], markersize=4, label=f"c = {c}")
            hollow = [(it, point(table[(c, it)])[0]) for it in ticks
                      if (c, it) in table and table[(c, it)].n and table[(c, it)].partial]
            if hollow:  # partial cells are drawn hollow
                ax.plot(*zip(*hollow), linestyle="none", marker=MARKERS[slot], markersize=4,
                        markerfacecolor="white", markeredgecolor=SERIES[slot])
            known = [(it, value) for it, value in zip(ticks, values) if not math.isnan(value)]
            if known:
                ends.append((*known[-1], f"c={c}"))
        ax.axhline(0.5, color=MUTED, linewidth=0.8, zorder=1)
        ax.set_ylim(0, 1)
        ax.set_ylabel(y_label)
        iterations_axis(ax, ticks)
        legend_above(ax)
        end_labels(ax, ends)

        rows = []
        for it in ticks:
            present = [table[(c, it)] for c in C_VALUES if (c, it) in table and table[(c, it)].n]
            row = [it, max((cell.n for cell in present), default=0)]
            for c in C_VALUES:
                cell = table.get((c, it))
                if cell is None or not cell.n:
                    row.append("no data")
                    continue
                value, low, high = point(cell)
                text = f"{value:.3f} {interval_text(low, high)}"
                if flag_half and low <= 0.5 <= high:
                    text += " incl.0.5"
                if cell.partial:
                    text += f" (partial, {cell.n}/{cell.planned})"
                row.append(text)
            rows.append(row)
        partial = any(cell.partial or not cell.n for cell in cells)
        reading = _curve_reading(table, ticks, point)
        self_play = [cell for cell in cells if cell.a == cell.b and cell.n]
        if self_play:
            cell = self_play[0]
            reading += (f" Self-play check ({label(cell.a)} against itself): {cell.score:.3f} "
                        f"{interval_text(*cell.interval)}, which should contain 0.5.")
        self.save_figure(fig, name, reading, partial)
        caption = f"{y_label} against iterations and c: {GAME_NAMES.get(game, game)}"
        if flag_half:
            caption += " (incl.0.5 = interval contains 0.5; descriptive only)"
        headers = ["Iterations", "Games"] + [f"c = {c}" for c in C_VALUES]
        self.write_table(name, caption, headers, rows, reading, partial)

    def heatmap(self, game):
        name = f"formula_heatmap_{game}"
        cells = {(cell.a["formula"], cell.a["c"]): cell for cell in self.cells("formula", game)
                 if cell.a.get("formula") in VARIANTS}
        if not any(cell.n for cell in cells.values()):
            self.missing("figure", name, f'no games for exp "formula", game {game}')
            return
        grid = [[cells[(f, c)].score if (f, c) in cells and cells[(f, c)].n else math.nan
                 for c in C_VALUES] for f in VARIANTS]
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        image = ax.imshow(grid, cmap=DIVERGING, vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(C_VALUES)), [str(c) for c in C_VALUES])
        ax.set_yticks(range(len(VARIANTS)), VARIANTS)
        ax.set_xlabel("c")
        ax.grid(False)
        for row, formula in enumerate(VARIANTS):
            for col, c in enumerate(C_VALUES):
                cell = cells.get((formula, c))
                if cell is None or not cell.n:
                    ax.text(col, row, "no data", ha="center", va="center", color=MUTED, fontsize=6)
                    continue
                strong = abs(cell.score - 0.5) > 0.33
                note = " incl.0.5" if cell.flag() == NS else ""
                ax.text(col, row, f"{cell.score:.2f}{note}", ha="center", va="center",
                        color="white" if strong else INK, fontsize=6.5)
        fig.colorbar(image, ax=ax, label="Score against standard UCT", fraction=0.05, pad=0.03)
        played = [cell for cell in cells.values() if cell.n]
        flagged = sum(cell.flag() == NS for cell in played)
        best = max(played, key=lambda cell: cell.score)
        reading = (f"{len(played)} of {len(VARIANTS) * len(C_VALUES)} formula x c cells have games "
                   f"({min(c.n for c in played)} to {max(c.n for c in played)} games each); "
                   f"{flagged} intervals include 0.5 (descriptive). Highest: "
                   f"{best.a['formula']} at c={best.a['c']}, {best.score:.3f}. With this many cells "
                   "the largest observed score can reflect selection noise; no pairwise significance test is made.")
        self.save_figure(fig, name, reading, any(cell.partial for cell in cells.values())
                         or len(played) < len(VARIANTS) * len(C_VALUES))

    # ------------------------------------------------------------------- other tables
    def nodes(self):
        rows = read_csv(self.raw / "nodes.csv")
        if not rows:
            for game in GAME_NAMES:
                self.missing("table", f"nodes_{game}", "nodes.csv is absent or empty")
            self.missing("figure", "nodes_depth", "nodes.csv is absent or empty")
            return
        for game in GAME_NAMES:
            self._nodes_table(game, [row for row in rows if row["game"] == game])
        self._nodes_figure(rows)

    def _nodes_table(self, game, rows):
        name = f"nodes_{game}"
        if not rows:
            self.missing("table", name, f"nodes.csv has no rows for {game}")
            return
        by_position = game == "ttt3"
        grouped = defaultdict(list)
        for row in rows:
            first = row["position"] if by_position else row["radius"]
            grouped[(first, row["depth"])].append(row)
        table, worse_with_order = [], []
        for (first, depth), group in grouped.items():
            mm, ab, ordered = (_algorithm_rows(group, key) for key in
                               ("minimax", "alphabeta", "alphabeta_ordered"))
            table.append([first or "-", depth, len(ab), _nodes_text(mm), _nodes_text(ab),
                          _nodes_text(ordered), _ratio_text(mm, ab), _ratio_text(mm, ordered),
                          _ratio_text(ab, ordered), _seconds_text(mm), _seconds_text(ab),
                          _seconds_text(ordered)])
            for position, row in ordered.items():
                if row["status"] == "ok" and ab.get(position, {}).get("status") == "ok" \
                        and int(row["nodes"]) > int(ab[position]["nodes"]):
                    worse_with_order.append(f"{position} (d={depth})")
        headers = ["Position" if by_position else "Radius", "Depth", "Positions", "Minimax nodes",
                   "AB nodes", "AB+ord nodes", "MM/AB", "MM/AB+ord", "AB/AB+ord", "MM s", "AB s",
                   "AB+ord s"]
        skipped = sum(not row["status"] == "ok" for row in rows)
        expected = {(name, str(radius or ""), str(depth or "full"), algorithm)
                    for g, _, name, _, radius, depth, algorithm in node_entries() if g == game}
        present = {(r["position"], r["radius"], r["depth"], r["algorithm"]) for r in rows}
        missing = len(expected - present)
        reading = (f"{len(rows)} searches, {skipped} not run or stopped (marked as skipped k/n). "
                   f"{missing} planned searches have no CSV row. "
                   f"{_agreement_text(rows)} Nodes are means over positions, which vary a lot: "
                   "see nodes.csv. Ratios use only positions where both searches finished.")
        if worse_with_order:
            reading += f" Ordering increased nodes at: {', '.join(worse_with_order[:6])}."
        self.write_table(name, f"Nodes and mean one-core time: {GAME_NAMES[game]}", headers, table,
                         reading, skipped > 0 or missing > 0)

    def _nodes_figure(self, rows):
        panels = [("gomoku9", "2", "Five-in-a-row, radius 2"), ("xiangqi", "", "Xiangqi")]
        panels = [panel for panel in panels if any(r["game"] == panel[0] for r in rows)]
        if not panels:
            self.missing("figure", "nodes_depth", "nodes.csv has no depth-limited rows")
            return
        fig, axes = plt.subplots(1, len(panels), figsize=DOUBLE, sharey=True, squeeze=False)
        for ax, (game, radius, title) in zip(axes[0], panels):
            chosen = [r for r in rows if r["game"] == game and r["radius"] == radius]
            ends = []
            for slot, (key, text) in enumerate((("minimax", "Minimax"), ("alphabeta", "Alpha-Beta"),
                                                ("alphabeta_ordered", "AB + ordering"))):
                # A depth counts only if all positions finished: a mean over the easy ones misleads.
                depths = sorted({int(r["depth"]) for r in chosen if r["algorithm"] == key})
                points = []
                for depth in depths:
                    group = [r for r in chosen if r["algorithm"] == key and int(r["depth"]) == depth]
                    expected_positions = {name for g, _, name, _, rad, d, algorithm in node_entries()
                                          if g == game and str(rad or "") == radius
                                          and d == depth and algorithm == key}
                    if {r["position"] for r in group} == expected_positions \
                            and all(r["status"] == "ok" for r in group):
                        points.append((depth, sum(int(r["nodes"]) for r in group) / len(group)))
                if points:
                    ax.plot(*zip(*points), color=SERIES[slot], linestyle=LINE_STYLES[slot],
                            marker=MARKERS[slot], markersize=4, linewidth=1.5, label=text)
                    ends.append((*points[-1], text))
            ax.set_yscale("log")
            ax.set_xticks([1, 2, 3, 4])
            ax.set_xlabel(f"{title}: search depth")
            ax.relim()
            ax.autoscale_view()
            ax.set_xlim(0.8, 4.2)
            legend_above(ax, 3)
            fig.canvas.draw()
            end_labels(ax, ends)
        axes[0][0].set_ylabel("Mean nodes per search (log scale)")
        fig.subplots_adjust(wspace=0.35)
        self.save_figure(fig, "nodes_depth", "Mean nodes against depth. A depth is drawn only "
                         "when every position finished, so partly skipped depths are absent. "
                         "Numbers are in the nodes tables.",
                         len(rows) < sum(1 for _ in node_entries())
                         or any(r["status"] != "ok" for r in rows))

    def root_stats(self):
        rows = read_csv(self.raw / "root_stats.csv")
        if not rows:
            self.missing("table", "root_stats", "root_stats.csv is absent or empty")
            return
        groups = defaultdict(list)
        for row in rows:
            groups[(row["position"], int(row["iterations"]), int(row["seed"]))].append(row)
        seeds = sorted({key[2] for key in groups})
        table, notes = [], []
        for (position, iterations, seed), group in groups.items():
            if seed != seeds[0]:
                continue
            all_seeds = [g for key, g in groups.items() if key[:2] == (position, iterations)]
            chosen = Counter(r["move"] for g in all_seeds for r in g if int(r["chosen"]))
            ranked = sorted(group, key=lambda r: -int(r["N"]))
            shown = ranked if position == "assignment" else ranked[:ROOT_TOP_MOVES]
            for r in shown:
                table.append([position, iterations, r["rollout"], r["move"], r["N"], r["W"],
                              r["W_over_N"], r["UCT"], f"{chosen[r['move']]}/{len(all_seeds)}"])
            if position == "assignment":
                notes.append(f"{iterations} it: {chosen['8']}/{len(all_seeds)} seeds")
        reading = f"Statistics shown for seed {seeds[0]}, c=1.4; 'Chosen' counts seeds over all " \
                  f"{len(seeds)} seeds. "
        reading += ("Assignment position, seeds choosing the only non-losing cell 8: "
                    + "; ".join(notes) + "." if notes else "Assignment position: no data.")
        expected = {"assignment", "empty_3x3", GOMOKU_POSITION, "xiangqi_start"}
        absent = expected - {key[0] for key in groups}
        expected_groups = {(position, it, seed) for position in expected
                           for it in ROOT_ITERATIONS for seed in ROOT_SEEDS}
        missing_groups = len(expected_groups - set(groups))
        reading += f" Missing planned position/iteration/seed searches: {missing_groups}."
        if absent:
            reading += f" Absent positions: {', '.join(sorted(absent))}."
        headers = ["Position", "Iterations", "Rollout", "Move", "N", "W", "W/N", "UCT", "Chosen"]
        self.write_table("root_stats", "Root statistics of MCTS (largest N first)", headers, table,
                         reading, bool(absent) or missing_groups > 0)

    def verify_quality(self):
        rows = read_csv(self.raw / "verify_quality.csv")
        if not rows:
            self.missing("table", "verify_quality", "verify_quality.csv is absent or empty")
            return
        positions = reachable_positions()
        decisive = _positions_allowing_a_blunder(positions)
        grouped = defaultdict(list)
        for row in rows:
            grouped[int(row["iterations"])].append(row)
        table, partial = [], set(grouped) != set(TTT_ITERATIONS)
        for iterations, group in sorted(grouped.items()):
            partial = partial or len(group) < QUALITY_SEEDS
            decisions = sum(int(r["positions"]) for r in group)
            blunders = sum(int(r["blunders"]) for r in group)
            low, high = wilson_interval(blunders, decisions)
            full = all(int(r["positions"]) == len(positions) for r in group)
            partial = partial or not full or {int(r["seed"]) for r in group} != set(range(QUALITY_SEEDS))
            among = f"{blunders / (decisive * len(group)):.4f}" if full else "n/a"
            table.append([iterations, len(group), decisions, blunders, f"{blunders / decisions:.4f}",
                          interval_text(low, high), among])
        first_zero = next((r[0] for r in table if r[3] == 0), None)
        reading = (f"Blunder = a move that worsens the exact game value. Only {decisive} of "
                   f"{len(positions)} positions allow a blunder; the last column uses those as "
                   f"the denominator. Lowest iteration count with zero blunders: {first_zero}.")
        headers = ["Iterations", "Seeds", "Decisions", "Blunders", "Blunder rate", "95% CI",
                   "Rate where blunder possible"]
        self.write_table("verify_quality", "MCTS move quality on every reachable 3x3 position",
                         headers, table, reading, partial)

    def verify_exhaustive(self):
        rows = read_csv(self.raw / "verify_exhaustive.csv")
        if not rows:
            self.missing("table", "verify_exhaustive", "verify_exhaustive.csv is absent or empty")
            return
        grouped = defaultdict(list)
        for row in rows:
            grouped[int(row["iterations"])].append(row)
        table, partial = [], False
        for iterations, group in sorted(grouped.items()):
            partial = partial or {(int(r["role"]), int(r["seed"])) for r in group} != {
                (role, seed) for role in (1, -1) for seed in range(EXHAUSTIVE_SEEDS)}
            lines = sum(int(r["lines"]) for r in group)
            losses = sum(int(r["losses"]) for r in group)
            bad_runs = sum(int(r["losses"]) > 0 for r in group)
            table.append([iterations, len(group), lines, sum(int(r["wins"]) for r in group),
                          sum(int(r["draws"]) for r in group), losses, bad_runs,
                          f"{3 / lines:.5f}" if losses == 0 else "losses observed",
                          f"{3 / len(group):.4f}" if bad_runs == 0 else "losses observed"])
        clean = [row[0] for row in table if row[5] == 0]
        reading = (f"Iterations with zero losses against every opponent line: {clean or 'none'}. "
                   "Zero observed losses is evidence, not proof: see the notes above.")
        headers = ["Iterations", "Runs", "Lines", "Wins", "Draws", "Losses", "Runs with a loss",
                   "Heuristic 3/lines (dependent)", "95% bound per run (3/runs)"]
        self.write_table("verify_exhaustive", "MCTS against every opponent line on 3x3", headers,
                         table, reading, partial
                         or set(grouped) != set(EXHAUSTIVE_ITERATIONS))

    def bandit(self):
        rows = read_csv(self.raw / "bandit.csv")
        if not rows:
            self.missing("table", "bandit_regret", "bandit.csv is absent or empty")
            self.missing("figure", "bandit_regret", "bandit.csv is absent or empty")
            return
        runs = defaultdict(list)
        for row in rows:
            runs[(row["setting"], row["strategy"], row["c"])].append(row)
        for series in runs.values():
            series.sort(key=lambda r: int(r["step"]))
        settings = list(dict.fromkeys(key[0] for key in runs))
        # The figure keeps one c per formula; the other c values are in the table.
        shown = list(dict.fromkeys(key[1] for key in runs))
        fig, axes = plt.subplots(1, len(settings), figsize=DOUBLE, sharey=True, squeeze=False)
        for ax, setting in zip(axes[0], settings):
            for slot, strategy in enumerate(shown):
                series = runs.get((setting, strategy, FIGURE_C)) or runs.get((setting, strategy, ""))
                if not series:
                    continue
                steps = [int(r["step"]) for r in series]
                means = [float(r["mean_regret"]) for r in series]
                errors = [float(r["ci95"]) for r in series]
                ax.fill_between(steps, [m - e for m, e in zip(means, errors)],
                                [m + e for m, e in zip(means, errors)],
                                color=SERIES[slot], alpha=0.2, linewidth=0)
                ax.plot(steps, means, color=SERIES[slot], linestyle=LINE_STYLES[slot],
                        linewidth=1.5, label=strategy)
            ax.set_xscale("log")
            ax.set_yscale("log")
            arms = next(series[0]["arms"] for key, series in runs.items() if key[0] == setting)
            ax.set_xlabel(f"{setting}: pulls (log scale)\nArms: {arms}", fontsize=7)
            legend_above(ax, 2)
        axes[0][0].set_ylabel("Mean cumulative regret (log scale)")
        fig.subplots_adjust(wspace=0.38)
        reading = " ".join(_bandit_note(setting, runs) for setting in settings)
        expected = {(setting, strategy, "" if c is None else str(c))
                    for setting in SETTINGS for strategy, c in RUNS}
        partial = set(runs) != expected or any(int(series[-1]["step"]) != HORIZON
                    or int(series[-1]["seeds"]) != BANDIT_SEEDS for series in runs.values())
        reading += f" {len(expected - set(runs))} planned strategy/setting/c runs are missing."
        self.save_figure(fig, "bandit_regret", f"c={FIGURE_C}. {reading}", partial)
        headers = ["Setting", "Strategy", "c", "Seeds", "R(1,000)", "R(10,000)", "R(100,000)",
                   "R(1e5)/R(1e4)", "Median R(1e5)", "95th pct R(1e5)", "Max R(1e5)", "Wrong arm"]
        table = [_bandit_row(key, series) for key, series in runs.items()]
        self.write_table("bandit_regret", "Cumulative regret, mean ± 95% half-width", headers, table,
                         reading + " A ratio near 1.25 fits ln T; near 10 means linear. Wrong arm = "
                         "share of seeds whose most-pulled arm at the end is not the best arm.", partial)

    def timing(self):
        if not self.games:
            self.missing("table", "timing", "no match files with games")
            return
        totals = defaultdict(lambda: [0, 0, 0.0])
        for row in self.games:
            plies = int(row["plies"])
            a_moves = (plies + 1) // 2 if int(row["a_first"]) else plies // 2
            for side, moves in (("a", a_moves), ("b", plies - a_moves)):
                spec = json.loads(row[side])
                if _is_baseline(spec) and row.get(f"{side}_time"):
                    total = totals[(row["game"], label(spec), _sort_key(spec))]
                    total[0] += 1
                    total[1] += moves
                    total[2] += float(row[f"{side}_time"])
        if not totals:
            self.missing("table", "timing", "no games by baseline agents")
            return
        table = [[game, agent, games, moves, f"{1000 * seconds / moves:.2f}"]
                 for (game, agent, _), (games, moves, seconds)
                 in sorted(totals.items(), key=lambda item: (item[0][0], item[0][2])) if moves]
        self.write_table("timing", "Mean time per move, measured under parallel load",
                         ["Game", "Agent", "Agent-games", "Moves", "ms per move"], table,
                         "Per move of the agent itself (about half of the plies). Measured while many "
                         "games ran in parallel, so compare within this table only.")

    # ------------------------------------------------------------------------ summary
    def write_summary(self):
        status_counts = Counter(entry[0] for entry in self.entries)
        lines = ["# Results summary", "",
                 f"OK {status_counts['OK']}, PARTIAL {status_counts['PARTIAL']}, "
                 f"MISSING {status_counts['MISSING']}. PARTIAL means some planned games or searches "
                 "are absent; they are marked in the table, not filled in. MISSING means no file "
                 "was produced. Each table is a .md and a .tex file, each figure a .png and a .pdf.",
                 "", "## Data found", ""]
        lines += self._completeness() + ["", "## How to read the numbers", ""] + NOTES
        for kind, title in (("table", "Tables"), ("figure", "Figures")):
            lines += ["", f"## {title}", ""]
            for status, entry_kind, name, reading in self.entries:
                if entry_kind == kind:
                    where = f"`{kind}s/{name}`" if status != "MISSING" else f"`{name}`"
                    lines.append(f"- **{status}** {where}: {reading}")
        (self.out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _completeness(self):
        lines = []
        for suite in SUITES:
            planned = sum(count for key, count in self.plan.items() if key[1] == suite)
            done = sum(len({int(r["index"]) for r in rows} & set(range(self.plan.get(key, 0))))
                       for key, rows in self.by_cell.items()
                       if key[1] == suite)
            status = "MISSING" if not done else "complete" if done >= planned else "PARTIAL"
            lines.append(f"- {suite}: {done} of {planned} planned games ({status}).")
        off_plan = sum(len(rows) for key, rows in self.by_cell.items() if key not in self.plan)
        if off_plan:
            lines.append(f"- {off_plan} games belong to pairings that are not in experiments/plan.py.")
        if self.dropped:
            lines.append(f"- {self.dropped} unusable rows (for example cut short by a crash) were ignored.")
        capped = [row for row in self.games if row["game"] == "xiangqi"]
        if capped:
            hit = sum(int(row["plies"]) >= XIANGQI_PLY_CAP for row in capped)
            drawn_at_cap = sum(int(row["plies"]) >= XIANGQI_PLY_CAP and float(row["a_score"]) == 0.5
                               for row in capped)
            lines.append(f"- xiangqi: {hit} of {len(capped)} games reached {XIANGQI_PLY_CAP} plies; "
                         f"{drawn_at_cap} of those ended as draws. Draw reasons are not recorded in CSV.")
        for file in ("nodes", "root_stats", "bandit", "verify_quality", "verify_exhaustive"):
            found = bool(read_csv(self.raw / f"{file}.csv"))
            lines.append(f"- {file}.csv: {'found' if found else 'MISSING'}.")
        return lines


NOTES = [
    "- Score = (W + 0.5 D) / games, from agent a's side. a_score already is from a's side, so "
    "who moved first does not change W, D or L.",
    f'- The interval is a nominal 95% Wilson interval applied to fractional scores. "{NS}" '
    "is only a display flag meaning that interval contains 0.5; it is not a pairwise test "
    "between configurations, proof of equality, or an adjustment for multiple comparisons.",
    "- With draws, scores are not Bernoulli observations, so these Wilson intervals are an "
    "approximation without guaranteed 95% coverage. An all-draw cell still shows a wide interval "
    "around 0.5. Seeds alternate first/second roles; these are not identical game distributions.",
    "- Many configurations are summarized with no correction; rankings and interval flags are descriptive, "
    "and selecting the highest observed score can overstate performance.",
    "- Partial cells may lean towards short games, because the runner writes games as they "
    "finish. Treat them as provisional.",
    "- Node counts: `search()` widens the root window to find ALL equally best moves, so "
    "Alpha-Beta visits more nodes than the textbook version that keeps one best move. "
    "Midgame positions come from seeded random play, not from strong games, and Minimax entries "
    "above the node limit are marked skipped.",
    "- Zero observed losses is evidence, not proof. The rule of three says: with zero failures "
    "in N independent trials, the failure rate is below about 3/N with 95% confidence. The lines "
    "of one exhaustive run share the agent's decisions, so they are not independent and 3/lines "
    "is only a heuristic, not a valid 95% bound; 3/runs treats each whole run as one trial "
    "and is the safer approximate figure (under independent run seeds). Neither "
    "excludes a rarer failure, because MCTS is randomised and only a finite number of runs exists.",
    "- Timing was measured with other games running in parallel, so it is only a rough guide.",
]


def _positions_allowing_a_blunder(positions):
    """Positions where at least one legal move worsens the exact game value."""
    memo, count = {}, 0
    for moves in positions:
        game = _replay(moves)
        count += len(optimal_moves(game, memo)) < len(game.legal_moves())
    return count


def _sides_text(cell):
    def mean(first):
        scores = [float(r["a_score"]) for r in cell.rows if int(r["a_first"]) == first]
        return f"{sum(scores) / len(scores):.2f}" if scores else "-"
    return f"{mean(1)} / {mean(0)}"


def _ladder_note(cells):
    """Smallest iteration count at which MCTS is significantly better than the opponent."""
    winning = [cell.a["iterations"] for cell in cells
               if cell.a["type"] == "mcts" and cell.flag() == BETTER]
    return (f"Lowest measured iteration count with a score interval above 0.5: {min(winning)} "
            "(descriptive, not a pairwise significance test)."
            if winning else "No measured iteration count has a score interval wholly above 0.5.")


def _curve_reading(table, ticks, point):
    """Compare the c values at the highest iteration count that has games for at least two."""
    for iterations in reversed(ticks):
        cells = {c: table[(c, iterations)] for c in C_VALUES
                 if (c, iterations) in table and table[(c, iterations)].n}
        if len(cells) >= 2:
            points = {c: point(cell) for c, cell in cells.items()}
            top = max(points, key=lambda c: points[c][0])
            bottom = min(points, key=lambda c: points[c][0])
            overlap = points[top][1] <= points[bottom][2]
            verdict = "intervals overlap (descriptive)" if overlap else "intervals do not overlap (descriptive)"
            return (f"At {iterations} iterations ({cells[top].n} games): highest c={top} "
                    f"{points[top][0]:.3f}, lowest c={bottom} {points[bottom][0]:.3f}: {verdict}.")
    return "Too few cells with games to compare c values."


def _score_point(cell):
    return (cell.score, *cell.interval)


def _loss_point(cell):
    losses = cell.count(0.0)
    return (losses / cell.n, *wilson_interval(losses, cell.n))


def _algorithm_rows(group, key):
    return {row["position"]: row for row in group if row["algorithm"] == key}


def _finished(rows):
    return [row for row in rows.values() if row["status"] == "ok"]


def _nodes_text(rows):
    if not rows:
        return "-"
    finished = _finished(rows)
    if not finished:
        return f"skipped ({len(rows)}/{len(rows)})"
    mean = sum(int(row["nodes"]) for row in finished) / len(finished)
    note = f" (skipped {len(rows) - len(finished)}/{len(rows)})" if len(finished) < len(rows) else ""
    return f"{mean:,.0f}{note}"


def _ratio_text(numerator, denominator):
    """Paired over the positions where both finished, so both sums cover the same positions."""
    common = [p for p, row in numerator.items()
              if row["status"] == "ok" and denominator.get(p, {}).get("status") == "ok"]
    if not common:
        return "n/a"
    bottom = sum(int(denominator[p]["nodes"]) for p in common)
    return f"{sum(int(numerator[p]['nodes']) for p in common) / bottom:.1f}"


def _seconds_text(rows):
    finished = _finished(rows)
    if not finished:
        return "-"
    return f"{sum(float(row['wall_s']) for row in finished) / len(finished):.3f}"


def _agreement_text(rows):
    """Pruning must never change the result: value and best moves have to be identical."""
    groups = defaultdict(set)
    for row in rows:
        if row["status"] == "ok":
            groups[(row["position"], row["radius"], row["depth"])].add((row["value"], row["best_moves"]))
    counts = Counter((row["position"], row["radius"], row["depth"])
                     for row in rows if row["status"] == "ok")
    comparable = {key: values for key, values in groups.items() if counts[key] >= 2}
    disagree = sum(len(results) > 1 for results in comparable.values())
    if disagree:
        return f"WARNING: value or best moves differ between algorithms in {disagree} of {len(comparable)} comparable cases."
    return (f"Finished algorithms agree on value and best moves in {len(comparable)} comparable cases; "
            f"{len(groups) - len(comparable)} cases have only one finished algorithm.")


def _bandit_row(key, series):
    setting, strategy, c = key
    at = {int(row["step"]): row for row in series}

    def regret(step):
        row = at.get(step)
        return f"{float(row['mean_regret']):,.1f} ± {float(row['ci95']):,.1f}" if row else "no data"

    last = at.get(100_000)
    growth = (f"{float(at[100_000]['mean_regret']) / float(at[10_000]['mean_regret']):.2f}"
              if 100_000 in at and 10_000 in at else "n/a")
    return [setting, strategy, c or "-", series[-1]["seeds"], regret(1000), regret(10_000), regret(100_000),
            growth, *([f"{float(last['median_regret']):,.1f}", f"{float(last['p95_regret']):,.1f}",
                       f"{float(last['max_regret']):,.1f}", f"{float(last['wrong_arm_share']):.3f}"]
                      if last else ["no data"] * 4)]


def _bandit_note(setting, runs):
    """Rank the runs of one setting by final regret and name the pairs that cannot be told apart."""
    finals = {key: series[-1] for key, series in runs.items() if key[0] == setting}
    ranked = sorted(finals.items(), key=lambda item: float(item[1]["mean_regret"]))

    def name(key):
        return f"{key[1]}(c={key[2]})" if key[2] else key[1]

    text = ", ".join(f"{name(key)} {float(row['mean_regret']):,.0f} "
                     f"[wrong {float(row['wrong_arm_share']):.3f}]" for key, row in ranked)
    ties = [f"{name(k1)} and {name(k2)}" for (k1, r1), (k2, r2) in zip(ranked, ranked[1:])
            if float(r2["mean_regret"]) - float(r1["mean_regret"])
            <= float(r1["ci95"]) + float(r2["ci95"])]
    verdict = f" 95% bands overlap (descriptive): {'; '.join(ties)}." if ties else ""
    return f"{setting}, regret at T={ranked[0][1]['step']}: {text}.{verdict}"


def _is_baseline(spec):
    if spec["type"] == "alphabeta":
        return True
    return (spec["type"] == "mcts" and spec.get("c") == 1.4 and spec.get("formula") == "ucb1"
            and spec.get("final_rule") == "robust" and spec.get("radius") is None)


def _sort_key(spec):
    return (spec["type"], spec.get("iterations") or spec.get("depth") or 0, spec.get("rollout") or "")


def build(raw=RAW_DIR, out=RAW_DIR.parent):
    """Write everything under ``out`` from the CSV files in ``raw``."""
    report = Report(raw, out)
    report.nodes()
    pairs = dict.fromkeys(key[:2] for key in report.plan)
    pairs.update(dict.fromkeys(key[:2] for key in report.by_cell))
    for exp, game in pairs:
        if exp == "curve":
            y_label = "Score against random" if game == "ttt3" else "Score against MCTS(500, c=1.4)"
            report.curve(exp, game, _score_point, y_label, flag_half=True)
        elif exp == "curve_perfect":
            report.curve(exp, game, _loss_point, "Loss rate against perfect player", flag_half=False)
        else:
            report.match_table(exp, game)
        if exp == "formula" and game == "gomoku9":
            report.heatmap(game)
    report.root_stats()
    report.verify_quality()
    report.verify_exhaustive()
    report.bandit()
    report.timing()
    report.write_summary()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default=RAW_DIR, type=Path)
    parser.add_argument("--out", default=RAW_DIR.parent, type=Path)
    parser.add_argument("--snapshot", type=Path,
                        help="freeze input CSVs here before reading (default: OUT/source_data/raw)")
    args = parser.parse_args()
    frozen = args.snapshot or args.out / "source_data" / "raw"
    if frozen.resolve() == args.raw.resolve():
        parser.error("snapshot directory must differ from raw input directory")
    frozen.mkdir(parents=True, exist_ok=True)
    for old in frozen.glob("*.csv"):
        old.unlink()
    manifest = {"captured_utc": datetime.now(timezone.utc).isoformat(),
                "source": str(args.raw.resolve()),
                "note": "Each source file was captured once; a running writer may append after capture.",
                "files": {}}
    for source in sorted(args.raw.glob("*.csv")):
        data = source.read_bytes()
        (frozen / source.name).write_bytes(data)
        manifest["files"][source.name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    (frozen.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report = build(frozen, args.out)
    summary = args.out / "SUMMARY.md"
    with summary.open("a", encoding="utf-8") as handle:
        handle.write(f"\nInput snapshot: `{frozen}`; capture UTC {manifest['captured_utc']}. "
                     f"Hashes and source path are in `{frozen.parent / 'manifest.json'}`. "
                     "Live raw CSVs may contain later rows.\n")
    counts = Counter(entry[0] for entry in report.entries)
    print(f"RESULT: OK {counts['OK']}, PARTIAL {counts['PARTIAL']}, MISSING {counts['MISSING']}. "
          f"See {args.out / 'SUMMARY.md'}", flush=True)


if __name__ == "__main__":
    main()
