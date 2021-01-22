from typing import (
    Optional,
    Union,
)

from structlog import BoundLogger

from cr_kyoushi.simulation import (
    states,
    transitions,
)
from cr_kyoushi.simulation.util import now

from .config import Context


__all__ = ["ActivitySelectionState", "WebsiteState"]


class ActivitySelectionState(states.ProbabilisticState):
    def __init__(
        self,
        name: str,
        max_websites_day: int,
        website_transition: transitions.Transition,
        website_weight: Union[int, float],
        idle_transition: transitions.Transition,
        idle_weight: Union[int, float],
    ):
        super().__init__(
            name,
            [website_transition, idle_transition],
            [website_weight, idle_weight],
            allow_uneven_probabilites=False,
        )
        self._max_websites_day: int = max_websites_day

    def next(
        self, log: BoundLogger, context: Context
    ) -> Optional[transitions.Transition]:
        # update website daylie visit count
        current_day = now().date()
        if context.current_day != current_day:
            context.current_day = current_day
            context.website_count = 0

        # if we reached the maximum visits we always idle
        if context.website_count >= self._max_websites_day:
            return self.transitions[1]

        return super().next(log, context)


class WebsiteState(states.ProbabilisticState):
    def __init__(
        self,
        name: str,
        website_transition: transitions.Transition,
        website_weight: Union[int, float],
        leave_transition: transitions.Transition,
        leave_weight: Union[int, float],
        max_depth: int,
    ):
        super().__init__(
            name,
            [website_transition, leave_transition],
            [website_weight, leave_weight],
            allow_uneven_probabilites=False,
        )
        self._max_depth: int = max_depth

    def next(
        self, log: BoundLogger, context: Context
    ) -> Optional[transitions.Transition]:
        if (
            len(context.available_links) == 0
            or context.website_depth >= self._max_depth
        ):
            # if the websites have not links to navigate to
            # or we have reached max depth then we always leave the website
            return self.transitions[1]

        return super().next(log, context)
