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

from ..core.config import (
    BasicStatemachineConfig,
    Idle,
    ProbabilisticStateConfig,
)
from ..core.util import (
    check_probabilities,
    greater_equal_one,
)
from .expect import RECEIVE_PATTERN


class CommandConfig(BaseModel):
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

    expect: Optional[Pattern] = Field(
        None,
        descrition=(
            "The regex pattern to wait for after executing the command. "
            "This will default to the host prompt pattern."
        ),
    )


class Command(CommandConfig):
    """Command model class"""

    expect: Pattern = Field(
        RECEIVE_PATTERN,
        descrition="The regex pattern to wait for after executing the command.",
    )


CommandChain = Union[str, CommandConfig, List[Union[str, CommandConfig]]]


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

    max_sudo_tries: int = Field(
        3,
        description="The maximum allowed password tries for the sudo prompt",
    )

    ssh_key: Optional[FilePath] = Field(
        None,
        description="The path to the SSH key file to use to connect to the host",
    )

    force_password: bool = Field(
        False,
        description="If password authentication should be forced. (Useful for hosts with many SSH Keys)",
    )

    verify_host: Optional[bool] = Field(
        None,
        description=(
            "If the user should verify the SSH servers host key "
            "(if not set global config value is used)"
        ),
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

    shell_prompt_pattern: Pattern = Field(
        RECEIVE_PATTERN,
        description=(
            "The shell prompt pattern to expect for commands. "
            "Default is the bash prompt."
        ),
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
        {},
        description="Mapping of host identifiers to the propabilities of them being selected.",
    )

    host_configs: Dict[str, HostConfig] = Field(
        {},
        description="Mapping of host identifiers to their configurations.",
    )

    max_daily: int = Field(
        10,
        description=(
            "The maximum amount of times the ssh user "
            "activity will be entered per day"
        ),
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


def convert_command(c: CommandConfig, expect_pattern: Pattern) -> Command:
    """Utility function to convert command config to command"""

    info = c.dict()
    expect = c.expect or expect_pattern
    info.update({"expect": expect})
    return Command(**info)


def convert_chain(chain: CommandChain, host_cfg: HostConfig) -> List[Command]:
    """Converts a command chain int a list of commands.

    i.e., simple str commands are converted to Command objects.
    """
    prompt = host_cfg.shell_prompt_pattern

    if isinstance(chain, str):
        return [Command(cmd=chain, expect=prompt)]
    if isinstance(chain, CommandConfig):
        return [convert_command(chain, prompt)]
    return [
        convert_command(c, prompt)
        if isinstance(c, CommandConfig)
        else Command(cmd=c, expect=prompt)
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
    hosts = {}
    for name, host_cfg in config.host_configs.items():
        assert config.username is not None or host_cfg.username is not None
        assert config.password is not None or host_cfg.password is not None

        host_dict = host_cfg.dict()

        if host_cfg.verify_host is None:
            host_dict["verify_host"] = config.verify_host
        else:
            host_dict["verify_host"] = host_cfg.verify_host

        # convert config command chain to proper commands
        host_dict["commands"] = [
            convert_chain(chain, host_cfg) for chain in host_cfg.commands
        ]

        # apply default values where appropriate
        host_dict["username"] = host_cfg.username or config.username
        host_dict["password"] = host_cfg.password or config.password

        if host_cfg.include_default_commands:
            # need to convert default commands for each host
            # as the shell prompts might be different
            default_commands = [
                convert_chain(chain, host_cfg) for chain in config.commands
            ]
            host_dict["commands"].extend(default_commands)

        if host_cfg.use_default_key and host_dict["ssh_key"] is None:
            host_dict["ssh_key"] = config.ssh_key

        if host_cfg.use_default_proxy:
            # configure proxy settings which do not have a value yet
            host_dict["proxy_host"] = host_cfg.proxy_host or config.proxy_host
            host_dict["proxy_port"] = host_cfg.proxy_port or config.proxy_port
            host_dict["proxy_username"] = (
                host_cfg.proxy_username or config.proxy_username
            )
            host_dict["proxy_ssh_key"] = host_cfg.proxy_ssh_key or config.proxy_ssh_key

        # create host config from host entry
        host = Host(**host_dict)

        hosts[name] = host

    return hosts


class ActivitySelectionConfig(ProbabilisticStateConfig):
    """SSH user state machines selecting activity states configuration."""

    ssh_user: float = Field(
        0.6,
        description="The base propability that ssh_user will be selected.",
    )

    idle: float = Field(
        0.4,
        description="The base propability that idle will be selected.",
    )


class ConnectedExtraConfig(BaseModel):
    """Base class for extra configuration fields for the connected state config."""

    disconnect_increase: float = Field(
        3.0,
        description=(
            "The multiplicative factor the disconnect transitions weight "
            "should be increased each time it is not selected."
        ),
    )

    _validate_increase = validator("disconnect_increase", allow_reuse=True)(
        greater_equal_one
    )


class ConnectedConfig(ProbabilisticStateConfig):
    """The selecting menu states configuration"""

    select_chain: float = Field(
        0.9,
        description="The base propability that select_chain will be selected.",
    )

    disconnect: float = Field(
        0.1,
        description="The base propability that disconnect will be selected.",
    )

    extra: ConnectedExtraConfig = Field(
        ConnectedExtraConfig(),
        description="Extra configuration for the state",
    )


class SudoDialogExtraConfig(BaseModel):
    """Base class for extra configuration fields for the sudo dialog config."""

    fail_increase: float = Field(
        4.0,
        description=(
            "The multiplicative factor the fail transitions weight "
            "should be increased each time it is not selected."
        ),
    )

    _validate_increase = validator("fail_increase", allow_reuse=True)(greater_equal_one)


class SudoDialogConfig(ProbabilisticStateConfig):
    """The selecting menu states configuration"""

    enter_password: float = Field(
        0.95,
        description="The base propability that enter_password will be selected.",
    )

    fail: float = Field(
        0.05,
        description="The base propability that fail will be selected.",
    )

    extra: SudoDialogExtraConfig = Field(
        SudoDialogExtraConfig(),
        description="Extra configuration for the state",
    )


class SSHStates(BaseModel):
    """Configuration class for all SSH user activity states."""

    connected: ConnectedConfig = Field(
        ConnectedConfig(),
        description="The connected states config",
    )

    sudo_dialog: SudoDialogConfig = Field(
        SudoDialogConfig(),
        description="The sudo dialog states config",
    )


class SSHUserStates(SSHStates):
    """Configuration class for the ssh user state machine states"""

    selecting_activity: ActivitySelectionConfig = Field(
        ActivitySelectionConfig(),
        description="The selecting activity states config",
    )


class StatemachineConfig(BasicStatemachineConfig):
    """SSH user state machine configuration model

    Example:
        ```yaml
        max_errors: 0
        start_time: 2021-01-23T9:00
        end_time: 2021-01-29T00:01
        schedule:
        work_days:
            monday:
                start_time: 09:00
                end_time: 17:30
            friday:
                start_time: 11:21
                end_time: 19:43
        ```
    """

    ssh_user: SSHUserConfig = Field(
        SSHUserConfig(),
        description="The ssh user config",
    )

    states: SSHUserStates = Field(
        SSHUserStates(),
        description="The states configuration for the state machine",
    )
