from typing import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MenuButton:
    text: str
    link: str | None = None
    func: Callable | None = None


@dataclass(frozen=True)
class MenuMsg:
    id: str
    title: str
    buttons: list[MenuButton] = field(default_factory=list)
    attach: list[tuple[str, str]] | None = None  # [(type, url), ...]
    args: list[str] = field(default_factory=list)


MenuRegistry = dict[str, MenuMsg]
