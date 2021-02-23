from typing import Optional

from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation import states
from cr_kyoushi.simulation.transitions import (
    NoopTransition,
    Transition,
)
from cr_kyoushi.simulation.util import now

from ..core.states import ActivityState
from .actions import SUDO_REGEX
from .context import Context


class ActivitySelectionState(states.AdaptiveProbabilisticState):
    """The main activity selection state for the ssh user.

    This will decide between either entering the ssh activity or idling.
    """

    def __init__(
        self,
        name: str,
        ssh_transition: Transition,
        idle_transition: Transition,
        ssh_max_daily: int = 10,
        ssh_weight: float = 0.6,
        idle_weight: float = 0.4,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            ssh_transition: The transition to enter the ssh activity
            idle_transition: The idle transition
            ssh_max_daily: The maximum amount of times to enter the ssh activity per day.
            ssh_weight: The propability of entering the ssh activity.
            idle_weight: The propability of entering the idle activity.
        """
        super().__init__(
            name=name,
            transitions=[ssh_transition, idle_transition],
            weights=[ssh_weight, idle_weight],
            name_prefix=name_prefix,
        )
        self.__ssh = ssh_transition
        self.__ssh_count = 0
        self.__ssh_max = ssh_max_daily
        self.__day = now().date()

    def adapt_before(self, log, context):
        """Sets the propability of entering the ssh activity to 0 if the daylie maximum is reached"""
        super().adapt_before(log, context)

        # reset ssh count and modifiers if we have a new day
        current_day = now().date()
        if self.__day != current_day:
            self.__day = current_day
            self.__ssh_count = 0
            self.reset()

        # if we reached the ssh limit set the transition probability to 0
        if self.__ssh_count >= self.__ssh_max:
            self._modifiers[self.__ssh] = 0

    def adapt_after(self, log, context, selected):
        """Increases the ssh activity enter count"""
        super().adapt_after(log, context, selected)

        # increase ssh count if we selected the transition
        if selected == self.__ssh:
            self.__ssh_count += 1


SelectedServer = states.SequentialState
"""Selected server state"""


class Connected(ActivityState):
    """Connected state

    i.e., the user is currently connected to a server.
    """

    def __init__(
        self,
        name: str,
        select_chain: Transition,
        disconnect: Transition,
        select_chain_weight: float = 0.9,
        disconnect_weight: float = 0.1,
        disconnect_increase=3,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name to assign to the state
            select_chain: The select command chain transition
            disconnect: The SSH disconnect transition
            select_chain_weight: The propability of selecting the select_chain transition.
            disconnect_weight: The propability of selecting the select_chain transition.
            disconnect_increase: The multiplicative factor by which the disconnect chance
                                 increases each time the user does not disconnect.
        """
        super().__init__(
            name,
            [select_chain, disconnect],
            disconnect,
            [select_chain_weight, disconnect_weight],
            modifiers=[1, 1],
            ret_increase=disconnect_increase,
            name_prefix=name_prefix,
        )
        self._select: Transition = select_chain

    def adapt_before(self, log: BoundLogger, context: Context):
        assert context.ssh_user.host is not None

        super().adapt_before(log, context)

        # disable command selection if we have no commands
        # for this host
        self._modifiers[self._select] = (
            1 if len(context.ssh_user.host.commands) > 0 else 0
        )

    def adapt_after(
        self,
        log: BoundLogger,
        context: Context,
        selected,
    ):
        super().adapt_after(log, context, selected)
        log.debug("Probs", probs=self.probabilities)


class ExecutingCommandChain(states.ChoiceState):
    """Executing command chain state

    i.e., the user is executing a chain of shell commands.
    """

    def __init__(
        self,
        name: str,
        execute_command: Transition,
        finished: Transition,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name to assign to the state
            execute_command: The command execution transition
            finished: The transition to execute once all
                      commands in the chain have been executed.
        """
        super().__init__(
            name,
            self._have_command,
            execute_command,
            finished,
            name_prefix=name_prefix,
        )

    def _have_command(self, log: BoundLogger, context: Context) -> bool:
        """
        Checks wether if we still have commands to execute.

        Returns:
            `True` if the remaining command list is not empty `False` otherwise.
        """
        return len(context.ssh_user.commands) > 0


class SudoDialogCheck(states.ChoiceState):
    """Pseudo check state for checking if we must enter the sudo password"""

    def __init__(
        self,
        name: str,
        exec_cmd_chain: str,
        sudo_dialog: str,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name to assign to the state
            exec_cmd_chain: The executing command chain states name
            sudo_dialog: The sudo dialog states name
        """
        executed = NoopTransition(
            "no_sudo_password_required",
            exec_cmd_chain,
            name_prefix=name_prefix,
        )
        require_password = NoopTransition(
            "require_sudo_password",
            sudo_dialog,
            name_prefix=name_prefix,
        )
        super().__init__(
            name,
            self._is_sudo_prompt,
            require_password,
            executed,
            name_prefix=name_prefix,
        )

    def _is_sudo_prompt(self, log: BoundLogger, context: Context) -> bool:
        """Check function for checking if we have sudo password prompt

        Returns:
            `True` if there is a prompt `False` otherwise
        """
        return bool(SUDO_REGEX.search(context.ssh_user.output[-1]))


class SudoDialog(states.AdaptiveProbabilisticState):
    """Sudo dialog state

    i.e., the user is prompted to enter the sudo password.
    """

    def __init__(
        self,
        name: str,
        enter_password: Transition,
        fail_password: Transition,
        fail_escalation: Transition,
        enter_password_weight: float = 0.95,
        fail_password_weight: float = 0.05,
        fail_increase: float = 4.0,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name to assign to the state
            enter_password: The enter correct password transition
            fail_password: The enter wrong password transition
            fail_escalation: The fail sudo escalation transition i.e., the transition to use for the final password try
            enter_password_weight: The chance the user will enter the correct password
            fail_password_weight: The chance the user will enter an incorrect password
            fail_increase: The multiplicative factor by which to increase the fail chance after each fail
        """

        super().__init__(
            name,
            [enter_password, fail_password],
            [enter_password_weight, fail_password_weight],
            modifiers=[1, 1],
            name_prefix=name_prefix,
        )
        self._fail_password = fail_password
        self._fail_escalation = fail_escalation
        self.fails = 0
        self.fail_increase = fail_increase

    def adapt_after(self, log, context, selected):
        super().adapt_after(log, context, selected)

        # with each fail we increase the likelyhood of typing
        # the wrong password and the fails counter
        if selected == self._fail_password:
            self.fails += 1
            self._modifiers[self._fail_password] *= self.fail_increase
        else:
            self.fails = 0
            self._modifiers[self._fail_password] = 1

    def next(self, log: BoundLogger, context: Context):
        assert context.ssh_user.host is not None

        choice = super().next(log, context)
        # if this our last try and we are about to fail again
        # then we will fail sudo escalation
        if (
            self.fails >= context.ssh_user.host.max_sudo_tries
            and choice == self._fail_password
        ):
            return self._fail_escalation
        return choice
