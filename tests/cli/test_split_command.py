import httpx
import pytest

from annotate.cli.commands.split import cmd_split
from annotate.cli import session


class _MockTransport(httpx.BaseTransport):
    def __init__(self, handler):
        self._handler = handler
        self.calls = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path, request.read()))
        return self._handler(request)


def test_split_strips_surrounding_quotes_from_label(monkeypatch):
    received: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json
        body = _json.loads(request.read())
        received.append(body)
        return httpx.Response(
            200,
            json=[{"turning_point_ply": body["ply"], "start_ply": 1, "end_ply": 30,
                   "move_range": "1. e4 to 15. Nf3", "label": body["label"], "has_annotation": False}],
        )

    transport = _MockTransport(handler)
    mock_client = httpx.Client(base_url="http://127.0.0.1:8765", transport=transport)

    session.state.game_id = "game-1"
    session.state.current_turning_point_ply = None
    monkeypatch.setattr(session, "_client", mock_client)
    monkeypatch.setattr(session, "print", lambda msg="": None)
    monkeypatch.setattr(session, "err", lambda msg: None)

    cmd_split(["14w", '"Plan Shift"'])

    assert len(received) == 1
    assert received[0]["ply"] == 27
    assert received[0]["label"] == "Plan Shift"
    assert session.state.current_turning_point_ply == 27

    # Cleanup
    session.state.game_id = None
    session.state.current_turning_point_ply = None
    session._client = None
