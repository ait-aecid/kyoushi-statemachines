"""The owncloud user activities context model classes"""

import sys

from typing import Optional

from pydantic import (
    BaseModel,
    Field,
)


if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class Context(Protocol):
    """AECID attacker context"""

    web_shell: Optional[str]
    """The url to the uploaded web shell"""


class ContextModel(BaseModel):
    """Beta user state machine context class"""

    web_shell: Optional[str] = Field(
        None,
        description="The url to the uploaded web shell",
    )
