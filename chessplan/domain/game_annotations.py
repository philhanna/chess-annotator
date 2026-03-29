from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .block import Block


@dataclass(slots=True)
class GameAnnotations:
    pgn_path: str
    event: str = ""
    white: str = ""
    black: str = ""
    result: str = ""
    summary: str = ""
    big_lessons: list[str] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "pgn_path": self.pgn_path,
            "event": self.event,
            "white": self.white,
            "black": self.black,
            "result": self.result,
            "summary": self.summary,
            "big_lessons": self.big_lessons,
            "blocks": [asdict(block) for block in self.blocks],
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "GameAnnotations":
        blocks = [Block(**item) for item in data.get("blocks", [])]
        return cls(
            pgn_path=data["pgn_path"],
            event=data.get("event", ""),
            white=data.get("white", ""),
            black=data.get("black", ""),
            result=data.get("result", ""),
            summary=data.get("summary", ""),
            big_lessons=list(data.get("big_lessons", [])),
            blocks=blocks,
        )
