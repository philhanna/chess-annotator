from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Block:
    """Describes a labeled review block covering a range of moves.

    Blocks capture the plan, trigger, outcome, and follow-up notes for a
    phase of the game so summaries can group strategic observations instead
    of isolated moves.
    """

    kind: str
    label: str
    start_move: int
    end_move: int
    side: str = "white"
    idea: str = ""
    trigger: str = ""
    end_condition: str = ""
    result: str = ""
    opponent_plan: str = ""
    better_plan: str = ""
    notes: str = ""

    def validate(self, max_move: int) -> list[str]:
        """Validate the block fields against domain rules.

        Parameters
        ----------
        max_move:
            The largest full-move number available in the reviewed game.

        Returns
        -------
        list[str]
            Human-readable validation messages. The list is empty when the
            block is valid.
        """

        errors: list[str] = []
        if not self.kind.strip():
            errors.append("kind must not be empty")
        if not self.label.strip():
            errors.append("label must not be empty")
        if self.side not in {"white", "black", "both", "none"}:
            errors.append("side must be one of: white, black, both, none")
        if self.start_move < 1:
            errors.append("start_move must be >= 1")
        if self.end_move < self.start_move:
            errors.append("end_move must be >= start_move")
        if self.end_move > max_move:
            errors.append(f"end_move must be <= {max_move}")
        return errors
