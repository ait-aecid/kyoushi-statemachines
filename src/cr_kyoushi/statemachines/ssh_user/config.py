import re

from typing import (
    Dict,
    List,
    Optional,
    Pattern,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    validator,
)

from ..core.config import Idle
from ..core.util import check_probabilities


RECEIVE_PATTERN = re.compile(r".*@.*:.*\$\s+")


class CommandBase(BaseModel):
    """Shell command configuration model"""

    cmd: str = Field(
        ...,
        description="The command string to execute. Can also be a signal in hex form e.g. '\\x03'",
    )

    chdir: Optional[str] = Field(
        None,
        description="The directory to change into before executing the command",
    )

    sudo: bool = Field(
        False,
        description=(
            "Flag configuring if the comman is executed with sudo or not. "
            "Note that this does not affect the optional directory change."
        ),
    )

    sudo_user: Optional[str] = Field(
        None,
        description="The user to become with sudo",
    )

    idle_after: Optional[Idle] = Field(
        Idle.TINY,
        description="The concrete or approximate time to to idle after executing the command.",
    )


class CommandConfig(CommandBase):
    """Command configuration class"""

    expect: Pattern = Field(
        RECEIVE_PATTERN,
        descrition="The regex pattern to wait for after executing the command.",
    )


class Command(CommandBase):
    """Command class

    !!! Note
        It is necessary to set expect as `str` as the Pydantic JSON encoder
        cannot handle `Pattern` fields as of v1.7.3. The code exists already on
        the master branch and should be part of the next release.
    """

    expect: str = Field(
        RECEIVE_PATTERN.pattern,
        descrition="The regex pattern to wait for after executing the command.",
    )


CommandChain = Union[str, List[Union[str, CommandConfig]]]


class HostConfigBase(BaseModel):
    """Host configuration base model"""

    host: str = Field(
        ...,
        description="The hostname or IP to connect to",
    )

    port: int = Field(
        22,
        description="The SSH port to connect to",
    )

    username: Optional[str] = Field(
        None,
        description="The username to use on this host",
    )

    password: Optional[str] = Field(
        None,
        description="The user password to use for this host",
    )

    ssh_key: Optional[FilePath] = Field(
        None,
        description="The path to the SSH key file to use to connect to the host",
    )

    force_password: bool = Field(
        False,
        description="If password authentication should be forced. (Useful for hosts with many SSH Keys)",
    )

    proxy_host: Optional[str] = Field(
        None,
        description="The host or IP of the SSH proxy server",
    )

    proxy_port: int = Field(
        22,
        description="The SSH port for the proxy server",
    )

    proxy_username: Optional[str] = Field(
        None,
        description="The user to use to connect to the proxy server.",
    )

    proxy_ssh_key: Optional[FilePath] = Field(
        None,
        description="The ssh key to use for the proxy server.",
    )

    proxy_verify_host: bool = Field(
        True,
        description="If the SSH host key should be verified or not",
    )


class HostConfig(HostConfigBase):
    """Host configuration model"""

    commands: List[CommandChain] = Field(
        [],
        description="List of command chains the user can execute on the host",
    )

    include_default_commands: bool = Field(
        False,
        description=(
            "If the shared command list should also be used "
            "when the host has specific commands set."
        ),
    )

    use_default_proxy: bool = Field(
        True,
        description=(
            "If the default proxy server should be used when present. "
            "Only relevant when the host does not have its own proxy server configured."
        ),
    )

    use_default_key: bool = Field(
        True,
        description=(
            "If the default ssh key should be used when "
            "present and no host ssh key is configured."
        ),
    )

    verify_host: Optional[bool] = Field(
        None,
        description=(
            "If the user should verify the SSH servers host key "
            "(if not set global config value is used)"
        ),
    )


class Host(HostConfigBase):
    """Host model

    i.e., after applying all default configuration values
    """

    username: str = Field(
        ...,
        description="The username to use on this host",
    )

    password: str = Field(
        ...,
        description="The user password to use for this host",
    )

    verify_host: bool = Field(
        True,
        description="If the user should verify the SSH servers host key ",
    )

    commands: List[List[Command]] = Field(
        [],
        description="List of command chains the user can execute on the host",
    )


