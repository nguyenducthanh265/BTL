"""Build an auditable five-page conference-style draft from a frozen raw snapshot.

Run from project root: python -m paper.build --raw results/source_data/raw
The PDF uses PyMuPDF; main.tex uses the standard IEEEtran conference class.
"""
import argparse
import csv
import hashlib
import html
import json
import platform
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def metrics(raw):
    from experiments.plan import build_suite, row_key
    from experiments.report import load_games

    all_games, _ = load_games(raw)
    files = {}
    for path in sorted(raw.glob("*.csv")):
        data = path.read_bytes()
        files[path.name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    values = {"python": platform.python_version()}
    for suite in ("ttt3", "gomoku9", "xiangqi"):
        tasks = build_suite(suite)
        actual = [r for r in all_games if r["game"] == suite]
        keys = {row_key(r["exp"], r["game"], json.loads(r["a"]), json.loads(r["b"]), r["index"]) for r in actual}
        planned = {row_key(t["exp"], t["game"], t["a"], t["b"], t["index"]) for t in tasks}
        values[suite + "_actual"] = f"{len(keys):,}"
        values[suite + "_done"] = f"{len(keys & planned):,}"
        values[suite + "_planned"] = f"{len(planned):,}"
    quality = read(raw / "verify_quality.csv")
    exhaustive = read(raw / "verify_exhaustive.csv")
    qtable = ["| Iterations | Positions | Blunders | Rate |", "|---|---|---|---|"]
    etable = ["| Iterations | Seed/side runs | Leaf paths | Loss paths |", "|---|---|---|---|"]
    for it in sorted({int(r["iterations"]) for r in quality}):
        rows = [r for r in quality if int(r["iterations"]) == it]
        n, b = sum(int(r["positions"]) for r in rows), sum(int(r["blunders"]) for r in rows)
        qtable.append(f"| {it} | {n:,} | {b:,} | {b/n:.4f} |")
    for it in sorted({int(r["iterations"]) for r in exhaustive}):
        rows = [r for r in exhaustive if int(r["iterations"]) == it]
        n, losses = sum(int(r["lines"]) for r in rows), sum(int(r["losses"]) for r in rows)
        etable.append(f"| {it} | {len(rows)} | {n:,} | {losses:,} |")
    values["quality_table"] = "\n".join(qtable)
    values["exhaustive_table"] = "\n".join(etable)
    wdl = ["| Game / opponent | Iter. | n | W / D / L |", "|---|---|---|---|"]
    grouped = defaultdict(list)
    for r in all_games:
        if r["exp"] == "wdl":
            a, b = json.loads(r["a"]), json.loads(r["b"])
            if a.get("type") == "mcts" and a.get("iterations") in (100, 1000):
                key = (r["game"], a["iterations"], b["type"], b.get("depth"))
                grouped[key].append(r)
    for (game, it, opponent, depth), rows in sorted(grouped.items(), key=lambda pair: str(pair[0])):
        counts = Counter(float(r["a_score"]) for r in rows)
        opponent += f" d={depth}" if opponent == "alphabeta" else ""
        wdl.append(f"| {game} / {opponent} | {it} | {len(rows)} | {counts[1.0]} / {counts[0.5]} / {counts[0.0]} |")
    values["wdl_table"] = "\n".join(wdl)
    nodes = read(raw / "nodes.csv")
    ntable = ["| 3x3 start algorithm | Nodes | Value |", "|---|---|---|"]
    for r in nodes:
        if r["game"] == "ttt3" and r["position"] == "empty" and r["status"] == "ok":
            ntable.append(f"| {r['algorithm']} | {int(r['nodes']):,} | {r['value']} |")
    values["nodes_table"] = "\n".join(ntable)
    root = read(raw / "root_stats.csv")
    selected = [r for r in root if r["position"] == "assignment" and r["iterations"] == "1000" and r["seed"] == "0"]
    rtable = ["| Move (cell) | N | W | W/N | Chosen |", "|---|---|---|---|---|"]
    for r in selected:
        rtable.append(f"| {r['move']} | {r['N']} | {r['W']} | {r['W_over_N']} | {r['chosen']} |")
    values["root_table"] = "\n".join(rtable)
    return values, files


def blocks(text):
    result = []
    for part in re.split(r"\n\s*\n", text.strip()):
        part = part.strip()
        if not part:
            continue
        if part.startswith("|"):
            rows = [[v.strip() for v in line.strip("|").split("|")] for line in part.splitlines() if not re.fullmatch(r"[|:\s-]+", line)]
            result.append(("table", rows))
        elif part.startswith("## "):
            result.append(("h2", part[3:]))
        elif part.startswith("### "):
            result.append(("h3", part[4:]))
        elif part.startswith("!["):
            result.append(("image", re.match(r"!\[(.*?)\]\((.*?)\)", part).groups()))
        else:
            result.append(("p", " ".join(part.splitlines())))
    return result


def to_html(items):
    output = []
    for kind, value in items:
        if kind == "table":
            rows = ["<tr>" + "".join(f"<{('th' if i == 0 else 'td')}>{html.escape(cell)}</{('th' if i == 0 else 'td')}>" for cell in row) + "</tr>" for i, row in enumerate(value)]
            output.append("<table>" + "".join(rows) + "</table>")
        elif kind == "image":
            label, path = value
            output.append(f'<img src="{html.escape(path)}"><p class="caption">{html.escape(label)}</p>')
        else:
            output.append(f"<{kind}>{html.escape(value)}</{kind}>")
    return "\n".join(output)


def tex_escape(text):
    return "".join({"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}"}.get(c, c) for c in text)


def to_tex(items):
    output = []
    for kind, value in items:
        if kind in ("h2", "h3"):
            # The IEEE class numbers sections itself.
            value = re.sub(r"^[IVX]+\. ", "", value)
            output.append("\\" + ("section" if kind == "h2" else "subsection") + "{" + tex_escape(value) + "}")
        elif kind == "image":
            label, path = value
            output.append(r"\begin{figure}[t]\centering\includegraphics[width=\columnwidth]{" + path + r"}\caption{" + tex_escape(label) + r"}\end{figure}")
        elif kind == "table":
            n = len(value[0])
            lines = [r"\begin{center}\scriptsize\begin{tabular}{" + "l" * n + r"}\hline"]
            lines.extend(" & ".join(tex_escape(cell) for cell in row) + r" \\" for row in value)
            lines.append(r"\hline\end{tabular}\end{center}")
            output.append("\n".join(lines))
        else:
            output.append(tex_escape(value) + "\n")
    return "\n\n".join(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT / "results/source_data/raw")
    args = parser.parse_args()
    raw = args.raw.resolve()
    if not raw.exists():
        raise SystemExit("Create the frozen raw snapshot before building the paper.")
    values, hashes = metrics(raw)
    content = (OUT / "content.md").read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace("{{" + key + "}}", str(value))
    if re.search(r"\{\{.*?\}\}", content):
        raise ValueError("Unresolved metric placeholder")
    columns = [blocks(part) for part in content.split("<!-- column -->")]
    if len(columns) != 10:
        raise ValueError("The reviewed layout expects 10 columns / five pages")
    (OUT / "paper.md").write_text(content.replace("<!-- column -->", ""), encoding="utf-8")
    (OUT / "metrics.json").write_text(json.dumps({"values": values, "input_files": hashes}, indent=2) + "\n", encoding="utf-8")
    figure_dir = OUT / "figures"
    figure_dir.mkdir(exist_ok=True)
    report_root = raw.parent.parent if raw.parent.name == "source_data" else raw.parent
    for name in ("curve_ttt3.png",):
        source = report_root / "figures" / name
        if not source.exists():
            source = ROOT / "results/figures" / name
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copyfile(source, figure_dir / name)
    title = "Minimax, Alpha-Beta and UCT: Reproducible Game-Search Experiments"
    tex = r"\documentclass[conference]{IEEEtran}" + "\n" + r"\usepackage{graphicx,url}" + "\n" + r"\title{" + title + "}\n" + r"\author{\IEEEauthorblockN{Coursework review draft}\IEEEauthorblockA{Author details to be supplied by the project owner}}" + "\n" + r"\begin{document}\maketitle" + "\n"
    abstract = columns[0][1][1]
    keywords = columns[0][2][1].split(" - ", 1)[1]
    tex += r"\begin{abstract}" + tex_escape(abstract) + r"\end{abstract}" + "\n"
    tex += r"\begin{IEEEkeywords}" + tex_escape(keywords) + r"\end{IEEEkeywords}" + "\n"
    tex += to_tex(columns[0][3:]) + "\n\n"
    tex += "\n\n".join(to_tex(col) for col in columns[1:]) + "\n" + r"\end{document}" + "\n"
    (OUT / "main.tex").write_text(tex, encoding="utf-8")
    import fitz

    doc = fitz.open()
    archive = fitz.Archive(str(OUT))
    css = """body {font-family: 'Times New Roman',serif;font-size:10pt;line-height:1.1;color:#111;} p {margin:0 0 7pt;text-align:justify;} h2 {font-size:10pt;text-align:center;margin:8pt 0 7pt;font-weight:normal;} h3 {font-size:10pt;font-style:italic;margin:7pt 0 5pt;} table {width:100%;border-collapse:collapse;font-size:8pt;margin:6pt 0 9pt;} th {border-top:0.6pt solid #111;border-bottom:0.4pt solid #111;} td,th {padding:3pt 2pt;text-align:left;} tr:last-child td {border-bottom:0.6pt solid #111;} img {width:100%;} .caption {font-size:8pt;text-align:left;margin:5pt 0 10pt;}"""
    for i in range(5):
        page = doc.new_page(width=612, height=792)
        top = 54
        if i == 0:
            heading = f'<div style="font-family:serif;text-align:center"><p style="font-size:20pt;margin:0 0 9pt">{html.escape(title)}</p><p style="font-size:9pt;margin:0">Coursework review draft | 6 November 2026<br>Author details to be supplied by the project owner</p></div>'
            spare, scale = page.insert_htmlbox(fitz.Rect(45, 35, 567, 126), heading, scale_low=1)
            if spare < 0 or scale != 1:
                raise ValueError("Title overflows")
            top = 135
        for j, rect in enumerate((fitz.Rect(45, top, 297, 738), fitz.Rect(315, top, 567, 738))):
            spare, scale = page.insert_htmlbox(rect, to_html(columns[i * 2 + j]), css=css, archive=archive, scale_low=1)
            if spare < 0 or scale != 1:
                raise ValueError(f"Column {i*2+j+1} overflows; shorten content instead of shrinking type")
        page.insert_textbox(fitz.Rect(45, 753, 567, 772), f"Review draft - frozen CSV evidence; incomplete experiments are identified | {i+1}", fontsize=8, fontname="tiro", align=1)
    doc.set_metadata({"title": title, "author": "Coursework review draft", "subject": "IEEE-style review draft; not a final submission"})
    target = ROOT / "output/pdf/game_search_report.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(target)
    preview = ROOT / "tmp/pdfs"
    preview.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(doc):
        page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2)).save(preview / f"paper-{i+1}.png")
    print(f"Built {len(doc)} pages: {target}")


if __name__ == "__main__":
    main()
