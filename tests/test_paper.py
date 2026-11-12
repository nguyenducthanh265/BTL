"""The paper must use the same validated match identities as the report."""
import csv
import json

from experiments.plan import mcts
from experiments.runner import FIELDS
from paper.build import metrics


def test_paper_ignores_retained_invalid_rows_and_canonical_duplicates(tmp_path):
    good = dict(exp="wdl", game="ttt3", a=json.dumps(mcts(1000), sort_keys=True),
                b=json.dumps({"type": "random"}), index=0, a_first=1, a_score=1,
                plies=5, a_time=0.1, b_time=0.1, a_nodes=10, b_nodes=0, seed=42,
                moves="[0,3,1,4,2]")
    duplicate = {**good, "a": json.dumps(dict(reversed(list(mcts(1000).items()))))}
    # A malformed newline-terminated record can remain when the runner resumes.
    invalid = {**good, "index": 1, "a_first": 0, "moves": "[broken]"}
    with (tmp_path / "ttt3.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        writer.writeheader()
        writer.writerows([good, duplicate, invalid])
    values, _ = metrics(tmp_path)
    assert values["ttt3_actual"] == "1"
    assert "| ttt3 / random | 1000 | 1 | 1 / 0 / 0 |" in values["wdl_table"]
