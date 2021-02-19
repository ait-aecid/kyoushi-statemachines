from cr_kyoushi.simulation import sm

from ..core.selenium import SeleniumStatemachine
from ..core.transitions import IdleTransition
from .activities import get_browser_activity
from .config import (
    Context,
    ContextModel,
    StatemachineConfig,
)
from .states import ActivitySelectionState


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(SeleniumStatemachine[Context]):
    def setup_context(self):
        driver = self.get_driver()
        self.context = ContextModel(
            driver=driver,
            main_window=driver.current_window_handle,
            fake=self.fake,
        )


class StatemachineFactory(sm.StatemachineFactory):
    @property
    def name(self) -> str:
        return "WebBrowserStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def build(self, config: StatemachineConfig):
        # setup transitions

        idle_transition = IdleTransition(
            idle_amount=config.idle.big,
            end_time=config.end_time,
            name="idle",
            target="selecting_activity",
        )

        (website_transition, on_website, leaving_website) = get_browser_activity(
            config.idle, config.user, config.states
        )

        # setup states
        selecting_activity = ActivitySelectionState(
            name="selecting_activity",
            max_daily=config.user.max_daily,
            website_transition=website_transition,
            website_weight=config.states.selecting_activity.visit_website,
            idle_transition=idle_transition,
            idle_weight=config.states.selecting_activity.idle,
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
