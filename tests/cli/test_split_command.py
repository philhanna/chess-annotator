from types import SimpleNamespace

from annotate.cli.commands.split import cmd_split
from annotate.cli import session


class FakeService:
    def __init__(self) -> None:
        self.calls = []

    def add_turning_point(self, *, game_id, ply, label):
        self.calls.append(
            {
                "game_id": game_id,
                "ply": ply,
                "label": label,
            }
        )
        return [SimpleNamespace(turning_point_ply=ply)]


def test_split_strips_surrounding_quotes_from_label(monkeypatch):
    fake_service = FakeService()
    session.state.game_id = "game-1"
    session.state.current_turning_point_ply = None
    monkeypatch.setattr(session, "get_service", lambda: fake_service)
    monkeypatch.setattr(session, "print", lambda msg="": None)
    monkeypatch.setattr(session, "err", lambda msg: None)

    cmd_split(["14w", '"Plan Shift"'])

    assert fake_service.calls == [
        {
            "game_id": "game-1",
            "ply": 27,
            "label": "Plan Shift",
        }
    ]
    assert session.state.current_turning_point_ply == 27
