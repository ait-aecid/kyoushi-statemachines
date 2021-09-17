import random

from datetime import datetime
from typing import (
    List,
    Optional,
    Union,
)

from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.simulation.states import (
    ChoiceState,
    ProbabilisticState,
    SequentialState,
    State,
)
from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    Transition,
    TransitionFunction,
)
from cr_kyoushi.simulation.util import now

from ..core.config import IdleConfig
from . import actions
from .config import (
    EscalateConfig,
    HostCMD,
    NetworkReconConfig,
    WebShellCMD,
    WordpressAttackConfig,
)
from .context import Context


class AttackStepTransition:
    def __init__(
        self,
        transition: Transition,
        children: List["AttackStepTransition"] = [],
    ):
        self.transition: Transition = transition
        self.children: List["AttackStepTransition"] = children

    @property
    def transitions(self) -> List[Transition]:
        t = [self.transition]
        for child in self.children:
            t.extend(child.transitions)
        return t


class AttackStep:
    def __init__(
        self,
        action: TransitionFunction,
        name: Optional[str] = None,
        children: List["AttackStep"] = [],
        delay_before: Union[ApproximateFloat, float] = 0.0,
        delay_after: Union[ApproximateFloat, float] = 0.0,
    ):
        self._action: TransitionFunction = action
        self._name: Optional[str] = name
        self.children: List["AttackStep"] = children
        self._delay_before: Union[ApproximateFloat, float] = delay_before
        self._delay_after: Union[ApproximateFloat, float] = delay_after

    def transition(
        self,
        target: str,
        name_prefix: Optional[str] = None,
    ) -> DelayedTransition:
        return DelayedTransition(
            transition_function=self._action,
            name=self._name,
            target=target,
            delay_before=self._delay_before,
            delay_after=self._delay_after,
            name_prefix=name_prefix,
        )

    def convert(
        self, target: str, name_prefix: Optional[str] = None
    ) -> AttackStepTransition:
        return AttackStepTransition(
            transition=self.transition(target, name_prefix),
            children=[child.convert(target, name_prefix) for child in self.children],
        )


class AttackPhaseState(State):
    def __init__(
        self,
        name: str,
        steps: List[AttackStep],
        next_phase: Optional[Transition] = None,
        name_prefix: Optional[str] = None,
    ):
        self._next_phase: Optional[Transition] = next_phase
        # convert attack steps in attack step transitions
        self.steps: List[AttackStepTransition] = [
            step.convert(name, name_prefix) for step in steps
        ]

        # combine all steps and their children into on big
        # transition list
        transitions: List[Transition] = (
            [] if self._next_phase is None else [self._next_phase]
        )
        for step in self.steps:
            transitions.extend(step.transitions)

        super().__init__(name, transitions=transitions, name_prefix=name_prefix)

    def next(self, log: BoundLogger, context) -> Optional[Transition]:
        if len(self.steps) > 0:
            # choose a random step to execute
            step: AttackStepTransition = random.choice(self.steps)

            # add potential step children to available steps list
            self.steps.extend(step.children)
            # remove selected step from available steps
            self.steps.remove(step)
            return step.transition
        else:
            # if we have no steps in this phase left
            # then execute the transition leading to the next phase
            return self._next_phase


VPNConnected = SequentialState


class ReconNetworks(AttackPhaseState):
    def __init__(
        self,
        name: str,
        config: NetworkReconConfig,
        idle: IdleConfig,
        next_phase: Optional[Transition] = None,
        name_prefix: Optional[str] = None,
    ):

        service_scan = AttackStep(
            name="service_scan",
            action=actions.NmapServiceScan(
                [str(h) for h in config.hosts],
                extra_args=config.service_scan_extra_args,
            ),
            delay_after=idle.small,
            children=[],
        )

        intranet_scan = AttackStep(
            name="host_discover_local",
            action=actions.NmapHostScan(
                [str(config.intranet)], extra_args=config.intranet_scan_extra_args
            ),
            delay_after=idle.small,
            children=[service_scan],
        )

        dns_scan = AttackStep(
            name="dns_brute_force",
            action=actions.NmapDNSBrute(
                [str(config.dns)], config.domain, extra_args=config.dns_scan_extra_args
            ),
            delay_after=idle.small,
            children=[intranet_scan],
        )

        dmz_scan = AttackStep(
            name="host_discover_dmz",
            action=actions.NmapHostScan(
                [str(config.dmz)], extra_args=config.dmz_scan_extra_args
            ),
            delay_after=idle.small,
            children=[],
        )

        super().__init__(
            name, [dns_scan, dmz_scan], next_phase=next_phase, name_prefix=name_prefix
        )


