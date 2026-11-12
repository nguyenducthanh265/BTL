"""JSON API and web page of the demo. Python standard library only.

The server keeps no game state. Every POST to /api/play carries the moves played so far:

    {"game": "xiangqi", "moves": [[70, 67]], "agent": {"type": "mcts", "iterations": 3000}}

The moves are replayed on a fresh game and the first illegal one is rejected. With an
"agent" the AI then adds one move, so the browser alone decides whose turn it is. Client
input is only ever parsed as JSON, checked against whitelists and clamped to safe ranges.
"""
import argparse
import json
import random
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from gameai.agents import build_agent
from gameai.games.tictactoe import TicTacToe
from gameai.games.xiangqi import COLS, Xiangqi
from gameai.search.minimax import search
from gameai.search.selection import FORMULAS

HOST = "127.0.0.1"
DEFAULT_PORT = 8000
MAX_BODY = 64 * 1024  # bytes; far more than the longest possible game needs
UNKNOWN_BODY_SECONDS = 1.0  # total drain deadline for a rejected POST path
MAX_ITERATIONS = 20000
TOP_CHILDREN = 10
ROLLOUTS = ("random", "heuristic", "cutoff")
PAGE = Path(__file__).with_name("index.html")

# Defaults answer within a few seconds on a laptop. On 3x3, depth 9 is a full search
# because the game cannot last longer than 9 plies.
_MCTS = {"c": 1.4, "formula": "ucb1"}
GAMES = {
    "ttt3": {
        "label": "Tic-Tac-Toe 3×3", "size": 3, "k": 3, "max_depth": 9,
        "mcts": {**_MCTS, "iterations": 2000, "rollout": "random"},
        "alphabeta": {"depth": 9},
    },
    "five9": {
        "label": "Cờ caro 5 quân 9×9", "size": 9, "k": 5, "max_depth": 5,
        "mcts": {**_MCTS, "iterations": 3000, "rollout": "heuristic", "radius": 2},
        "alphabeta": {"depth": 3, "radius": 2},
    },
    "five15": {
        "label": "Cờ caro 5 quân 15×15", "size": 15, "k": 5, "max_depth": 5,
        "mcts": {**_MCTS, "iterations": 3000, "rollout": "heuristic", "radius": 2},
        "alphabeta": {"depth": 2, "radius": 2},
    },
    "xiangqi": {
        "label": "Cờ tướng", "max_depth": 5,
        "mcts": {**_MCTS, "iterations": 3000, "rollout": "cutoff"},
        "alphabeta": {"depth": 3},
    },
}
PIECES = {
    1: "帥", 2: "仕", 3: "相", 4: "傌", 5: "俥", 6: "炮", 7: "兵",
    -1: "將", -2: "士", -3: "象", -4: "馬", -5: "車", -6: "砲", -7: "卒",
}


class BadRequest(Exception):
    """Invalid client input; the message is shown to the user."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ------------------------------------------------------------------ input validation
def pick(value, allowed, what):
    """Accept ``value`` only if it is a string from the whitelist ``allowed``."""
    if not isinstance(value, str) or value not in allowed:
        raise BadRequest(f"{what} không hợp lệ")
    return value


def clamp(spec, name, default, low, high, types=(int,)):
    """Read a number and force it into [low, high]."""
    value = spec.get(name, default)
    if type(value) not in types:  # not isinstance: in Python, True is also an int
        raise BadRequest(f"Tham số {name} không hợp lệ")
    return min(high, max(low, value))


def parse_agent(game_name, spec):
    """Turn the client's agent description into safe options for ``build_agent``."""
    if not isinstance(spec, dict):
        raise BadRequest("Cấu hình AI không hợp lệ")
    kind = pick(spec.get("type"), ("mcts", "alphabeta"), "Thuật toán")
    config = GAMES[game_name]
    defaults = config[kind]
    # Only big boards have candidate_moves worth restricting; Xiangqi has none at all.
    radius = clamp(spec, "radius", defaults["radius"], 1, 4) if "radius" in defaults else None
    if kind == "alphabeta":
        depth = clamp(spec, "depth", defaults["depth"], 1, config["max_depth"])
        return {"type": kind, "depth": depth, "radius": radius}
    return {
        "type": kind,
        "iterations": clamp(spec, "iterations", defaults["iterations"], 1, MAX_ITERATIONS),
        "c": clamp(spec, "c", defaults["c"], 0, 10, (int, float)),
        "formula": pick(spec.get("formula", defaults["formula"]), FORMULAS, "Công thức"),
        "rollout": pick(spec.get("rollout", defaults["rollout"]), ROLLOUTS, "Rollout"),
        "radius": radius,
    }


