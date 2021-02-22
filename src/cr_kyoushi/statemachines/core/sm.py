from datetime import datetime
from typing import (
    Generic,
    List,
    Optional,
    TypeVar,
)

from faker import Faker

from cr_kyoushi.simulation.config import get_seed
from cr_kyoushi.simulation.model import WorkSchedule
from cr_kyoushi.simulation.sm import WorkHoursStatemachine
from cr_kyoushi.simulation.states import State

from .config import (
    FakerContext,
    FakerContextModel,
)


C = TypeVar("C", bound=FakerContext)


class FakerStatemachine(WorkHoursStatemachine, Generic[C]):
    """Generic Faker state machine class"""

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
        self.context: Optional[C] = None
        # seed faker random with global seed
        Faker.seed(get_seed())
        self.fake: Faker = Faker()

    def setup_context(self):
        raise NotImplementedError()

    def _pause_work(self):
        self.current_state = self.initial_state
        self.destroy_context()

    def _resume_work(self):
        # recreate context
        self.setup_context()


class Statemachine(FakerStatemachine[FakerContext]):
    """Basic faker state machine class with a faker context"""

    def setup_context(self):
        self.context = FakerContextModel(
            fake=self.fake,
        )
