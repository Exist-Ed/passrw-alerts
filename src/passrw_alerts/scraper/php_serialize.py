"""Minimal decoder for PHP `serialize()` output.

pass.rw.by embeds each train's data as a PHP-serialized array in a hidden form field.
PHP string lengths are counted in bytes, so decoding works on UTF-8 bytes, not str.
"""

from typing import Any


class PhpUnserializeError(ValueError):
    pass


def loads(data: str | bytes) -> Any:
    raw = data.encode() if isinstance(data, str) else data
    value, end = _decode(raw, 0)
    if end != len(raw):
        raise PhpUnserializeError(f"trailing data at byte {end}")
    return value


def _decode(raw: bytes, pos: int) -> tuple[Any, int]:
    kind = raw[pos : pos + 1]
    try:
        match kind:
            case b"N":
                return None, pos + 2
            case b"b" | b"i" | b"d":
                end = raw.index(b";", pos)
                token = raw[pos + 2 : end].decode()
                value = {b"b": lambda t: t == "1", b"i": int, b"d": float}[kind](token)
                return value, end + 1
            case b"s":
                colon = raw.index(b":", pos + 2)
                length = int(raw[pos + 2 : colon])
                start = colon + 2
                return raw[start : start + length].decode(), start + length + 2
            case b"a":
                colon = raw.index(b":", pos + 2)
                count = int(raw[pos + 2 : colon])
                pos = colon + 2
                result: dict[Any, Any] = {}
                for _ in range(count):
                    key, pos = _decode(raw, pos)
                    result[key], pos = _decode(raw, pos)
                return result, pos + 1
    except (ValueError, IndexError) as error:
        raise PhpUnserializeError(f"malformed value at byte {pos}") from error
    raise PhpUnserializeError(f"unsupported type {kind!r} at byte {pos}")


def as_list(value: dict[int, Any] | None) -> list[Any]:
    """PHP lists arrive as {0: ..., 1: ...}; return values in key order."""
    return [value[key] for key in sorted(value)] if value else []
