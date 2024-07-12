from typing import TYPE_CHECKING, Optional

from iterm2 import App, Connection

if TYPE_CHECKING:
    from .git_poller import GitPoller

APP_ID = "net.padz.iterm2.python_bettergit"
TRIGGER_VAR = "user.python_bettergit_trigger"
CWD_VAR = "user.python_bettergit_cwd"

connection: Optional[Connection] = None
app: Optional[App] = None
pollers: dict[str, "GitPoller"] = {}
cwds: dict[str, str] = {}


def set_connection(new_connection: Connection) -> None:
    # pylint: disable=global-statement
    global connection
    connection = new_connection


def set_app(new_app: App) -> None:
    # pylint: disable=global-statement
    global app
    app = new_app
