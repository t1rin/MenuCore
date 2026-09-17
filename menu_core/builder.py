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


def __build_media(attach: dict[str, list[tuple[str, str]]]) -> list[InputMedia]:
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


def __build_keyboard_markup(matrix_btns: list[list[MenuButton]],
                            ) -> None: #InlineKeyboardMarkup:
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    for line_btns in matrix_btns:
        line_keyboard: list[InlineKeyboardButton] = []
        for button in line_btns:
            ...

    # InlineKeyboardmarkup(inline_keyboard=[
    #     [inlinekeyboardbutton(text=text, callback_data=...) 
    #     for text, callback_data in line] for line in table
    # ])


async def call(event: CallbackQuery | Message,
               id: int , **data: Any) -> None:
    """Показывает сообщение с id с параметрами data"""
    
    message = event.message if isinstance(event, CallbackQuery) else event

    edited = False
    if isinstance(message, Message):
        try:
            await message.edit_text("text", reply_markup=None)
            edited = True
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                edited = True
            else:
                logger.debug(f"Could not edit message: {e}")

    if not edited:
        target = message if isinstance(message, Message) else (
            event if isinstance(event, Message) else None
        )
        if target is not None:
            sent = await target.answer("text", reply_markup=None)

    if isinstance(event, CallbackQuery):
        await event.answer()
