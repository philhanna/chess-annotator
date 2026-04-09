import json
from urllib import parse, request

from annotate.ports import LichessUploader


class LichessAPIUploader(LichessUploader):
    """Upload PGN text to Lichess via the public import API endpoint.

    Sends a ``POST`` request to the Lichess import endpoint and extracts the
    resulting game URL from the response. The URL extraction strategy tries three
    fallback sources in order: the JSON body, the ``Location`` header, and finally
    the final redirected URL.
    """

    def __init__(self, api_url: str = "https://lichess.org/api/import") -> None:
        """Initialise the uploader, optionally overriding the Lichess API endpoint.

        Args:
            api_url: Full URL of the Lichess PGN import endpoint. Defaults to the
                     public production endpoint.
        """
        self.api_url = api_url

    def upload(self, pgn_text: str) -> str:
        """POST ``pgn_text`` to the Lichess import endpoint and return the analysis URL.

        The URL is resolved using the following priority order:
        1. The ``"url"`` key in the JSON response body.
        2. The ``Location`` response header.
        3. The final redirected URL from the HTTP response.

        Raises:
            urllib.error.URLError: if the HTTP request fails.
        """
        # Encode the PGN as an application/x-www-form-urlencoded payload.
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
                # Prefer the URL field from the JSON body when present.
                if isinstance(data, dict) and isinstance(data.get("url"), str):
                    return data["url"]
            # Fall back to the Location header if the body didn't contain a URL.
            if location:
                return location
            # Last resort: the URL the HTTP client was redirected to.
            return response.geturl()