def parse_move(game, raw):
    """JSON to engine move. Types are strict because 1.0 == True == 1 in Python."""
    if isinstance(game, Xiangqi):
        if isinstance(raw, list) and len(raw) == 2 and all(type(cell) is int for cell in raw):
            return tuple(raw)
    elif type(raw) is int:
        return raw
    raise BadRequest("Nước đi sai định dạng")


# ------------------------------------------------------------------ game logic
def new_game(name):
    config = GAMES[name]
    return Xiangqi() if name == "xiangqi" else TicTacToe(config["size"], config["k"])


def move_label(game, move):
    """Readable move for the current position: (row, column), or piece and coordinates."""
    if not isinstance(game, Xiangqi):
        row, col = divmod(move, game.size)
        return f"({row + 1}, {col + 1})"

    def square(index):  # standard Xiangqi notation: files a-i, ranks 0-9 from Red's side
        row, col = divmod(index, COLS)
        return f"{'abcdefghi'[col]}{9 - row}"

    return f"{PIECES[game.board[move[0]]]} {square(move[0])}-{square(move[1])}"


def replay(game_name, moves):
    """Play the client's moves on a new game, checking each one against the rules."""
    game = new_game(game_name)
    last_label = None
    for raw in moves:
        move = parse_move(game, raw)
        if move not in game.legal_moves():
            raise BadRequest("Nước đi không hợp lệ")
        last_label = move_label(game, move)
        game.play(move)
    return game, last_label


def think(game, options):
    """Choose a move and report what the search saw: returns (move, analysis)."""
    rng = random.Random()
    started = time.perf_counter()
    if options["type"] == "alphabeta":
        # search() directly, not AlphaBetaAgent: the agent does not expose the value.
        radius = options["radius"]
        moves = None if radius is None else lambda state: state.candidate_moves(radius)
        result = search(game, depth=options["depth"], pruning=True, moves=moves, order=True)
        move = rng.choice(result.best_moves)
        return move, {
            "type": "alphabeta",
            "value": result.value,  # always from the point of view of player +1
            "nodes": result.nodes,
            "best_count": len(result.best_moves),
            "best_moves": [move_label(game, m) for m in result.best_moves[:TOP_CHILDREN]],
            "seconds": time.perf_counter() - started,
            "label": move_label(game, move),
            "options": options,
        }
    agent = build_agent(options)
    move = agent.choose(game, rng)
    seconds = time.perf_counter() - started
    root = agent.root
    # Same order as final_move's "robust" rule, so the first row is the move played.
    children = sorted(root.children, key=lambda child: (child.n, child.w), reverse=True)
    return move, {
        "type": "mcts",
        "iterations": root.n,
        "nodes": agent.nodes,
        "expanded": len(children),
        "candidates": len(children) + len(root.untried),
        "children": [
            {"move": child.move, "label": move_label(game, child.move),
             "n": child.n, "w": child.w, "ratio": child.w / child.n}
            for child in children[:TOP_CHILDREN]
        ],
        "seconds": seconds,
        "label": move_label(game, move),
        "options": options,
    }


