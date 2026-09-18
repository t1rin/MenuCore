import logging
from typing import Any

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from pydantic import ValidationError

from .builder import call
from .callbacks import menu_cb
from .models import MenuRegistry, MenuMessage, MenuButton
from .errors import RegisterError, MenuCoreError


router = Router()
logger = logging.getLogger(__name__)
__menu_data: MenuRegistry | None = None


def register_menus(source_menus: list[dict[str, Any]]) -> None: # протестировать -> Router
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


async def start_message(target: Bot | Message | CallbackQuery,
                        chat_id: int | None = None,
                        *, menu_id: str, data: Any) -> None:
    if __menu_data is None:
        raise MenuCoreError("Menu data is not initialized. "
                            "Call 'register_menus()' before accessing menus.")
    if menu_id not in __menu_data:
        raise MenuCoreError(f"Menu with ID {repr(menu_id)} was not found. "
                            f"Available menu IDs: {list(__menu_data.keys())}")
    menu_data = __menu_data[menu_id]

    event = target
    if isinstance(target, Bot):
        if chat_id is None:
            raise MenuCoreError("`chat_id` cannot be None when target is Bot.")
        event = await target.send_message(chat_id=chat_id, text="...")
    if not isinstance(event, Bot):
        await call(
            event, 
            title=menu_data.title, 
            buttons=menu_data.buttons, 
            attach=menu_data.attach
            **data
        )


@router.callback_query(F.data.startswith("__mc:"))
async def handler(callback: CallbackQuery) -> None:
    data = menu_cb.unpack(callback.data or "")

    ...
