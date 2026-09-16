from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters.callback_data import CallbackData


router = Router()


@router.callback_query(F.data.startswith("__mc:"))
async def handler(callback: CallbackQuery) -> None:
    ...
