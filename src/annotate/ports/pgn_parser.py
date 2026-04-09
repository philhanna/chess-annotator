from abc import ABC, abstractmethod


class PGNParser(ABC):
    @abstractmethod
    def parse(self, pgn_text: str) -> dict:
        ...
