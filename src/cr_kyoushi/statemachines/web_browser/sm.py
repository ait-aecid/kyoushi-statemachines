from datetime import datetime
from typing import List
from typing import Optional

from cr_kyoushi.simulation import sm
from cr_kyoushi.simulation import states
from cr_kyoushi.simulation import transitions
from cr_kyoushi.simulation.model import WorkSchedule

from ..core.selenium import SeleniumConfig
from ..core.selenium import get_webdriver
from ..core.selenium import install_webdriver
from .config import Context
from .config import StatemachineConfig
from .states import ActivitySelectionState
from .states import WebsiteState
from .transitions import Idle
from .transitions import OpenLink
from .transitions import VisitWebsite
from .transitions import background_website
from .transitions import close_website
from .transitions import leave_website


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(sm.WorkHoursStatemachine):
    _selenium_config: SeleniumConfig
    _webdriver_path: Optional[str]

    def __init__(
        self,
        initial_state: str,
        states: List[states.State],
        selenium_config: SeleniumConfig,
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
        self._selenium_config = selenium_config
        self._webdriver_path = None

    def setup_context(self):
        # we assume we only install once at the start of the sm
        if self._webdriver_path is None:
            self._webdriver_path = install_webdriver(self._selenium_config)

        self.context = Context(
            driver=get_webdriver(
                self._selenium_config,
                self._webdriver_path,
            )
        )

    def destroy_context(self):
        self.context.driver.close()

    def _resume_work(self):
        self.current_state = self.initial_state
        # reset context
        self.destroy_context()
        self.setup_context()


class StatemachineFactory(sm.StatemachineFactory):
    @property
    def name(self) -> str:
        return "WebBrowserStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def build(self, config: StatemachineConfig):
        # setup transitions
        idle_transition = transitions.Transition(
            transition_function=Idle(config.user.idle_time, config.end_time),
            name="idle",
            target="selecting_activity",
        )

        website_transition = transitions.DelayedTransition(
            transition_function=VisitWebsite(
                config.user.websites,
                "selecting_activity",
            ),
            name="visit_website",
            target="on_website",
            delay_after=config.user.wait_time,
        )

        link_transition = transitions.DelayedTransition(
            transition_function=OpenLink("selecting_activity"),
            name="visit_link",
            target="on_website",
            delay_after=config.user.wait_time,
        )

        # setup states
        selecting_activity = ActivitySelectionState(
            name="selecting_activity",
            max_websites_day=config.user.max_websites_day,
            website_transition=website_transition,
            website_weight=config.states.selecting_activity.visit_website,
            idle_transition=idle_transition,
            idle_weight=config.states.selecting_activity.idle,
        )

        on_website = WebsiteState(
            name="on_website",
            website_transition=link_transition,
            website_weight=config.states.on_website.visit_link,
            leave_transition=leave_website,
            leave_weight=config.states.on_website.leave_website,
            max_depth=config.user.max_depth,
        )

        leaving_website = states.ProbabilisticState(
            name="leaving_website",
            transitions=[background_website, close_website],
            weights=[
                config.states.leaving_website.background,
                config.states.leaving_website.close,
            ],
        )

        return Statemachine(
            initial_state="selecting_activity",
            states=[selecting_activity, on_website, leaving_website],
            selenium_config=config.selenium,
            start_time=config.start_time,
            end_time=config.end_time,
            work_schedule=config.schedule,
            max_errors=config.max_errors,
        )