def handle_play(request):
    """The whole API: validate, replay, optionally let the AI move, describe the result."""
    if not isinstance(request, dict):
        raise BadRequest("Yêu cầu phải là một đối tượng JSON")
    name = pick(request.get("game"), GAMES, "Trò chơi")
    moves = request.get("moves")
    if not isinstance(moves, list):
        raise BadRequest("Danh sách nước đi không hợp lệ")
    agent = request.get("agent")
    options = None if agent is None else parse_agent(name, agent)

    game, last_label = replay(name, moves)
    ai_move = analysis = None
    if options and game.winner() is None:
        ai_move, analysis = think(game, options)
        last_label = analysis["label"]
        game.play(ai_move)
        moves = moves + [ai_move]

    winner = game.winner()
    return {
        "game": name,
        "moves": moves,
        "board": game.board,
        "to_play": game.to_play,
        "legal": game.legal_moves(),
        "status": "playing" if winner is None else "finished",
        "winner": winner,
        "check": isinstance(game, Xiangqi) and game.general_attacked(game.to_play),
        "last_label": last_label,
        "ai_move": ai_move,
        "analysis": analysis,
    }


def config_json():
    return {
        "games": GAMES,
        "formulas": list(FORMULAS),
        "rollouts": ROLLOUTS,
        "max_iterations": MAX_ITERATIONS,
        "pieces": PIECES,
    }


# ------------------------------------------------------------------ HTTP
def _reject_constant(name):
    raise ValueError(f"{name} is not valid JSON")  # Python would accept NaN and Infinity


class Handler(BaseHTTPRequestHandler):
    timeout = 30  # seconds a client may stall on the socket; does not limit the search

    def log_message(self, *args):
        pass  # keep the console clean during the presentation

    def _send(self, status, body, content_type):
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except OSError:  # the browser left, for example after "New game" during a search
            self.close_connection = True

    def _send_json(self, status, data):
        self._send(status, json.dumps(data).encode(), "application/json; charset=utf-8")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise BadRequest("Thiếu Content-Length hợp lệ") from None
        if length < 0:
            raise BadRequest("Thiếu Content-Length hợp lệ")
        if length > MAX_BODY:
            raise BadRequest("Yêu cầu quá lớn", status=413)
        try:
            return json.loads(self.rfile.read(length), parse_constant=_reject_constant)
        except (ValueError, RecursionError, OSError):  # bad JSON, too deep, or client stalled
            raise BadRequest("Nội dung không phải JSON hợp lệ") from None

    def _discard_unknown_body(self):
        # Consume a normal bounded upload before closing. Otherwise unread body
        # bytes can reset a Windows connection before the JSON 404 reaches it.
        # Do not parse unknown-path bodies or wait indefinitely for a slow client.
        try:
            remaining = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return
        if not 0 <= remaining <= MAX_BODY:
            return
        deadline = time.monotonic() + UNKNOWN_BODY_SECONDS
        previous_timeout = self.connection.gettimeout()
        try:
            while remaining:
                seconds = deadline - time.monotonic()
                if seconds <= 0:
                    break
                self.connection.settimeout(seconds)
                chunk = self.rfile.read1(min(remaining, 8192))
                if not chunk:
                    break
                remaining -= len(chunk)
        except OSError:
            pass  # incomplete/aborted upload: keep the route's 404 semantics
        finally:
            self.connection.settimeout(previous_timeout)

    def do_GET(self):
        if self.path == "/":
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/config":
            self._send_json(200, config_json())
        else:
            self._send_json(404, {"error": "Không tìm thấy"})

    def do_POST(self):
        if self.path != "/api/play":
            self._discard_unknown_body()
            self._send_json(404, {"error": "Không tìm thấy"})
            return
        try:
            self._send_json(200, handle_play(self._read_json()))
        except BadRequest as error:
            self._send_json(error.status, {"error": str(error)})
        except Exception:  # a bug on our side: log it, tell the client nothing internal
            traceback.print_exc()
            self._send_json(500, {"error": "Lỗi máy chủ"})


class DemoServer(ThreadingHTTPServer):
    # One thread per request, so the page stays responsive during a search. Without this
    # flag Windows lets two servers share a port, and an old one could answer instead.
    allow_reuse_address = False


def make_server(port=DEFAULT_PORT):
    return DemoServer((HOST, port), Handler)


def main():
    parser = argparse.ArgumentParser(description="Playable demo of the game AI")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    try:
        server = make_server(args.port)
    except OSError:
        print(f"Port {args.port} is busy, using a free one instead.")
        server = make_server(0)
    print(f"Demo running at http://{HOST}:{server.server_address[1]}/  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
