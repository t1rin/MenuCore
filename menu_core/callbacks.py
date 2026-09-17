from typing import Any


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

    def unpack(self, data: str) -> dict[str, Any] | None:
        prefix, _, rest = data.partition(":")
        if prefix != self.prefix:
            return None
        kv: dict[str, Any] = {}
        if rest:
            for chunk in rest.split(":"):
                k, _, v = chunk.partition("=")
                if v.isdigit():
                    kv[k] = int(v)
                elif v == "None":
                    kv[k] = None
                else:
                    kv[k] = v
        return kv


menu_cb = CallbackData("__mc")
