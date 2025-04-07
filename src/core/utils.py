import logging
from typing import Any

log = logging.getLogger(__name__)

def safe_get_attr(obj: Any, attr_name: str, default: Any = None) -> Any:
    return getattr(obj, attr_name, default) if obj is not None else default

def safe_get_nested_attr(obj: Any, *attrs: str, default: Any = None) -> Any:
    for attr in attrs:
        if obj is None:
            return default
        if hasattr(obj, '__getattribute__'):
            obj = getattr(obj, attr, None)
        else:
            return default
    return obj if obj is not None else default
