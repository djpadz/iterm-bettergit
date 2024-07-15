from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from iterm2 import App, Connection

if TYPE_CHECKING:
    from .git_poller import GitPoller

APP_ID = "net.padz.iterm2.python_bettergit"
CWD_VAR = "user.python_bettergit_cwd"


@dataclass
class _globals:
    connection: Optional[Connection] = None
    app: Optional[App] = None


app_globals = _globals()
