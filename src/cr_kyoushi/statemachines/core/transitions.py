from datetime import (
    datetime,
    timedelta,
)
from typing import Optional

from structlog import BoundLogger

from cr_kyoushi.simulation.model import (
    ApproximateFloat,
    Context,
)
from cr_kyoushi.simulation.transitions import Transition
from cr_kyoushi.simulation.util import (
    now,
    sleep,
    sleep_until,
)


__all__ = ["Idle", "IdleTransition"]


class Idle:
    """Transition function that idles and does nothing"""

    def __init__(
        self,
        idle_amount: ApproximateFloat,
        end_time: Optional[datetime] = None,
    ):
        self._idle_amount: ApproximateFloat = idle_amount
        self._end_time: Optional[datetime] = end_time

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        if self._end_time is None:
            sleep(self._idle_amount)
        # if we have an endtime we need special considerations
        else:
            # calc datetime to idle until
            idle_time = now() + timedelta(seconds=self._idle_amount.value)

            # sleep either until idle datetime or until end time
            # if that is earlier
            sleep_until(min(idle_time, self._end_time))


class IdleTransition(Transition):
    """Transition that idles and does nothing"""

    def __init__(
        self,
        idle_amount: ApproximateFloat,
        end_time: Optional[datetime] = None,
        name=None,
        target=None,
    ):
        super().__init__(
            transition_function=Idle(
                idle_amount=idle_amount,
                end_time=end_time,
            ),
            name=name,
            target=target,
        )
