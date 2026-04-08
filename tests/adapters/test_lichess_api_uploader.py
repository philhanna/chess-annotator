import json
from urllib import parse

from annotate.adapters.lichess_api_uploader import LichessAPIUploader


class FakeResponse:
    def __init__(self, body: str, *, url: str, headers: dict[str, str] | None = None):
        self._body = body.encode("utf-8")
        self._url = url
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_upload_posts_urlencoded_pgn_and_uses_json_url(monkeypatch):
    captured = {}

    def fake_urlopen(req):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["headers"] = dict(req.header_items())
        captured["body"] = req.data.decode("utf-8")
        return FakeResponse(
            json.dumps({"url": "https://lichess.org/abc123"}),
            url="https://lichess.org/api/import",
        )

    monkeypatch.setattr("annotate.adapters.lichess_api_uploader.request.urlopen", fake_urlopen)

    uploader = LichessAPIUploader()
    url = uploader.upload("1. e4 { [%tp] } e5 *")

    assert url == "https://lichess.org/abc123"
    assert captured["url"] == "https://lichess.org/api/import"
    assert captured["method"] == "POST"
    payload = parse.parse_qs(captured["body"])
    assert payload["pgn"] == ["1. e4 { [%tp] } e5 *"]


def test_upload_falls_back_to_location_header(monkeypatch):
    def fake_urlopen(_req):
        return FakeResponse(
            "",
            url="https://lichess.org/api/import",
            headers={"Location": "https://lichess.org/def456"},
        )

    monkeypatch.setattr("annotate.adapters.lichess_api_uploader.request.urlopen", fake_urlopen)

    uploader = LichessAPIUploader()
    assert uploader.upload("1. d4 d5 *") == "https://lichess.org/def456"


def test_upload_falls_back_to_response_url(monkeypatch):
    def fake_urlopen(_req):
        return FakeResponse("", url="https://lichess.org/ghi789")

    monkeypatch.setattr("annotate.adapters.lichess_api_uploader.request.urlopen", fake_urlopen)

    uploader = LichessAPIUploader()
    assert uploader.upload("1. c4 e5 *") == "https://lichess.org/ghi789"
