from typing import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MenuButton:
    text: str
    child_id: str | None = None
    func: Callable | None = None


@dataclass(frozen=True)
class MenuMessage:
    id: str
    title: str
    buttons: list[list[MenuButton]] = field(default_factory=list)
    attach: list[tuple[str, str]] | None = None  # [(type, url), ...]
    need_args: list[str] = field(default_factory=list)


MenuRegistry = dict[str, MenuMessage]
