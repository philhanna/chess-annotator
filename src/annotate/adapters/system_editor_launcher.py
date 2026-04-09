import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from annotate.ports.editor_launcher import EditorLauncher


class SystemEditorLauncher(EditorLauncher):
    """Launch the system ``$EDITOR`` to edit text interactively.

    Writes the initial text to a temporary ``.md`` file, launches the editor
    process, waits for it to exit, then reads and returns the saved content.
    The temporary file is deleted after reading regardless of whether the
    editor exits cleanly.

    Falls back to ``vi`` when ``$EDITOR`` is not set.
    """

    def edit(self, initial_text: str) -> str:
        """Open ``initial_text`` in ``$EDITOR`` and return whatever the user saved.

        Args:
            initial_text: The text to pre-populate in the editor.

        Returns:
            The full content of the temporary file after the editor closes.
        """
        # Read the editor command from the environment, defaulting to vi.
        editor = os.environ.get("EDITOR", "vi")
        # Shell-split to support editors specified with arguments, e.g. "code --wait".
        editor_cmd = shlex.split(editor)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as tmp:
            tmp.write(initial_text)
            tmp_path = tmp.name
        try:
            # Block until the editor process terminates.
            subprocess.run(editor_cmd + [tmp_path])
            return Path(tmp_path).read_text()
        finally:
            # Always clean up the temporary file, even if the editor crashed.
            Path(tmp_path).unlink(missing_ok=True)
