# annotate.cli.commands
from annotate.cli.commands.close import cmd_close
from annotate.cli.commands.comment import cmd_comment
from annotate.cli.commands.copy import cmd_copy
from annotate.cli.commands.delete import cmd_delete
from annotate.cli.commands.diagram import cmd_diagram
from annotate.cli.commands.help_ import cmd_help
from annotate.cli.commands.import_game import cmd_import
from annotate.cli.commands.json_ import cmd_json
from annotate.cli.commands.label import cmd_label
from annotate.cli.commands.list_ import cmd_list, cmd_list_segments
from annotate.cli.commands.open_ import cmd_open
from annotate.cli.commands.quit_ import cmd_quit
from annotate.cli.commands.render import cmd_render
from annotate.cli.commands.save import cmd_save
from annotate.cli.commands.see import cmd_see
from annotate.cli.commands.select import cmd_select
from annotate.cli.commands.split import cmd_split
from annotate.cli.commands.merge import cmd_merge
from annotate.cli.commands.view import cmd_view

__all__ = [
    "cmd_close",
    "cmd_comment",
    "cmd_copy",
    "cmd_delete",
    "cmd_diagram",
    "cmd_help",
    "cmd_import",
    "cmd_json",
    "cmd_label",
    "cmd_list",
    "cmd_list_segments",
    "cmd_merge",
    "cmd_open",
    "cmd_quit",
    "cmd_render",
    "cmd_save",
    "cmd_see",
    "cmd_select",
    "cmd_split",
    "cmd_view",
]
