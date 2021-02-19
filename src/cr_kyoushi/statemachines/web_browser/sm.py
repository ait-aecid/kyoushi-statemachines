from cr_kyoushi.simulation import (
    sm,
    states,
    transitions,
)

from ..core.selenium import SeleniumStatemachine
from ..core.transitions import IdleTransition
from .config import (
    Context,
    ContextModel,
    StatemachineConfig,
)
from .states import (
    ActivitySelectionState,
    WebsiteState,
)
from .transitions import (
    OpenLink,
    VisitWebsite,
    background_website,
    close_website,
    leave_website,
)


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

        website_transition = transitions.DelayedTransition(
            transition_function=VisitWebsite(
                config.user.websites,
                "selecting_activity",
            ),
            name="visit_website",
            target="on_website",
            delay_after=config.idle.medium,
        )

        link_transition = transitions.DelayedTransition(
            transition_function=OpenLink("selecting_activity"),
            name="visit_link",
            target="on_website",
            delay_after=config.idle.medium,
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
