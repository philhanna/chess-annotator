from abc import ABC, abstractmethod


class LichessUploader(ABC):
    @abstractmethod
    def upload(self, pgn_text: str) -> str:
        ...
