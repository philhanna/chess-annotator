import json
import threading
from contextlib import contextmanager
from http.client import HTTPConnection
from pathlib import Path

from annotate.adapters import web_app
from annotate.service import AnnotateSession


def test_frontend_root_points_to_top_level_frontend_dir() -> None:
    root = web_app.frontend_root()

    assert root == Path(__file__).resolve().parents[1] / "frontend"


def test_create_session_uses_frontend_root() -> None:
    session = web_app.create_session()

    assert session.frontend_root == web_app.frontend_root()


def test_asset_content_type_for_css() -> None:
    content_type = web_app.asset_content_type(Path("frontend/app.css"))

    assert content_type == "text/css"


def test_require_string_accepts_string_payload() -> None:
    assert web_app.require_string({"name": "demo"}, "name") == "demo"


def test_require_int_accepts_integer_payload() -> None:
    assert web_app.require_int({"ply": 12}, "ply") == 12


def test_require_bool_accepts_boolean_payload() -> None:
    assert web_app.require_bool({"diagram": True}, "diagram") is True


@contextmanager
def running_server():
    session = AnnotateSession(frontend_root=web_app.frontend_root())
    server = web_app.AnnotateHTTPServer(("127.0.0.1", 0), session)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def post_json(server: web_app.AnnotateHTTPServer, path: str, payload: dict[str, object] | None = None):
    connection = HTTPConnection(*server.server_address)
    body = json.dumps(payload or {})
    connection.request(
        "POST",
        path,
        body=body,
        headers={"Content-Type": "application/json"},
    )
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response.status, json.loads(data.decode("utf-8"))


def get_json(server: web_app.AnnotateHTTPServer, path: str):
    connection = HTTPConnection(*server.server_address)
    connection.request("GET", path)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response.status, json.loads(data.decode("utf-8"))


def test_open_route_returns_document_view_with_zeroth_ply() -> None:
    pgn_text = Path("tests/testdata/game1.pgn").read_text()

    with running_server() as server:
        status, payload = post_json(
            server,
            "/api/open",
            {"display_name": "game1.pgn", "pgn_text": pgn_text},
        )

    assert status == 200
    assert payload["session"]["source_name"] == "game1.pgn"
    assert payload["selected_ply"] == 0
    assert payload["move_rows"][0]["is_initial_position"] is True
    assert payload["diagram_enabled"] is False


def test_select_ply_and_navigate_routes_update_selection() -> None:
    pgn_text = Path("tests/testdata/game1.pgn").read_text()

    with running_server() as server:
        post_json(server, "/api/open", {"display_name": "game1.pgn", "pgn_text": pgn_text})
        status, selected = post_json(server, "/api/select-ply", {"ply": 3})
        assert status == 200
        assert selected["selected_ply"] == 3

        status, rewound = post_json(server, "/api/navigate", {"action": "start"})

    assert status == 200
    assert rewound["selected_ply"] == 0
    assert rewound["editor"]["diagram"] is False


def test_save_routes_preserve_root_comment_and_clear_unsaved_flag() -> None:
    pgn_text = Path("tests/testdata/game1.pgn").read_text()

    with running_server() as server:
        post_json(server, "/api/open", {"display_name": "game1.pgn", "pgn_text": pgn_text})
        status, applied = post_json(
            server,
            "/api/apply-annotation",
            {"comment": "Opening overview", "diagram": True},
        )
        assert status == 200
        assert applied["session"]["unsaved_changes"] is True

        status, payload = post_json(server, "/api/save")
        assert status == 200
        assert "Opening overview" in payload["pgn_text"]
        assert payload["suggested_filename"] == "game1-annotated.pgn"

        status, confirmed = post_json(
            server,
            "/api/confirm-save",
            {"output_name": "game1-annotated.pgn"},
        )

    assert status == 200
    assert confirmed["session"]["unsaved_changes"] is False
    assert confirmed["session"]["last_saved_name"] == "game1-annotated.pgn"


def test_clear_comments_route_clears_root_and_move_comments() -> None:
    pgn_text = Path("tests/testdata/game3.pgn").read_text()

    with running_server() as server:
        post_json(server, "/api/open", {"display_name": "game3.pgn", "pgn_text": pgn_text})
        post_json(
            server,
            "/api/apply-annotation",
            {"comment": "Opening overview", "diagram": False},
        )
        status, cleared = post_json(server, "/api/clear-comments")

    assert status == 200
    assert cleared["selected_ply"] == 0
    assert cleared["editor"]["comment"] == ""
    assert all(row["comment"] == "" for row in cleared["move_rows"])


def test_game_view_route_reports_current_selection() -> None:
    pgn_text = Path("tests/testdata/annotate-multi.pgn").read_text()

    with running_server() as server:
        post_json(server, "/api/open", {"display_name": "annotate-multi.pgn", "pgn_text": pgn_text})
        post_json(server, "/api/select-game", {"game_index": 1})
        post_json(server, "/api/select-ply", {"ply": 10})
        status, payload = get_json(server, "/api/game-view")

    assert status == 200
    assert payload["selected_game"]["index"] == 1
    assert payload["selected_ply"] == 10
    assert payload["editor"]["diagram"] is True
