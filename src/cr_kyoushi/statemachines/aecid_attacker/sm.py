"""Statemachine that only idles or executes the ssh user activity."""


from datetime import (
    datetime,
    timedelta,
)
from typing import Union

from cr_kyoushi.simulation import sm
from cr_kyoushi.simulation.states import (
    FinalState,
    SequentialState,
)
from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    NoopTransition,
    Transition,
)
from cr_kyoushi.simulation.util import now

from ..beta_user.actions import VPNConnect
from ..beta_user.actions import vpn_disconnect as f_vpn_disconnect
from . import (
    actions,
    states,
)
from .config import StatemachineConfig
from .context import ContextModel


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(sm.StartEndTimeStatemachine):
    """AECID attacker state machine"""

    def setup_context(self):
        self.context = ContextModel()


def _to_datetime(v: Union[timedelta, datetime], base: datetime) -> datetime:
    if isinstance(v, timedelta):
        return base + v
    return v


class StatemachineFactory(sm.StatemachineFactory):
    """AECID attacker state machine factory"""

    @property
    def name(self) -> str:
        return "AECIDAttackerStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def build(self, config: StatemachineConfig):
        idle = config.idle
        # get start and escalate time
        start_time: datetime = _to_datetime(config.attack_start_time, now())
        escalate_time: datetime = _to_datetime(config.escalate_start_time, start_time)

        # build transitions
        f_vpn_connect = VPNConnect(config.vpn)
        vpn_connect = DelayedTransition(
            f_vpn_connect,
            name="vpn_connect",
            target="vpn_connected",
            delay_after=idle.small,
        )

        traceroute = DelayedTransition(
            actions.Traceroute(config.recon.trace_target),
            name="traceroute_internet",
            target="recon_networks",
            delay_after=idle.tiny,
        )

        recon_networks_finish = NoopTransition(
            "recon_networks_finish",
            target="recon_wordpress",
        )

        upload_rce_shell = DelayedTransition(
            actions.UploadWebShell(
                config.wordpress.url,
                config.wordpress.rce_image,
                admin_ajax=config.wordpress.admin_ajax,
            ),
            name="upload_rce_shell",
            target="recon_host",
        )

        recon_host_finish = NoopTransition(
            "recon_host_finish",
            target="wait_escalate_choice",
        )

        vpn_pause = Transition(
            f_vpn_disconnect,
            name="vpn_disconnect",
            target="cracking_passwords",
        )

        cracking = Transition(
            actions.WaitUntilNext(
                escalate_time,
                name="escalate phase",
            ),
            name="wait_until_escalate",
            target="cracked_passwords",
        )

        vpn_reconnect = DelayedTransition(
            f_vpn_connect,
            name="vpn_connect",
            target="vpn_reconnected",
            delay_after=idle.small,
        )

        listen_reverse_shell = DelayedTransition(
            actions.StartReverseShellListener(config.escalate.reverse_port),
            name="reverse_shell_listen",
            target="reverse_shell_listening",
            delay_after=idle.tiny,
        )

        open_reverse_shell = Transition(
            actions.OpenReverseShell(config.escalate.reverse_cmd),
            name="open_reverse_shell",
            target="opening_reverse_shell",
        )

        wait_reverse_shell = DelayedTransition(
            actions.WaitReverseShellConnection(),
            name="wait_reverse_shell",
            target="reverse_shell",
            delay_after=idle.small,
        )

        login_user = DelayedTransition(
            actions.ShellChangeUser(config.escalate.user, config.escalate.password),
            name="login_user",
            target="escalated",
            delay_after=idle.small,
        )

        vpn_disconnect = Transition(
            f_vpn_disconnect,
            name="vpn_disconnect",
            target="end",
        )

        # build states

        initial = SequentialState(
            "initial",
            transition=vpn_connect,
        )

        vpn_connected = states.VPNConnected(
            name="vpn_connected",
            transition=traceroute,
        )

        recon_networks = states.ReconNetworks(
            name="recon_networks",
            config=config.recon,
            idle=idle,
            next_phase=recon_networks_finish,
        )

        recon_wordpress = states.ReconWordpress(
            name="recon_wordpress",
            config=config.wordpress,
            idle=idle,
            next_phase=upload_rce_shell,
        )

        recon_host = states.ReconHost(
            name="recon_host",
            config=config.wordpress,
            idle=idle,
            next_phase=recon_host_finish,
        )

        wait_escalate_choice = states.WaitChoice(
            name="wait_escalate_choice",
            escalate_time=escalate_time,
            listen_reverse_shell=listen_reverse_shell,
            vpn_disconnect=vpn_pause,
        )

        cracking_passwords = states.CrackingPasswords(
            name="cracking_passwords",
            transition=cracking,
        )

        cracked_passwords = states.CrackedPasswords(
            name="cracked_passwords",
            transition=vpn_reconnect,
        )

        vpn_reconnected = states.VPNReconnected(
            name="vpn_reconnected",
            transition=listen_reverse_shell,
        )

        reverse_shell_listening = states.ListeningReverseShell(
            name="reverse_shell_listening",
            transition=open_reverse_shell,
        )

        opening_reverse_shell = states.OpeningReverseShell(
            name="opening_reverse_shell",
            transition=wait_reverse_shell,
        )

        reverse_shell = states.ReverseShell(
            name="reverse_shell",
            transition=login_user,
        )

        escalated = states.Escalated(
            name="escalated",
            config=config.escalate,
            idle=idle,
            next_phase=vpn_disconnect,
        )

        end = FinalState("end")

        return Statemachine(
            initial_state=initial.name,
            states=[
                initial,
                vpn_connected,
                recon_networks,
                recon_wordpress,
                recon_host,
                wait_escalate_choice,
                cracking_passwords,
                cracked_passwords,
                vpn_reconnected,
                reverse_shell_listening,
                opening_reverse_shell,
                reverse_shell,
                escalated,
                end,
            ],
            start_time=start_time,
        )
