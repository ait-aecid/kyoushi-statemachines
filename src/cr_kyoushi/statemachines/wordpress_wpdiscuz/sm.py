"""Statemachine that only idles or executes the wordpress wpDiscuz activity."""
from datetime import datetime
from typing import (
    List,
    Optional,
)

from cr_kyoushi.simulation import sm
from cr_kyoushi.simulation.model import WorkSchedule
from cr_kyoushi.simulation.states import State

from ..core.selenium import (
    SeleniumConfig,
    SeleniumStatemachine,
)
from ..core.transitions import IdleTransition
from .activities import (
    get_post_activity,
    get_posts_activity,
)
from .config import StatemachineConfig
from .context import (
    Context,
    ContextModel,
    WpDiscuzContext,
)
from .states import ActivitySelectionState


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(SeleniumStatemachine[Context]):
    """Wordpress wpDiscuz activity state machine"""

    def __init__(
        self,
        author: str,
        email: str,
        initial_state: str,
        states: List[State],
        selenium_config: SeleniumConfig,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        work_schedule: Optional[WorkSchedule] = None,
        max_errors: int = 0,
    ):
        super().__init__(
            initial_state,
            states,
            selenium_config=selenium_config,
            start_time=start_time,
            end_time=end_time,
            work_schedule=work_schedule,
            max_errors=max_errors,
        )
        self.author: str = author
        self.email: str = email

    def setup_context(self):
        driver = self.get_driver()
        self.context = ContextModel(
            driver=driver,
            main_window=driver.current_window_handle,
            fake=self.fake,
            wpdiscuz=WpDiscuzContext(
                author=self.author,
                email=self.email,
            ),
        )


class StatemachineFactory(sm.StatemachineFactory):
    """Wordpress wpDiscuz activity state machine factory"""

    @property
    def name(self) -> str:
        return "WordpressWpDiscuzStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def build(self, config: StatemachineConfig):
        idle = config.idle

        (goto_wordpress, posts_page, close_choice) = get_posts_activity(
            idle=idle,
            user_config=config.wpdiscuz,
            posts_config=config.states.posts_page,
            close_config=config.states.close_choice,
        )

        (post_page, comment_compose) = get_post_activity(
            idle=idle,
            post_config=config.states.post_page,
            return_home=goto_wordpress,
        )

        idle_transition = IdleTransition(
            idle_amount=idle.big,
            end_time=config.end_time,
            name="idle",
            target="selecting_activity",
        )

        initial = ActivitySelectionState(
            name="selecting_activity",
            wpdiscuz_transition=goto_wordpress,
            idle_transition=idle_transition,
            wpdiscuz_max_daily=config.wpdiscuz.max_daily,
            wpdiscuz_weight=config.states.selecting_activity.wpdiscuz,
            idle_weight=config.states.selecting_activity.idle,
        )

        return Statemachine(
            author=config.wpdiscuz.author,
            email=config.wpdiscuz.email,
            initial_state="selecting_activity",
            states=[
                initial,
                posts_page,
                close_choice,
                post_page,
                comment_compose,
            ],
            selenium_config=config.selenium,
            start_time=config.start_time,
            end_time=config.end_time,
            work_schedule=config.schedule,
            max_errors=config.max_errors,
        )
