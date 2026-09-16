from typing import Any

from aiogram import Router, F
from aiogram.types import CallbackQuery


class CallbackData:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def pack(self, **kv: Any) -> str:
        parts = [self.prefix]
        for k, v in kv.items():
            parts.append(f"{k}={v}")
        data = ":".join(parts)
        if len(data.encode()) > 64:
            raise ValueError(f"callback_data too long: {repr(data)}")
        return data

    def unpack(self, data: str) -> dict[str, str] | None:
        prefix, _, rest = data.partition(":")
        if prefix != self.prefix:
            return None
        kv: dict[str, str] = {}
        if rest:
            for chunk in rest.split(":"):
                k, _, v = chunk.partition("=")
                kv[k] = v
        return kv


menu_cb = CallbackData("__mc")
router = Router()


@router.callback_query(F.data.startswith("__mc:"))
async def handler(callback: CallbackQuery) -> None:
    data = menu_cb.unpack(callback.data or "")

    ...
