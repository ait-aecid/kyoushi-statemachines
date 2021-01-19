"""
This module contains various utility functions.
"""

from typing import Dict
from typing import TypeVar


_FILTER_KEY = TypeVar("_FILTER_KEY")
_FILTER_VAL = TypeVar("_FILTER_VAL")


def filter_none_keys(
    container: Dict[_FILTER_KEY, _FILTER_VAL]
) -> Dict[_FILTER_KEY, _FILTER_VAL]:
    """Removes all keys pointing to `None` values from a `dict`

    Args:
        container: The dict to filter

    Returns:
        The original dict without its `None` values.
    """
    return {k: v for k, v in container.items() if v is not None}
