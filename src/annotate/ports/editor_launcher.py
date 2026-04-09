from abc import ABC, abstractmethod


class EditorLauncher(ABC):
    @abstractmethod
    def edit(self, initial_text: str) -> str:
        ...
