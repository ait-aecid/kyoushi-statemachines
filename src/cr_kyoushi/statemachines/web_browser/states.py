from typing import Optional

from structlog import BoundLogger

from cr_kyoushi.simulation import (
    states,
    transitions,
)
from cr_kyoushi.simulation.util import now

from .config import Context


__all__ = ["ActivitySelectionState", "WebsiteState", "LeavingWebsite"]


class ActivitySelectionState(states.ProbabilisticState):
    def __init__(
        self,
        name: str,
        max_daily: int,
        website_transition: transitions.Transition,
        website_weight: float,
        idle_transition: transitions.Transition,
        idle_weight: float,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            [website_transition, idle_transition],
            [website_weight, idle_weight],
            name_prefix=name_prefix,
        )
        self._max_daily: int = max_daily

    def next(
        self, log: BoundLogger, context: Context
    ) -> Optional[transitions.Transition]:
        browser = context.web_browser
        # update website daylie visit count
        current_day = now().date()
        if browser.current_day != current_day:
            browser.current_day = current_day
            browser.website_count = 0

        # if we reached the maximum visits we always idle
        if browser.website_count >= self._max_daily:
            return self.transitions[1]

        return super().next(log, context)


class WebsiteState(states.ProbabilisticState):
    def __init__(
        self,
        name: str,
        website_transition: transitions.Transition,
        website_weight: float,
        leave_transition: transitions.Transition,
        leave_weight: float,
        max_depth: int,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            [website_transition, leave_transition],
            [website_weight, leave_weight],
            name_prefix=name_prefix,
        )
        self._max_depth: int = max_depth

    def next(
        self, log: BoundLogger, context: Context
    ) -> Optional[transitions.Transition]:
        browser = context.web_browser
        if (
            len(browser.available_links) == 0
            or browser.website_depth >= self._max_depth
        ):
            # if the websites have not links to navigate to
            # or we have reached max depth then we always leave the website
            return self.transitions[1]

        return super().next(log, context)


LeavingWebsite = states.ProbabilisticState
