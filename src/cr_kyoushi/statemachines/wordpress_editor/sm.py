"""Statemachine that only idles or executes the wordpress editor activity."""

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
    get_base_activity,
    get_editor_activity,
)
from .config import (
    StatemachineConfig,
    WordpressEditorConfig,
)
from .context import (
    Context,
    ContextModel,
    WordpressEditorContext,
)
from .states import ActivitySelectionState


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(SeleniumStatemachine[Context]):
    """Wordpress editor activity state machine"""

    def __init__(
        self,
        initial_state: str,
        states: List[State],
        selenium_config: SeleniumConfig,
        user_config: WordpressEditorConfig,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        work_schedule: Optional[WorkSchedule] = None,
        max_errors: int = 0,
    ):
        super().__init__(
            initial_state,
            states,
            selenium_config,
            start_time=start_time,
            end_time=end_time,
            work_schedule=work_schedule,
            max_errors=max_errors,
        )
        self._user_config: WordpressEditorConfig = user_config

    def setup_context(self):
        driver = self.get_driver()
        self.context = ContextModel(
            driver=driver,
            main_window=driver.current_window_handle,
            fake=self.fake,
            wp_editor=WordpressEditorContext(
                username=self._user_config.username,
                password=self._user_config.password,
            ),
        )


class StatemachineFactory(sm.StatemachineFactory):
    """Wordpress editor activity state machine factory"""

    @property
    def name(self) -> str:
        return "WordpressEditorStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def build(self, config: StatemachineConfig):
        idle = config.idle
        user_config = config.wp_editor
        states_config = config.states

        (
            goto_wp_admin,
            pause,
            logged_in_check,
            login_page,
            logout_choice,
        ) = get_base_activity(
            idle=idle,
            user_config=user_config,
            login_config=states_config.login_page,
            logout_config=states_config.logout_choice,
        )

        (
            selecting_menu,
            comments_page,
            reply_editor,
            posts_page,
            post_editor,
            post_publishing,
            post_published,
        ) = get_editor_activity(
            idle=idle,
            user_config=user_config,
            menu_config=states_config.selecting_menu,
            comments_config=states_config.comments_page,
            posts_config=states_config.posts_page,
            pause_wordpress=pause,
        )

        idle_transition = IdleTransition(
            idle_amount=idle.big,
            end_time=config.end_time,
            name="idle",
            target="selecting_activity",
        )

        initial = ActivitySelectionState(
            name="selecting_activity",
            wp_editor_transition=goto_wp_admin,
            idle_transition=idle_transition,
            wp_editor_max_daily=user_config.max_daily,
            wp_editor_weight=states_config.selecting_activity.wp_editor,
            idle_weight=states_config.selecting_activity.idle,
        )

        return Statemachine(
            initial_state="selecting_activity",
            states=[
                initial,
                logged_in_check,
                login_page,
                logout_choice,
                selecting_menu,
                comments_page,
                reply_editor,
                posts_page,
                post_editor,
                post_publishing,
                post_published,
            ],
            selenium_config=config.selenium,
            user_config=user_config,
            start_time=config.start_time,
            end_time=config.end_time,
            work_schedule=config.schedule,
            max_errors=config.max_errors,
        )
