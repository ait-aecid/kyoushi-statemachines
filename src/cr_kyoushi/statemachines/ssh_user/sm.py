"""Statemachine that only idles or executes the ssh user activity."""


from cr_kyoushi.simulation import sm

from ..core.sm import FakerStatemachine
from ..core.transitions import IdleTransition
from .activities import get_ssh_activity
from .config import StatemachineConfig
from .context import (
    Context,
    ContextModel,
)
from .states import ActivitySelectionState


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(FakerStatemachine[Context]):
    """SSH user activity state machine"""

    def setup_context(self):
        self.context = ContextModel(
            fake=self.fake,
        )


class StatemachineFactory(sm.StatemachineFactory):
    """SSH user activity state machine factory"""

    @property
    def name(self) -> str:
        return "SSHUserStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def build(self, config: StatemachineConfig):
        idle = config.idle
        user_config = config.ssh_user
        states_config = config.states

        (
            select_ssh_server,
            selected_server,
            connected,
            executing_chain,
            sudo_check,
            sudo_dialog,
        ) = get_ssh_activity(
            idle=idle,
            user=user_config,
            connected_config=states_config.connected,
            sudo_config=states_config.sudo_dialog,
        )

        idle_transition = IdleTransition(
            idle_amount=idle.big,
            end_time=config.end_time,
            name="idle",
            target="selecting_activity",
        )

        initial = ActivitySelectionState(
            name="selecting_activity",
            ssh_transition=select_ssh_server,
            idle_transition=idle_transition,
            ssh_max_daily=user_config.max_daily,
            ssh_weight=states_config.selecting_activity.ssh_user,
            idle_weight=states_config.selecting_activity.idle,
        )

        return Statemachine(
            initial_state="selecting_activity",
            states=[
                initial,
                selected_server,
                connected,
                executing_chain,
                sudo_check,
                sudo_dialog,
            ],
            start_time=config.start_time,
            end_time=config.end_time,
            work_schedule=config.schedule,
            max_errors=config.max_errors,
        )
