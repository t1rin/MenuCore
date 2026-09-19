import logging
from typing import Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import (InputMediaDocument, InputMediaPhoto,
                           InputMediaVideo, InputMediaAudio,
                           InputMedia, FSInputFile)

from .models import MenuButton
from .errors import InvalidTypeAttach
from .callbacks import menu_cb


logger = logging.getLogger(__name__)


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

    TYPES = {
        "document": InputMediaDocument,
        "photo": InputMediaPhoto,
        "video": InputMediaVideo,
        "audio": InputMediaAudio,
    }

    return [
        TYPES[_type](media=FSInputFile(url), caption=caption)
        for _type, media_items in attach.items()
        for caption, url in media_items
    ]


def __format(text: str, **data: Any) -> str:
    try:
        return text.format(**data)
    except KeyError:
        return text


def __build_keyboard_markup(matrix_btns: list[list[MenuButton]],
                            ) -> InlineKeyboardMarkup:
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    for line_btns in matrix_btns:
        line_keyboard: list[InlineKeyboardButton] = []
        for button in line_btns:
            __id = button.child_id
            if isinstance(button.func, str):
                __func_id = button.func
            else:
                __func_id = None
            data = menu_cb.pack(__id=__id, __func_id=__func_id)
            keyboard_button = InlineKeyboardButton(
                text=button.text, callback_data=data)
            line_keyboard.append(keyboard_button)
        inline_keyboard.append(line_keyboard)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def call(event: CallbackQuery | Message,
               *, title: str | None = None,
               buttons: list[list[MenuButton]] | None = None, 
               attach: dict[str, list[tuple[str, str]]] | None = None,
               **data: Any) -> None:
    """Показывает сообщение с переданными параметрами:
    :code:`title` - текст сообщения
    :code:`buttons` - матрица объектов MenuButton
    :code:`attach` - прикрепления (фото, видео, документы и тд)
    :code:`**data` - параметры форматирования title;
    контекст для обработки нажатия"""

    message = event.message if isinstance(event, CallbackQuery) else event

    text = __format(title, **data) if title else ". . ."
    media = __build_media(attach) if attach else None
    keyboard = __build_keyboard_markup(buttons) if buttons else None

    edited = False
    if isinstance(message, Message):
        try:
            if not media:
                await message.edit_text(text, reply_markup=keyboard)
                edited = True
            elif len(media) == 1:
                await message.edit_media(media=media[0], reply_markup=keyboard)
                edited = True
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                edited = True
            else:
                logger.debug(f"Could not edit message: {e}")

    if not edited:
        target = message if isinstance(message, Message) else (
            event if isinstance(event, Message) else None)
        if target is not None:
            target.delete()
            if media:
                await target.answer_media_group(media=media)
                if keyboard is not None:
                    await target.answer("⬆️", reply_markup=keyboard)
            else:
                await target.answer(text, reply_markup=keyboard)

    if isinstance(event, CallbackQuery):
        await event.answer()