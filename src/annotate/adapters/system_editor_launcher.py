import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from annotate.ports.editor_launcher import EditorLauncher


class SystemEditorLauncher(EditorLauncher):
    def edit(self, initial_text: str) -> str:
        editor = os.environ.get("EDITOR", "vi")
        editor_cmd = shlex.split(editor)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as tmp:
            tmp.write(initial_text)
            tmp_path = tmp.name
        try:
            subprocess.run(editor_cmd + [tmp_path])
            return Path(tmp_path).read_text()
        finally:
            Path(tmp_path).unlink(missing_ok=True)
