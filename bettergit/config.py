from dataclasses import dataclass

CONFIG_DEFAULTS = {
    "debug": False,
    "git_binary": "/usr/bin/git",
    "icon_status_other": "\u203C\uFE0F",  # Red double exclamation mark
    "icon_status_dirty": "\U0001F534",  # Red circle
    "icon_status_push_or_pull": "\U0001F7E1",  # Yellow circle
    "icon_status_clean": "\U0001F7E2",  # Green circle
    "icon_push_count": "\N{UPWARDS BLACK ARROW}",
    "icon_pull_count": "\N{DOWNWARDS BLACK ARROW}",
    "icon_modified_count": "\N{LOWER RIGHT PENCIL}",
    "icon_untracked_count": "\N{WARNING SIGN}",
    "icon_deleted_count": "\N{MINUS SIGN}",
    "icon_staged_count": "\N{CHECK MARK}",
    "icon_stashes_count": "\N{UP ARROWHEAD IN A RECTANGLE BOX}",
}


RUNNING_CONFIG = {}


def get_config_default(item: str):
    return CONFIG_DEFAULTS[item]


def get_config(item: str):
    return RUNNING_CONFIG.get(item, CONFIG_DEFAULTS[item])


def set_config(item: str, value):
    RUNNING_CONFIG[item] = value


@dataclass
class StringKnobConfig:
    key: str
    name: str
    placeholder: str = None


STRING_KNOB_CONFIGS: list[StringKnobConfig] = [
    StringKnobConfig("git_binary", "Git binary", get_config_default("git_binary")),
    StringKnobConfig("icon_status_other", "Icon: Status other"),
    StringKnobConfig("icon_status_dirty", "Icon: Status dirty"),
    StringKnobConfig("icon_status_push_or_pull", "Icon: Status push or pull"),
    StringKnobConfig("icon_status_clean", "Icon: Status clean"),
    StringKnobConfig("icon_push_count", "Icon: Push count"),
    StringKnobConfig("icon_pull_count", "Icon: Pull count"),
    StringKnobConfig("icon_modified_count", "Icon: Modified count"),
    StringKnobConfig("icon_untracked_count", "Icon: Untracked count"),
    StringKnobConfig("icon_deleted_count", "Icon: Deleted count"),
    StringKnobConfig("icon_staged_count", "Icon: Staged count"),
    StringKnobConfig("icon_stashes_count", "Icon: Stashes count"),
]
