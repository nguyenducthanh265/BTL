"""CSV match validation shared by resuming, coverage counts and reporting."""
import json
import math


def valid_game(row):
    """Reject incomplete or internally inconsistent records before counting a game.

    This checks the record structure; replaying game rules is a separate audit.
    """
    try:
        index, plies = int(row["index"]), int(row["plies"])
        moves = json.loads(row["moves"])
        if index < 0 or plies <= 0 or not isinstance(moves, list) or len(moves) != plies:
            return False
        if int(row["a_first"]) != int(index % 2 == 0):
            return False
        if float(row["a_score"]) not in (0.0, 0.5, 1.0):
            return False
        for side in ("a", "b"):
            spec = json.loads(row[side])
            if not isinstance(spec, dict) or "type" not in spec:
                return False
            seconds = float(row[f"{side}_time"])
            if not math.isfinite(seconds) or seconds < 0 or int(row[f"{side}_nodes"]) < 0:
                return False
        int(row["seed"])
        return bool(row["exp"] and row["game"])
    except (KeyError, TypeError, ValueError):
        return False


def game_key(row):
    """Canonical identity, independent of JSON whitespace and object key ordering."""
    return (row["exp"], row["game"], json.dumps(json.loads(row["a"]), sort_keys=True),
            json.dumps(json.loads(row["b"]), sort_keys=True), int(row["index"]))
