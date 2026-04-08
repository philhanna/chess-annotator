from abc import ABC, abstractmethod


class LichessUploader(ABC):
    """Upload PGN text to Lichess and return the resulting analysis URL."""

    @abstractmethod
    def upload(self, pgn_text: str) -> str:
        """Upload PGN text and return the Lichess URL."""
        ...
