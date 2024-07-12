from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from iterm2 import App, Connection

if TYPE_CHECKING:
    from .git_poller import GitPoller

APP_ID = "net.padz.iterm2.python_bettergit"
TRIGGER_VAR = "user.python_bettergit_trigger"
CWD_VAR = "user.python_bettergit_cwd"


@dataclass
class _globals:
    connection: Optional[Connection] = None
    app: Optional[App] = None
    pollers: dict[str, "GitPoller"] = field(default_factory=dict)
    cwds: dict[str, str] = field(default_factory=dict)


app_globals = _globals()
