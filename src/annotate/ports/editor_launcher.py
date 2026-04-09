from abc import ABC, abstractmethod


class EditorLauncher(ABC):
    """Port for delegating text editing to an external editor.

    This abstraction lets use cases request an interactive editing step without
    coupling to a specific editor mechanism. The returned string is whatever text
    the user saved before closing the editor.
    """

    @abstractmethod
    def edit(self, initial_text: str) -> str:
        """Open ``initial_text`` in an external editor and return the saved result.

        The method blocks until the editor process exits. If the user saves
        without making changes, the original text is returned unchanged.
        """
        ...
