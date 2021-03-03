"""The owncloud user activities context model classes"""

import sys

from subprocess import Popen
from typing import Optional

from pwnlib.tubes.listen import listen
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

    vpn_process: Optional[Popen]
    """The VPN process for remote users"""

    web_shell: Optional[str]
    """The url to the uploaded web shell"""

    reverse_shell: Optional[listen]
    """The reverse shell connection the attacker has created"""


class ContextModel(BaseModel):
    """Beta user state machine context class"""

    vpn_process: Optional[Popen]
    """The VPN process for remote users"""

    web_shell: Optional[str] = Field(
        None,
        description="The url to the uploaded web shell",
    )

    reverse_shell: Optional[listen]
    """The reverse shell connection the attacker has created"""

    class Config:
        arbitrary_types_allowed = True
