import logging
from typing import Any
from secrets import token_urlsafe

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import (InputMediaDocument, InputMediaPhoto,
                           InputMediaVideo, InputMediaAudio,
                           InputMedia, FSInputFile)

from .models import MenuButton
from .errors import InvalidTypeAttach, MenuCoreError
from .callbacks import menu_cb


__TYPES_ATTACH: dict[str, type] = {
    "document": InputMediaDocument,
    "photo": InputMediaPhoto,
    "video": InputMediaVideo,
    "audio": InputMediaAudio,
}

__SEND_METHOD_BY_CLASS: dict[type, str] = {
    InputMediaDocument: "answer_document",
    InputMediaPhoto: "answer_photo",
    InputMediaVideo: "answer_video",
    InputMediaAudio: "answer_audio",
}

__logger = logging.getLogger(__name__)
context_cache: dict[str, dict[str, Any]] = {}
message_tokens: dict[tuple[int, int], set[str]] = {}


def get_token(length: int) -> str:
    return token_urlsafe(length)[:length]


def __invalidate_message(chat_id: int, message_id: int) -> None:
    key = (chat_id, message_id)
    old_tokens = message_tokens.pop(key, None)
    if not old_tokens:
        return
    for token in old_tokens:
        context_cache.pop(token, None)


def __register_message(chat_id: int, message_id: int, tokens: set[str]) -> None:
    if tokens:
        message_tokens[(chat_id, message_id)] = tokens


def __is_valid_types_attach(types_attach: list[str]) -> bool:
    _type: Any = None
    for type_attach in types_attach:
        if type_attach not in ["document", "photo", "video", "audio"]:
            return False
        if _type is None:
            _type = type_attach
            continue
        if _type == type_attach:
            continue
        permissions = [("photo", "video"), ("video", "photo")]
        if (_type, type_attach) not in permissions:
            return False
    return True


def __build_media(attach: dict[str, list[tuple[str, str]]]) -> list[Any]:
    if not __is_valid_types_attach(list(attach.keys())):
        raise InvalidTypeAttach("Attachment type is not valid")

    return [
        __TYPES_ATTACH[_type](media=FSInputFile(url), caption=caption)
        for _type, media_items in attach.items()
        for caption, url in media_items
    ]


def __build_keyboard(matrix_btns: list[list[MenuButton]],
                     current_menu_id: str | None = None,
                     **context: Any) -> tuple[InlineKeyboardMarkup, set]:
    new_tokens: set[str] = set()
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    for line_btns in matrix_btns:
        line_keyboard: list[InlineKeyboardButton] = []
        for button in line_btns:
            __id = button.child_id
            if isinstance(button.func, str):
                __func_id = button.func
            else:
                __func_id = None
            context_id = get_token(length=10)
            context_cache[context_id] = {
                "__id": __id, "__crnt_id": current_menu_id,
                "__func_id": __func_id, **context}
            new_tokens.add(context_id)
            data = menu_cb.pack(context_id=context_id)
            keyboard_button = InlineKeyboardButton(
                text=button.text, callback_data=data)
            line_keyboard.append(keyboard_button)
        inline_keyboard.append(line_keyboard)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard), new_tokens


async def __prepare_content(
    title: str | None,
    buttons: list[list[MenuButton]] | None,
    attach: dict[str, list[tuple[str, str]]] | None,
    need_args: list[str] | None,
    current_menu_id: str | None,
    data: dict[str, Any],
) -> tuple[str, list[Any] | None, InlineKeyboardMarkup | None, set[str]]:
    if need_args:
        for arg in need_args:
            if arg not in data.keys():
                raise MenuCoreError(f"Missing required argument: '{arg}'")

    text = __format(title, **data) if title else ". . ."
    media = __build_media(attach) if attach else None

    keyboard: InlineKeyboardMarkup | None = None
    new_tokens: set[str] = set()
    if buttons is not None:
        keyboard, new_tokens = __build_keyboard(buttons, current_menu_id, **data)

    return text, media, keyboard, new_tokens


async def __try_edit_message(own_message: Message, text: str, media: list[Any] | None,
                             keyboard: InlineKeyboardMarkup | None) -> bool:
    try:
        if not media:
            await own_message.edit_text(text, reply_markup=keyboard)
            return True
        elif len(media) == 1:
            await own_message.edit_media(media=media[0], reply_markup=keyboard)
            return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return True
        else:
            __logger.debug(f"Could not edit message: {e}")
    return False


async def __send_new_message(target: Message, own_message: Message | None,
                             text: str, media: list[Any] | None,
                             keyboard: InlineKeyboardMarkup | None,
                             ) -> Message | None:
    if own_message is not None:
        await target.delete()

    if media and len(media) > 1:
        await target.answer_media_group(media=media)
        if keyboard is not None:
            return await target.answer(text, reply_markup=keyboard)
        return None
    elif media:
        method = getattr(target, __SEND_METHOD_BY_CLASS[type(media[0])])
        return await method(
            media[0].media, caption=media[0].caption, reply_markup=keyboard)
    else:
        return await target.answer(text, reply_markup=keyboard)


def __format(text: str, **data: Any) -> str:
    try:
        return text.format(**data)
    except KeyError:
        return text


async def call(event: CallbackQuery | Message,
               *, title: str | None = None,
               buttons: list[list[MenuButton]] | None = None, 
               attach: dict[str, list[tuple[str, str]]] | None = None,
               need_args: list[str] | None = None,
               current_menu_id: str | None = None,
               **data: Any) -> None:
    """Показывает сообщение с переданными параметрами:
    :code:`title` - текст сообщения
    :code:`buttons` - матрица объектов MenuButton
    :code:`attach` - прикрепления (фото, видео, документы и тд)
    :code:`need_args` - указание обязательные параметров для data
    :code:`current_menu_id` - id показываемого меню
    :code:`**data` - параметры форматирования title;
    контекст для обработки нажатия"""
    
    message = event.message if isinstance(event, CallbackQuery) else event
    
    if need_args:
        for arg in need_args:
            if arg not in data.keys():
                raise MenuCoreError(f"Missing required argument: '{arg}'")

    text, media, keyboard, new_tokens = await __prepare_content(
        title, buttons, attach, need_args, current_menu_id, data)
        
    own_message: Message | None = None
    if isinstance(message, Message):
        bot = message.bot
        if (
            bot is not None and
            message.from_user is not None
            and message.from_user.id == bot.id
        ):
            own_message = message

    if own_message is not None:
        __invalidate_message(own_message.chat.id, own_message.message_id)

    edited = False
    if own_message is not None:
        edited = await __try_edit_message(own_message, text, media, keyboard)

    final_message: Message | None = own_message if edited else None

    if not edited:
        target = own_message if own_message is not None else (
            event if isinstance(event, Message) else None)
        if target is not None:
            final_message = await __send_new_message(
                target, own_message, text, media, keyboard)

    if final_message is not None and new_tokens:
        __register_message(final_message.chat.id, final_message.message_id, new_tokens)

    if isinstance(event, CallbackQuery):
        await event.answer()
