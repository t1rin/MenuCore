from aiogram import Router, F
from aiogram.types import CallbackQuery

from .callbacks import menu_cb


router = Router()


@router.callback_query(F.data.startswith("__mc:"))
async def handler(callback: CallbackQuery) -> None:
    data = menu_cb.unpack(callback.data or "")

    ...
