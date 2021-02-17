"""The ssh user activities context model classes"""


from typing import (
    List,
    Optional,
)

from faker import Faker
from pwnlib.tubes.process import process
from pydantic import (
    BaseModel,
    Field,
)

from ..core.config import IdleConfig
from .config import (
    Command,
    Host,
)


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


class Context(BaseModel):
    """SSH user state machine context class"""

    fake: Faker
    """Faker instance to use for generating various random content"""

    ssh_user: SSHUserContext = Field(
        SSHUserContext(),
        description="The owncloud user context",
    )

    class Config:
        arbitrary_types_allowed = True
