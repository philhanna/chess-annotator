from dataclasses import dataclass


@dataclass
class SegmentContent:
    label: str = ""
    annotation: str = ""
    show_diagram: bool = True

    @property
    def commentary(self) -> str:
        return self.annotation

    @commentary.setter
    def commentary(self, value: str) -> None:
        self.annotation = value

    def has_authored_content(self) -> bool:
        return bool(self.label.strip()) or bool(self.annotation.strip())


@dataclass(frozen=True)
class SegmentView:
    turning_point_ply: int
    start_ply: int
    end_ply: int
    content: SegmentContent

    @property
    def label(self) -> str:
        return self.content.label

    @property
    def annotation(self) -> str:
        return self.content.annotation

    @property
    def commentary(self) -> str:
        return self.content.annotation

    @property
    def show_diagram(self) -> bool:
        return self.content.show_diagram


@dataclass
class Segment:
    start_ply: int
    label: str = ""
    commentary: str = ""
    show_diagram: bool = True
