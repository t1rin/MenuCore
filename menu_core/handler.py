from typing import Any

from aiogram import Router, F
from aiogram.types import CallbackQuery
from pydantic import ValidationError

from .callbacks import menu_cb
from .models import MenuRegistry, MenuMessage, MenuButton
from .errors import RegisterError


router = Router()
__menu_data: MenuRegistry | None = None


def register_menus(source_menus: list[dict[str, Any]]) -> None:
    global __menu_data
    if __menu_data is not None:
        raise RegisterError("Cannot register menus: menu data is already initialized.")

    menu_registry: MenuRegistry = {}

    for i, source_menu in enumerate(source_menus):
        try:
            menu = MenuMessage.model_validate(source_menu)
        except ValidationError as e:
            raise RegisterError(f"source_menus[{i}]: invalid menu data\n{e}") from e

        if menu.id in menu_registry:
            raise RegisterError(f"Duplicate menu id: {repr(menu.id)}")

        menu_registry[menu.id] = menu

    __menu_data = menu_registry


@router.callback_query(F.data.startswith("__mc:"))
async def handler(callback: CallbackQuery) -> None:
    data = menu_cb.unpack(callback.data or "")

    ...
