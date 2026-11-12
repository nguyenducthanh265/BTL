"""The demo's JSON API, exercised over real HTTP against a server on a free port."""
import http.client
import json
import select
import threading

import pytest

from gameai.demo.server import MAX_BODY, make_server, parse_agent
from gameai.search.selection import FORMULAS

ALL_GAMES = ("ttt3", "five9", "five15", "xiangqi")
X_WINS = [0, 3, 1, 4, 2]  # X completes the top row
DRAW = [0, 1, 2, 4, 3, 5, 7, 6, 8]
# Red cannon to the e-file, then the e-soldiers trade, opening the file onto the black general.
XIANGQI_CHECK = [[70, 67], [31, 40], [58, 49], [27, 36], [49, 40]]
QUICK_MCTS = {"type": "mcts", "iterations": 30}
QUICK_ALPHABETA = {"type": "alphabeta", "depth": 1}


@pytest.fixture(scope="module")
def port():
    server = make_server(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


def request(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=120)
    try:
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        return response.status, response.getheader("Content-Type"), response.read()
    finally:
        connection.close()


def post_raw(port, body):
    status, _, data = request(port, "POST", "/api/play", body)
    return status, json.loads(data)


def post(port, **fields):
    return post_raw(port, json.dumps(fields))


def play(port, **fields):
    status, data = post(port, **fields)
    assert status == 200, data
    return data


def assert_rejected(port, **fields):
    status, data = post(port, **fields)
    assert status == 400
    assert isinstance(data["error"], str) and data["error"]


# ------------------------------------------------------------------ page and config
def test_server_binds_to_loopback_only():
    server = make_server(0)
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()


def test_a_busy_port_is_an_error_rather_than_a_shared_one(port):
    with pytest.raises(OSError):
        make_server(port)


def test_page_is_self_contained_utf8_html(port):
    status, content_type, data = request(port, "GET", "/")
    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    page = data.decode("utf-8")
    assert "https://" not in page and "http://" not in page  # nothing to fetch when offline
    assert "Hoàn tác" in page and "Ván mới" in page


def test_config_lists_whitelists_and_defaults(port):
    status, _, data = request(port, "GET", "/api/config")
    config = json.loads(data)
    assert status == 200
    assert tuple(config["games"]) == ALL_GAMES
    assert config["formulas"] == list(FORMULAS)
    assert config["rollouts"] == ["random", "heuristic", "cutoff"]
    assert config["games"]["xiangqi"]["mcts"]["rollout"] == "cutoff"
    assert config["games"]["five9"]["mcts"]["radius"] == 2
    assert config["games"]["five15"]["alphabeta"]["radius"] == 2


def test_unknown_path_is_404_json(port):
    status, _, data = request(port, "GET", "/etc/passwd")
    assert status == 404 and "error" in json.loads(data)
    status, _, data = request(port, "POST", "/nope", "{}")
    assert status == 404 and "error" in json.loads(data)


def test_unknown_post_consumes_a_fragmented_body_before_closing(port):
    # A normal upload can span packets. Closing with unread bytes can reset the
    # connection on Windows before the client receives its JSON error response.
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.putrequest("POST", "/nope")
        connection.putheader("Content-Length", "2")
        connection.endheaders()
        connection.send(b"{")
        assert not select.select([connection.sock], [], [], 0.2)[0], \
            "server closed/replied before consuming the complete bounded body"
        connection.send(b"}")
        response = connection.getresponse()
        assert response.status == 404 and "error" in json.loads(response.read())
    finally:
        connection.close()


@pytest.mark.parametrize("length", [str(MAX_BODY + 1), "-1", "invalid"])
def test_unknown_post_does_not_wait_for_an_unbounded_or_invalid_body(port, length):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.putrequest("POST", "/nope")
        connection.putheader("Content-Length", length)
        connection.endheaders()  # no upload: a rejected path must remain bounded
        response = connection.getresponse()
        assert response.status == 404 and "error" in json.loads(response.read())
    finally:
        connection.close()


def test_unknown_post_accepts_maximum_body_without_parsing_it(port):
    status, _, data = request(port, "POST", "/nope", b"x" * MAX_BODY)
    assert status == 404 and "error" in json.loads(data)


def test_unknown_post_incomplete_upload_has_a_short_deadline(port):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.putrequest("POST", "/nope")
        connection.putheader("Content-Length", "2")
        connection.endheaders()
        connection.send(b"{")  # never finish the body: do not occupy a worker for 30s
        response = connection.getresponse()
        assert response.status == 404 and "error" in json.loads(response.read())
    finally:
        connection.close()


# ------------------------------------------------------------------ replaying moves
@pytest.mark.parametrize("game, cells, legal", [
    ("ttt3", 9, 9), ("five9", 81, 81), ("five15", 225, 225), ("xiangqi", 90, 44),
])
def test_start_position(port, game, cells, legal):
    data = play(port, game=game, moves=[])
    assert len(data["board"]) == cells and len(data["legal"]) == legal
    assert data["to_play"] == 1 and data["status"] == "playing" and data["winner"] is None
    assert data["moves"] == [] and data["ai_move"] is None and data["analysis"] is None


def test_legal_moves_are_accepted(port):
    data = play(port, game="ttt3", moves=[4])
    assert data["board"][4] == 1 and data["to_play"] == -1 and 4 not in data["legal"]
    data = play(port, game="xiangqi", moves=[[70, 67]])
    assert data["board"][67] == 6 and data["board"][70] == 0 and data["moves"] == [[70, 67]]


@pytest.mark.parametrize("game, moves", [
    ("ttt3", [4, 4]),  # occupied
    ("ttt3", [9]),  # off the board
    ("ttt3", [-1]),  # would wrap around as a Python index
    ("five9", [81]),
    ("xiangqi", [[0, 1]]),  # chariot onto its own horse
    ("xiangqi", [[0, 9]]),  # black piece on red's turn
    ("xiangqi", [[70, 70]]),
    ("xiangqi", [[-20, 67]]),
    ("ttt3", X_WINS + [5]),  # the game is already over
])
def test_illegal_moves_are_rejected(port, game, moves):
    assert_rejected(port, game=game, moves=moves)


@pytest.mark.parametrize("game, move", [
    ("ttt3", True),  # True == 1 and 1.0 == 1 in Python, so a plain "in legal" would pass
    ("ttt3", 1.0),
    ("ttt3", "4"),
    ("ttt3", None),
    ("ttt3", [4]),
    ("ttt3", {"cell": 4}),
    ("xiangqi", 70),
    ("xiangqi", [70]),
    ("xiangqi", [70, 67, 1]),
    ("xiangqi", [70.0, 67]),
    ("xiangqi", [True, 67]),
    ("xiangqi", ["70", "67"]),
    ("xiangqi", None),
])
def test_wrongly_typed_moves_are_rejected(port, game, move):
    assert_rejected(port, game=game, moves=[move])


# ------------------------------------------------------------------ malformed requests
@pytest.mark.parametrize("body", [
    b"",
    b"not json",
    b"{",
    b"[1, 2, 3]",
    b"null",
    b"\xff\xfe\x00garbage",
    b'{"game": "ttt3", "moves": [NaN]}',
    b'{"game": "ttt3", "moves": [], "agent": {"type": "mcts", "c": NaN}}',
    b'{"game": "ttt3", "moves": [], "agent": {"type": "mcts", "c": Infinity}}',
    pytest.param(b"[" * 50_000, id="too_deeply_nested"),
])
def test_malformed_body_is_rejected(port, body):
    status, data = post_raw(port, body)
    assert status == 400 and "error" in data


@pytest.mark.parametrize("fields", [
    {"game": "ttt3"},
    {"game": "ttt3", "moves": "012"},
    {"game": "ttt3", "moves": {"0": 0}},
    {"moves": []},
])
def test_missing_or_wrong_fields_are_rejected(port, fields):
    assert_rejected(port, **fields)


@pytest.mark.parametrize("game", ["chess", "", None, 3, ["ttt3"], {"a": 1}, "__class__"])
def test_unknown_game_is_rejected(port, game):
    assert_rejected(port, game=game, moves=[])


def test_oversized_body_is_refused_without_being_read(port):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    connection.putrequest("POST", "/api/play")
    connection.putheader("Content-Length", str(MAX_BODY + 1))
    connection.endheaders()
    response = connection.getresponse()
    assert response.status == 413 and "error" in json.loads(response.read())
    connection.close()


@pytest.mark.parametrize("value", ["abc", "-5", ""])
def test_bad_content_length_is_rejected(port, value):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    connection.putrequest("POST", "/api/play")
    connection.putheader("Content-Length", value)
    connection.endheaders()
    response = connection.getresponse()
    assert response.status == 400 and "error" in json.loads(response.read())
    connection.close()


@pytest.mark.parametrize("agent", [
    "mcts",
    ["mcts"],
    {},
    {"type": "perfect"},
    {"type": ["mcts"]},
    {"type": "mcts", "formula": "evil"},
    {"type": "mcts", "formula": ["ucb1"]},
    {"type": "mcts", "rollout": "os.system"},
    {"type": "mcts", "rollout": {}},
    {"type": "mcts", "iterations": "100"},
    {"type": "mcts", "iterations": 1.5},
    {"type": "mcts", "iterations": True},
    {"type": "mcts", "c": "1.4"},
    {"type": "mcts", "c": True},
    {"type": "mcts", "radius": "2"},
    {"type": "alphabeta", "depth": "3"},
    {"type": "alphabeta", "depth": 2.5},
])
def test_bad_agent_is_rejected(port, agent):
    assert_rejected(port, game="five9", moves=[], agent=agent)


# ------------------------------------------------------------------ clamping
@pytest.mark.parametrize("asked, used", [(10**9, 20000), (0, 1), (-5, 1), (77, 77)])
def test_iterations_are_clamped(port, asked, used):
    # Two cells left, so that even the 20000 iterations of the upper bound finish fast.
    agent = {"type": "mcts", "iterations": asked}
    data = play(port, game="ttt3", moves=[0, 1, 2, 4, 3, 5, 7], agent=agent)
    assert data["analysis"]["options"]["iterations"] == used
    assert data["analysis"]["iterations"] == used
    assert sum(child["n"] for child in data["analysis"]["children"]) == used


@pytest.mark.parametrize("game, asked, used", [
    ("xiangqi", 99, 5), ("five9", 99, 5), ("five15", 6, 5), ("xiangqi", 0, 1), ("five9", -3, 1),
    ("ttt3", 99, 9),
])
def test_depth_is_clamped(game, asked, used):
    assert parse_agent(game, {"type": "alphabeta", "depth": asked})["depth"] == used


def test_full_search_is_allowed_on_3x3(port):
    data = play(port, game="ttt3", moves=[], agent={"type": "alphabeta", "depth": 99})
    assert data["analysis"]["options"]["depth"] == 9
    assert data["analysis"]["value"] == 0  # the game-theoretic value of Tic-Tac-Toe


def test_c_and_radius_are_clamped():
    options = parse_agent("five9", {"type": "mcts", "c": 1e9, "radius": 99})
    assert options["c"] == 10 and options["radius"] == 4
    options = parse_agent("five9", {"type": "mcts", "c": -1, "radius": -1})
    assert options["c"] == 0 and options["radius"] == 1


@pytest.mark.parametrize("game", ["ttt3", "xiangqi"])
@pytest.mark.parametrize("kind", ["mcts", "alphabeta"])
def test_radius_is_ignored_where_it_does_not_apply(game, kind):
    # Xiangqi has no candidate_moves, and 3x3 should search every move.
    assert parse_agent(game, {"type": kind, "radius": 2})["radius"] is None


@pytest.mark.parametrize("game", ALL_GAMES)
def test_defaults_fill_in_missing_options(game):
    assert parse_agent(game, {"type": "mcts"})["iterations"] >= 1
    assert parse_agent(game, {"type": "alphabeta"})["depth"] >= 1


# ------------------------------------------------------------------ the AI reply
def assert_valid_reply(port, game, before, data):
    """The reply was legal before it was played, and the server accepts it on replay."""
    legal_before = play(port, game=game, moves=before)["legal"]
    assert data["ai_move"] in legal_before
    assert data["moves"] == before + [data["ai_move"]]
    again = play(port, game=game, moves=data["moves"])
    assert again["board"] == data["board"] and again["to_play"] == data["to_play"]


@pytest.mark.parametrize("game, moves", [
    ("ttt3", []), ("ttt3", [4]),
    ("five9", []), ("five9", [40]),
    ("five15", []), ("five15", [112]),
    ("xiangqi", []), ("xiangqi", [[70, 67]]),
])
@pytest.mark.parametrize("agent", [QUICK_MCTS, QUICK_ALPHABETA])
def test_ai_reply_is_legal(port, game, moves, agent):
    assert_valid_reply(port, game, moves, play(port, game=game, moves=moves, agent=agent))


@pytest.mark.parametrize("game", ALL_GAMES)
@pytest.mark.parametrize("rollout", ["random", "heuristic", "cutoff"])
def test_every_rollout_works_on_every_game(port, game, rollout):
    agent = {"type": "mcts", "iterations": 10, "rollout": rollout}
    assert_valid_reply(port, game, [], play(port, game=game, moves=[], agent=agent))


@pytest.mark.parametrize("formula", FORMULAS)
def test_every_formula_works(port, formula):
    agent = {"type": "mcts", "iterations": 50, "formula": formula}
    assert_valid_reply(port, "ttt3", [], play(port, game="ttt3", moves=[], agent=agent))


@pytest.mark.parametrize("iterations", [1, 2])
def test_mcts_works_with_fewer_iterations_than_moves(port, iterations):
    agent = {"type": "mcts", "iterations": iterations}
    data = play(port, game="xiangqi", moves=[], agent=agent)
    assert data["analysis"]["expanded"] == iterations and data["analysis"]["candidates"] == 44
    assert_valid_reply(port, "xiangqi", [], data)


def test_radius_limits_big_board_replies_to_cells_near_stones(port):
    agent = {"type": "mcts", "iterations": 100, "radius": 1}
    data = play(port, game="five15", moves=[112], agent=agent)  # centre stone
    assert data["analysis"]["candidates"] == 8


@pytest.mark.parametrize("moves", [X_WINS, DRAW])
@pytest.mark.parametrize("agent", [QUICK_MCTS, QUICK_ALPHABETA])
def test_finished_game_gets_no_ai_move(port, moves, agent):
    data = play(port, game="ttt3", moves=moves, agent=agent)
    assert data["status"] == "finished" and data["legal"] == []
    assert data["ai_move"] is None and data["analysis"] is None and data["moves"] == moves


def test_result_is_reported(port):
    assert play(port, game="ttt3", moves=X_WINS)["winner"] == 1
    assert play(port, game="ttt3", moves=DRAW)["winner"] == 0


def test_full_optimal_3x3_game_over_http_is_a_draw(port):
    moves = []
    for _ in range(9):
        data = play(port, game="ttt3", moves=moves, agent={"type": "alphabeta", "depth": 9})
        assert_valid_reply(port, "ttt3", moves, data)
        moves = data["moves"]
        if data["status"] == "finished":
            break
    assert len(moves) == 9 and data["winner"] == 0 and data["legal"] == []


def test_five9_win_undo_and_reset_over_http(port):
    # X builds five on row 1, O has four on row 2. The last stone ends the game.
    moves = [0, 9, 1, 10, 2, 11, 3, 12, 4]
    won = play(port, game="five9", moves=moves, agent=QUICK_MCTS)
    assert won["winner"] == 1 and won["status"] == "finished" and won["legal"] == []
    assert won["ai_move"] is None  # no extra AI move after the human wins
    undone = play(port, game="five9", moves=moves[:-1])
    assert undone["status"] == "playing" and undone["to_play"] == 1
    assert undone["board"][4] == 0 and 4 in undone["legal"]
    reset = play(port, game="five9", moves=[])
    assert reset["board"] == [0] * 81 and len(reset["legal"]) == 81


def test_xiangqi_capture_undo_and_reset_over_http(port):
    captured = play(port, game="xiangqi", moves=XIANGQI_CHECK)
    assert captured["board"][40] == 7 and captured["board"][49] == 0
    undone = play(port, game="xiangqi", moves=XIANGQI_CHECK[:-1])
    assert undone["board"][40] == -7 and undone["board"][49] == 7
    assert undone["to_play"] == 1 and undone["check"] is False
    reset = play(port, game="xiangqi", moves=[])
    assert reset["board"][70] == 6 and reset["board"][67] == 0
    assert reset["to_play"] == 1 and len(reset["legal"]) == 44


def test_rejected_request_does_not_change_other_games_or_future_replays(port):
    first = play(port, game="ttt3", moves=[4])
    assert_rejected(port, game="ttt3", moves=[4, 4], agent=QUICK_MCTS)
    other = play(port, game="xiangqi", moves=[[70, 67]])
    assert other["board"][67] == 6
    again = play(port, game="ttt3", moves=[4])
    assert again["board"] == first["board"] and again["moves"] == [4]
    assert play(port, game="ttt3", moves=[])["board"] == [0] * 9


def test_ai_takes_a_win_and_finishes_the_game(port):
    agent = {"type": "alphabeta", "depth": 9}
    data = play(port, game="ttt3", moves=[0, 3, 1, 4], agent=agent)
    assert data["ai_move"] == 2 and data["status"] == "finished" and data["winner"] == 1
    assert data["legal"] == []


# ------------------------------------------------------------------ what the AI thought
def test_mcts_analysis_describes_the_root(port):
    agent = {"type": "mcts", "iterations": 500, "formula": "ucb1", "rollout": "random", "c": 1.4}
    data = play(port, game="ttt3", moves=[], agent=agent)
    analysis = data["analysis"]
    assert analysis["type"] == "mcts" and analysis["iterations"] == 500
    assert analysis["seconds"] >= 0 and analysis["nodes"] >= 10
    children = analysis["children"]
    assert sum(child["n"] for child in children) == 500
    assert [child["n"] for child in children] == sorted((c["n"] for c in children), reverse=True)
    for child in children:
        assert child["ratio"] == pytest.approx(child["w"] / child["n"])
        assert 0 <= child["ratio"] <= 1
        assert child["label"]
    assert children[0]["move"] == data["ai_move"]  # robust child: the most visited move


def test_mcts_table_is_limited_to_the_top_children(port):
    agent = {"type": "mcts", "iterations": 100}
    analysis = play(port, game="xiangqi", moves=[], agent=agent)["analysis"]
    assert len(analysis["children"]) == 10
    assert analysis["expanded"] == 44 and analysis["candidates"] == 44


def test_xiangqi_labels_name_the_piece(port):
    agent = {"type": "mcts", "iterations": 100}
    analysis = play(port, game="xiangqi", moves=[], agent=agent)["analysis"]
    pieces = "帥仕相傌俥炮兵"
    assert all(child["label"][0] in pieces for child in analysis["children"])


def test_alphabeta_analysis_reports_value_and_nodes(port):
    data = play(port, game="ttt3", moves=[0, 3, 1, 4], agent={"type": "alphabeta", "depth": 9})
    analysis = data["analysis"]
    assert analysis["type"] == "alphabeta" and analysis["seconds"] >= 0
    assert analysis["nodes"] > 1
    assert analysis["value"] == 999_999  # X wins with the next stone
    assert analysis["best_moves"]


def test_alphabeta_value_is_from_the_first_players_view(port):
    # O to move and winning with cell 6, so the value is negative although O is the one thinking.
    agent = {"type": "alphabeta", "depth": 9}
    data = play(port, game="ttt3", moves=[0, 4, 1, 2, 3], agent=agent)
    assert data["ai_move"] == 6 and data["analysis"]["value"] == -999_999


# ------------------------------------------------------------------ Xiangqi status
def test_check_is_reported(port):
    data = play(port, game="xiangqi", moves=XIANGQI_CHECK)
    assert data["check"] is True and data["to_play"] == -1 and data["status"] == "playing"
    assert play(port, game="xiangqi", moves=XIANGQI_CHECK[:-1])["check"] is False
    assert play(port, game="ttt3", moves=[])["check"] is False


def test_replies_under_check_answer_the_check(port):
    data = play(port, game="xiangqi", moves=XIANGQI_CHECK, agent=QUICK_MCTS)
    assert data["to_play"] == 1
    assert_valid_reply(port, "xiangqi", XIANGQI_CHECK, data)


# ------------------------------------------------------------------ responsiveness
def test_server_answers_while_the_ai_is_thinking(port):
    finished = threading.Event()

    def think():
        play(port, game="xiangqi", moves=[], agent={"type": "mcts", "iterations": 3000})
        finished.set()

    thread = threading.Thread(target=think)
    thread.start()
    status, _, _ = request(port, "GET", "/api/config")
    answered_during_search = not finished.is_set()
    thread.join()
    assert status == 200 and answered_during_search
