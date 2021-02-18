"""Statemachine that only idles or executes the ssh user activity."""

from datetime import datetime
from typing import (
    List,
    Optional,
)

from faker import Faker

from cr_kyoushi.simulation import sm
from cr_kyoushi.simulation.config import get_seed
from cr_kyoushi.simulation.model import WorkSchedule
from cr_kyoushi.simulation.states import State

from ..core.transitions import IdleTransition
from .activities import get_ssh_activity
from .config import StatemachineConfig
from .context import Context
from .states import ActivitySelectionState


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(sm.WorkHoursStatemachine):
    """SSH user activity state machine"""

    def __init__(
        self,
        initial_state: str,
        states: List[State],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        work_schedule: Optional[WorkSchedule] = None,
        max_errors: int = 0,
    ):
        super().__init__(
            initial_state,
            states,
            start_time=start_time,
            end_time=end_time,
            work_schedule=work_schedule,
            max_errors=max_errors,
        )
        self.context: Optional[Context] = None
        # seed faker random with global seed
        Faker.seed(get_seed())
        self.fake: Faker = Faker()

    def setup_context(self):
        self.context = Context(
            fake=self.fake,
        )

    def _resume_work(self):
        self.current_state = self.initial_state
        # reset context
        self.destroy_context()
        self.setup_context()


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
