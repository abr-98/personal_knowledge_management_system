from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any


def serialize_for_mcp(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return serialize_for_mcp(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): serialize_for_mcp(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_for_mcp(item) for item in value]
    if isinstance(value, tuple):
        return [serialize_for_mcp(item) for item in value]
    return value