import httpx
import pytest

from annotate.cli import annotate
from annotate.cli import session as session_module

# ---------------------------------------------------------------------------
# Fake response data matching the server JSON shapes
# ---------------------------------------------------------------------------

_SEGMENT_SUMMARY = {
    "turning_point_ply": 1,
    "start_ply": 1,
    "end_ply": 20,
    "move_range": "1. e4 to 10...Nc6",
    "label": "Opening",
    "has_annotation": True,
}

_GAME_STATE = {
    "game_id": "game-1",
    "title": "Opened Game",
    "session_open": True,
    "has_unsaved_changes": False,
    "resumed": False,
    "segments": [_SEGMENT_SUMMARY],
}

_SEGMENT_DETAIL = {
    "turning_point_ply": 1,
    "start_ply": 1,
    "end_ply": 20,
    "move_range": "1. e4 to 10...Nc6",
    "label": "Opening",
    "annotation": "Plan the opening.",
    "move_list": "1. e4 e5 2. Nf3 Nc6",
}

_IMPORTED_GAME_STATE = {
    "game_id": "game-1",
    "title": "Imported Game",
    "session_open": True,
    "has_unsaved_changes": False,
    "resumed": False,
    "segments": [_SEGMENT_SUMMARY],
}


# ---------------------------------------------------------------------------
# Mock transport helpers
# ---------------------------------------------------------------------------

class _MockTransport(httpx.BaseTransport):
    """Routes requests to a handler function and records calls."""

    def __init__(self, handler):
        self._handler = handler
        self.calls: list[tuple[str, str]] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        return self._handler(request)


def _make_client(handler) -> tuple[httpx.Client, _MockTransport]:
    transport = _MockTransport(handler)
    client = httpx.Client(base_url="http://127.0.0.1:8765", transport=transport)
    return client, transport


def _standard_handler(request: httpx.Request) -> httpx.Response:
    """Handler that covers the common game-1 session workflow."""
    method, path = request.method, request.url.path

    if method == "GET" and path == "/games":
        return httpx.Response(200, json=[])
    if method == "POST" and path == "/games/game-1/session":
        return httpx.Response(200, json=_GAME_STATE)
    if method == "GET" and path == "/games/game-1/session":
        return httpx.Response(200, json=_GAME_STATE)
    if method == "GET" and path == "/games/game-1/session/segments":
        return httpx.Response(200, json=[_SEGMENT_SUMMARY])
    if method == "GET" and path.startswith("/games/game-1/session/segments/"):
        return httpx.Response(200, json=_SEGMENT_DETAIL)
    if method == "POST" and path == "/games/game-1/session/save":
        return httpx.Response(200, json=_GAME_STATE)
    if method == "DELETE" and path == "/games/game-1/session":
        return httpx.Response(200, json={"game_id": "game-1", "closed": True, "requires_confirmation": False})

    return httpx.Response(404, json={"detail": f"Not found: {method} {path}"})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_cli_state(monkeypatch):
    session_module.state.game_id = None
    session_module.state.current_turning_point_ply = None
    session_module._client = None
    # Skip the server-launch probe — tests manage their own mock client.
    monkeypatch.setattr(annotate, "_ensure_server_running", lambda: None)
    yield
    session_module.state.game_id = None
    session_module.state.current_turning_point_ply = None
    session_module._client = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_repl_open_list_view_save_and_quit(monkeypatch, capsys):
    client, transport = _make_client(_standard_handler)
    monkeypatch.setattr(session_module, "_client", client)

    inputs = iter(["open game-1", "list", "1", "view", "save", "quit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    with pytest.raises(SystemExit):
        annotate.main()

    out = capsys.readouterr().out
    assert "Opened: Opened Game" in out
    assert "1. e4 to 10...Nc6" in out
    assert "Plan the opening." in out
    assert "Saved." in out
    assert ("POST", "/games/game-1/session") in transport.calls
    assert ("POST", "/games/game-1/session/save") in transport.calls


def test_repl_import_handles_overwrite_prompt(monkeypatch, tmp_path, capsys):
    pgn_path = tmp_path / "game.pgn"
    pgn_path.write_text(
        "[Event \"Test\"]\n[White \"White\"]\n[Black \"Black\"]\n[Date \"2024.01.01\"]\n\n1. e4 e5 *\n"
    )

    post_count = {"n": 0}

    def import_handler(request: httpx.Request) -> httpx.Response:
        method, path = request.method, request.url.path
        if method == "GET" and path == "/games":
            return httpx.Response(200, json=[])
        if method == "POST" and path == "/games":
            post_count["n"] += 1
            if post_count["n"] == 1:
                return httpx.Response(409, json={"detail": "Game id already exists: game-1"})
            return httpx.Response(201, json=_IMPORTED_GAME_STATE)
        if method == "DELETE" and path == "/games/game-1/session":
            return httpx.Response(200, json={"game_id": "game-1", "closed": True, "requires_confirmation": False})
        return httpx.Response(404, json={"detail": f"Not found: {method} {path}"})

    client, transport = _make_client(import_handler)
    monkeypatch.setattr(session_module, "_client", client)

    # Patch get_config in the import command module so author is set.
    from types import SimpleNamespace
    import annotate.cli.commands.import_game as import_mod
    monkeypatch.setattr(
        import_mod,
        "get_config",
        lambda: SimpleNamespace(author="Tester", diagram_size=360, page_size="a4", server_url="http://127.0.0.1:8765"),
    )

    inputs = iter([
        f"import {pgn_path}",
        "game-1",
        "2024.01.01",
        "white",
        "yes",  # confirm overwrite
        "quit",
    ])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    with pytest.raises(SystemExit):
        annotate.main()

    out = capsys.readouterr().out
    assert "Imported and opened: Imported Game" in out
    assert post_count["n"] == 2


def test_view_shows_annotation_text(monkeypatch, capsys):
    client, transport = _make_client(_standard_handler)
    monkeypatch.setattr(session_module, "_client", client)

    inputs = iter(["open game-1", "view", "quit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    with pytest.raises(SystemExit):
        annotate.main()

    out = capsys.readouterr().out
    assert "Plan the opening." in out
