from abc import ABC, abstractmethod


class LichessUploader(ABC):
    """Port for uploading a PGN game to Lichess and retrieving the analysis URL.

    Implementations are responsible for HTTP transport and URL extraction.
    The returned string must be a fully-qualified Lichess game or analysis URL
    that the caller can open in a browser.
    """

    @abstractmethod
    def upload(self, pgn_text: str) -> str:
        """Upload ``pgn_text`` to Lichess and return the resulting analysis URL."""
        ...
