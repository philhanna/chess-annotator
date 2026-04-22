import pytest

from annotate.adapters import cli


def test_parse_args_defaults_to_system_browser() -> None:
    args = cli.parse_args([])

    assert args.browser is None


def test_parse_args_accepts_browser_name() -> None:
    args = cli.parse_args(["--browser", "firefox"])

    assert args.browser == "firefox"


def test_open_browser_uses_system_default_when_not_specified(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []

    def fake_open(url: str) -> None:
        opened.append(url)

    monkeypatch.setattr(cli.webbrowser, "open", fake_open)

    cli.open_browser("http://127.0.0.1:9999/")

    assert opened == ["http://127.0.0.1:9999/"]


def test_open_browser_uses_named_browser_when_specified(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []

    class DummyBrowser:
        def open(self, url: str) -> None:
            opened.append(url)

    monkeypatch.setattr(cli.webbrowser, "get", lambda name: DummyBrowser())

    cli.open_browser("http://127.0.0.1:9999/", browser_name="firefox")

    assert opened == ["http://127.0.0.1:9999/"]


def test_open_browser_exits_cleanly_for_unknown_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error(name: str):
        raise cli.webbrowser.Error("not found")

    monkeypatch.setattr(cli.webbrowser, "get", raise_error)

    with pytest.raises(SystemExit, match="Unable to locate browser 'firefox'"):
        cli.open_browser("http://127.0.0.1:9999/", browser_name="firefox")
