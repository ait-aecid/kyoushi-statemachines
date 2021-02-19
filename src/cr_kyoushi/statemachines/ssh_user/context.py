"""The ssh user activities context model classes"""

import sys

from typing import (
    List,
    Optional,
)

from pwnlib.tubes.process import process
from pydantic import (
    BaseModel,
    Field,
)

from ..core.config import (
    FakerContext,
    FakerContextModel,
    IdleConfig,
)
from .config import (
    Command,
    Host,
)


if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class SSHUserContext(BaseModel):
    shell: Optional[process]
    """The currently active remote shell"""

    host: Optional[Host] = Field(
        None,
        description="The host the ssh user is currently connected to",
    )

    output: List[str] = Field(
        [],
        description="The output of the current command",
    )

    commands: List[Command] = Field(
        [],
        description="The command chain the user is currently executing",
    )

    idle_config: IdleConfig = Field(
        IdleConfig(),
        description="Idle configuration for the ssh user",
    )

    class Config:
        arbitrary_types_allowed = True


class Context(FakerContext, Protocol):
    """SSH user state machine context protocol"""

    ssh_user: SSHUserContext
    """The owncloud user context"""


class ContextModel(FakerContextModel):
    """SSH user state machine context class"""

    ssh_user: SSHUserContext = Field(
        SSHUserContext(),
        description="The owncloud user context",
    )
