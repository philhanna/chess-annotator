from abc import ABC, abstractmethod


class EditorLauncher(ABC):
    """Describe a service that delegates text editing to an external editor.

    This port exists so use cases can request an interactive editing
    step without knowing whether the application will launch ``$EDITOR``,
    open a GUI editor, or use some other editing mechanism. The returned
    string represents the text as saved by the user.
    """

    @abstractmethod
    def edit(self, initial_text: str) -> str:
        """Open the text in an external editor and return the saved result."""
        ...