class SSHUserConfig(BaseModel):
    """SSH User config model"""

    username: Optional[str] = Field(
        None,
        description="The default username to use.",
    )

    password: Optional[str] = Field(
        None,
        description="The default user password to use.",
    )

    ssh_key: Optional[FilePath] = Field(
        None,
        description="The path to the default SSH key file.",
    )

    verify_host: bool = Field(
        True,
        description="If the user should verify the SSH servers host key",
    )

    proxy_host: Optional[str] = Field(
        None,
        description="The host or IP of the default SSH proxy server",
    )

    proxy_port: int = Field(
        22,
        description="The SSH port for the default proxy server",
    )

    proxy_username: Optional[str] = Field(
        None,
        description="The default user to use to connect to the proxy server.",
    )

    proxy_ssh_key: Optional[FilePath] = Field(
        None,
        description="The default ssh key to use for the proxy server.",
    )

    proxy_verify_host: bool = Field(
        True,
        description="If the SSH host key should be verified or not",
    )

    commands: List[CommandChain] = Field(
        [],
        description="Default list of command chains the user can execute on the hosts.",
    )

    hosts: Dict[str, float] = Field(
        ...,
        description="Mapping of host identifiers to the propabilities of them being selected.",
    )

    host_configs: Dict[str, HostConfig] = Field(
        ...,
        description="Mapping of host identifiers to their configurations.",
    )

    _validate_probabilities = validator("hosts", allow_reuse=True)(check_probabilities)

    @validator("host_configs")
    def check_host_has_config(
        cls,
        v: Dict[str, HostConfig],
        values,
        **kwargs,
    ) -> Dict[str, HostConfig]:
        if "hosts" in values:
            for host in values["hosts"].keys():
                assert (
                    host in v
                ), f"Everyhost must have a config, but no config found for {host}!"
        return v

    @validator("host_configs")
    def check_host_has_username(
        cls,
        v: Dict[str, HostConfig],
        values,
        **kwargs,
    ) -> Dict[str, HostConfig]:
        for host, cfg in v.items():
            assert (
                cfg.username is not None or values.get("username", None) is not None
            ), f"Everyhost must have a username, but {host} has none!"
        return v

    @validator("host_configs")
    def check_host_has_password(
        cls,
        v: Dict[str, HostConfig],
        values,
        **kwargs,
    ) -> Dict[str, HostConfig]:
        for host, cfg in v.items():
            assert (
                cfg.password is not None or values.get("password", None) is not None
            ), f"Everyhost must have a password configured, but {host} has none!"
        return v

    @validator("host_configs")
    def check_host_proxy_cfg(
        cls,
        v: Dict[str, HostConfig],
        values,
        **kwargs,
    ) -> Dict[str, HostConfig]:
        for host, cfg in v.items():
            if (
                # only check if host has local proxy config
                cfg.proxy_host is not None
                # or is configured to use the global proxy config
                or (
                    values.get("proxy_host", None) is not None and cfg.use_default_proxy
                )
            ):
                assert (
                    # must have local proxy user
                    cfg.proxy_username is not None
                    # or global proxy user
                    or (
                        cfg.use_default_proxy
                        and values.get("proxy_username", None) is not None
                    )
                ), f"Proxy server requires proxy username, but {host} has no proxy username!"
                assert (
                    # must have local proxy ssh key
                    cfg.proxy_ssh_key is not None
                    # or global proxy ssh key
                    or (
                        cfg.use_default_proxy
                        and values.get("proxy_ssh_key", None) is not None
                    )
                ), f"Proxy server requires proxy ssh key, but {host} has no proxy ssh key!"
        return v


def convert_command(c: CommandConfig) -> Command:
    """Utility function to convert command config to command"""

    info = c.dict()
    info.update({"expect": c.expect.pattern})
    return Command(**info)


def convert_chain(chain: CommandChain) -> List[Command]:
    """Converts a command chain int a list of commands.

    i.e., simple str commands are converted to Command objects.
    """
    if isinstance(chain, str):
        return [Command(cmd=chain)]
    return [
        convert_command(c) if isinstance(c, CommandConfig) else Command(cmd=c)
        for c in chain
    ]


def get_hosts(config: SSHUserConfig) -> Dict[str, Host]:
    """Converts an SSHUserConfig into a dictionary of hosts.

    Each host has concrete values and all default config values are applied.

    Args:
        config: The ssh user config instance

    Returns:
        Concrete hosts dictionary.
    """
    default_commands = [convert_chain(chain) for chain in config.commands]
    hosts = {}
    for name, host_cfg in config.host_configs.items():
        assert config.username is not None or host_cfg.username is not None
        assert config.password is not None or host_cfg.password is not None

        if host_cfg.verify_host is None:
            verify_host = config.verify_host
        else:
            verify_host = host_cfg.verify_host

        # create host config from host entry
        host = Host(
            host=host_cfg.host,
            port=host_cfg.port,
            username=host_cfg.username or config.username,
            password=host_cfg.password or config.password,
            commands=[convert_chain(chain) for chain in host_cfg.commands],
            ssh_key=host_cfg.ssh_key,
            force_password=host_cfg.force_password,
            verify_host=verify_host,
            proxy_host=host_cfg.proxy_host,
            proxy_port=host_cfg.proxy_port,
            proxy_username=host_cfg.proxy_username,
            proxy_ssh_key=host_cfg.proxy_ssh_key,
            proxy_verify_host=host_cfg.proxy_verify_host,
        )

        # apply default values where appropriate
        if host_cfg.include_default_commands:
            host.commands.extend(default_commands)

        if host_cfg.use_default_key and host.ssh_key is None:
            host.ssh_key = config.ssh_key

        if host_cfg.use_default_proxy:
            # configure proxy settings which do not have a value yet
            host.proxy_host = host.proxy_host or config.proxy_host
            host.proxy_port = host.proxy_port or config.proxy_port
            host.proxy_username = host.proxy_username or config.proxy_username
            host.proxy_ssh_key = host.proxy_ssh_key or config.proxy_ssh_key

        hosts[name] = host

    return hosts
