import logging
import inspect
from typing import Any, Callable

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from pydantic import ValidationError

from .callbacks import menu_cb
from .builder import call, context_cache, get_token
from .models import MenuRegistry, MenuMessage, MenuButton
from .errors import RegisterError, MenuCoreError


__router = Router()
__logger = logging.getLogger(__name__)
__menu_data: MenuRegistry | None = None


def setup_menus(source_menus: list[dict[str, Any]]) -> Router:
    """Подключает меню и возвращает роутер обработчика
    :code:`source_menus` - список для регистрации меню"""

    global __menu_data, __router
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

    for menu in menu_registry.values():
        for row in menu.buttons:
            for button in row:
                if button.child_id is not None and button.child_id not in menu_registry:
                    raise RegisterError(f"Menu {repr(menu.id)}: button {repr(button.text)} "
                                        f"references unknown child_id {repr(button.child_id)}")

    __menu_data = menu_registry

    return __router


async def start_menu(target: Bot | Message | CallbackQuery,
                     chat_id: int | None = None,
                     *, menu_id: str, **data: Any) -> None:
    """Показывает стартовое меню по переданным параметрам
    :code:`target` - для вызова через обработчик или напрямую через Bot
    :code:`chat_id` - id чата для отправки напрямую через Bot
    :code:`menu_id` - id начального меню
    :code:`**data` - контекст выполнения
    для запуском требуется сначала подключить данные"""

    if __menu_data is None:
        raise MenuCoreError("Menu data is not initialized. "
                            "Call 'start_menu()' before accessing menus.")
    if menu_id not in __menu_data:
        raise MenuCoreError(f"Menu with ID {repr(menu_id)} was not found. "
                            f"Available menu IDs: {list(__menu_data.keys())}")
    menu_data = __menu_data[menu_id]

    event = target
    if isinstance(target, Bot):
        if chat_id is None:
            raise MenuCoreError("`chat_id` cannot be None when target is Bot.")
        event = await target.send_message(chat_id=chat_id, text=". . .")
    if not isinstance(event, Bot):
        await call(
            event, 
            title=menu_data.title, 
            buttons=menu_data.buttons,
            attach=menu_data.attach,
            need_args=menu_data.need_args,
            current_menu_id=menu_id,
            **data,
        )


@__router.callback_query(F.data.startswith("__mc:"))
async def __handler(callback: CallbackQuery) -> None:
    callback_data = menu_cb.unpack(callback.data or "")
    context_id = callback_data.get("context_id") if callback_data else None
    data = context_cache.pop(context_id, None) if isinstance(context_id, str) else None
    if data is None:
        __logger.error("Failed to unpack callback data")
        return
    
    func = data.pop("__func", None)
    menu_id = data.pop('__id', None)
    current_menu_id = data.pop("__crnt_id", None)

    menu = None
    if __menu_data is not None:
        menu = (__menu_data.get(menu_id) if menu_id
                else __menu_data.get(current_menu_id))
    
    if func is not None:
        if inspect.iscoroutinefunction(func):
            await func(data)
        else:
            func(data)

    if menu is not None:
        await call(
            callback,
            title=menu.title,
            buttons=menu.buttons,
            attach=menu.attach,
            need_args=menu.need_args,
            current_menu_id=menu.id,
            **data,
        )
    else:
        await callback.answer()

    if __logger.isEnabledFor(logging.DEBUG):
        from .builder import message_tokens
        __logger.debug("current context: %r", context_cache)
        __logger.debug("current messages: %r", message_tokens)