class ReconWordpress(AttackPhaseState):
    def __init__(
        self,
        name: str,
        config: WordpressAttackConfig,
        idle: IdleConfig,
        next_phase: Optional[Transition] = None,
        name_prefix: Optional[str] = None,
    ):
        wpscan = AttackStep(
            name="wpscan",
            action=actions.WPScan(
                str(config.url), extra_args=config.wordpress_extra_args
            ),
            delay_after=idle.small,
        )

        dirb_scan = AttackStep(
            name="dirb_scan",
            action=actions.Dirb(
                [str(config.url)],
                wordlists=[str(p.absolute) for p in config.dirb_wordlists],
                extra_args=config.dirb_extra_args,
            ),
            delay_after=idle.small,
        )

        super().__init__(
            name, [wpscan, dirb_scan], next_phase=next_phase, name_prefix=name_prefix
        )


def web_shell_cmd_to_step(cmd: WebShellCMD, idle: IdleConfig) -> AttackStep:
    return AttackStep(
        name=cmd.name,
        action=actions.ExecWebShellCommand(cmd=cmd.cmd),
        delay_after=idle.get(cmd.idle_after),
        children=[web_shell_cmd_to_step(child, idle) for child in cmd.children],
    )


class ReconHost(AttackPhaseState):
    def __init__(
        self,
        name: str,
        config: WordpressAttackConfig,
        idle: IdleConfig,
        next_phase: Optional[Transition] = None,
        name_prefix: Optional[str] = None,
    ):
        attack_steps = [web_shell_cmd_to_step(cmd, idle) for cmd in config.commands]

        super().__init__(
            name, attack_steps, next_phase=next_phase, name_prefix=name_prefix
        )


class WaitChoice(ChoiceState):
    def __init__(
        self,
        name: str,
        escalate_time: datetime,
        listen_reverse_shell: Transition,
        decide_cracking_method: Transition,
        name_prefix: Optional[str] = None,
    ):
        self.escalate_time: datetime = escalate_time
        super().__init__(
            name,
            self.check_escalate_time,
            listen_reverse_shell,
            decide_cracking_method,
            name_prefix=name_prefix,
        )

    def check_escalate_time(self, log: BoundLogger, context: Context) -> bool:
        return now() >= self.escalate_time


class CrackChoice(ProbabilisticState):
    def __init__(
        self,
        name: str,
        offline_cracking: Transition,
        wphashcrack: Transition,
        offline_cracking_probability: float,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            [offline_cracking, wphashcrack],
            [offline_cracking_probability, 1 - offline_cracking_probability],
            name_prefix=name_prefix,
        )


CrackingPasswords = SequentialState
CrackedPasswords = SequentialState
WPHashCracked = SequentialState
VPNReconnected = SequentialState
ListeningReverseShell = SequentialState
OpeningReverseShell = SequentialState
ReverseShell = SequentialState
PTYShell = SequentialState


def host_cmd_to_step(cmd: HostCMD, idle: IdleConfig) -> AttackStep:
    return AttackStep(
        name=cmd.name,
        action=actions.ExecShellCommand(cmd.cmd, cmd.expect),
        delay_after=idle.get(cmd.idle_after),
        children=[host_cmd_to_step(child, idle) for child in cmd.children],
    )


class Escalated(AttackPhaseState):
    def __init__(
        self,
        name: str,
        config: EscalateConfig,
        idle: IdleConfig,
        next_phase: Optional[Transition] = None,
        name_prefix: Optional[str] = None,
    ):
        attack_steps = [host_cmd_to_step(cmd, idle) for cmd in config.commands]

        super().__init__(
            name, attack_steps, next_phase=next_phase, name_prefix=name_prefix
        )
