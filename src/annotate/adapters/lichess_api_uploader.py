import json
from urllib import parse, request

from annotate.ports import LichessUploader


class LichessAPIUploader(LichessUploader):
    """Upload PGN text to Lichess using the public import endpoint."""

    def __init__(self, api_url: str = "https://lichess.org/api/import") -> None:
        self.api_url = api_url

    def upload(self, pgn_text: str) -> str:
        """POST ``pgn_text`` to the Lichess import endpoint and return the analysis URL.

        The URL is extracted from the JSON response body when available,
        then from the ``Location`` header, and finally from the final
        redirected URL as a fallback.
        """
        payload = parse.urlencode({"pgn": pgn_text}).encode("utf-8")
        req = request.Request(
            self.api_url,
            data=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            location = response.headers.get("Location")
            if body:
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = None
                if isinstance(data, dict) and isinstance(data.get("url"), str):
                    return data["url"]
            if location:
                return location
            return response.geturl()
