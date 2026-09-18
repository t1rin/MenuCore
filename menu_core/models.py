from typing import Callable, Any, Literal
from pydantic import BaseModel, ConfigDict


class MenuButton(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    text: str
    child_id: str | None = None
    func: Callable[..., Any] | None = None


class MenuMessage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    title: str
    buttons: list[list[MenuButton]] = []
    attach: dict[str, list[tuple[str, str]]] | None = None  # {type: [(caption, url), ...], ...}
    need_args: list[str] = []


MenuRegistry = dict[str, MenuMessage]
