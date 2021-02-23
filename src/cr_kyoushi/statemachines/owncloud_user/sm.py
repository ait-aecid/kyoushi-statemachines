"""Statemachine that only idles or executes the owncloud user activity."""


from cr_kyoushi.simulation import sm

from ..core.selenium import SeleniumStatemachine
from ..core.transitions import IdleTransition
from .activities import (
    get_base_activity,
    get_file_details_activity,
    get_file_view_activity,
)
from .config import StatemachineConfig
from .context import (
    Context,
    ContextModel,
)
from .states import ActivitySelectionState


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(SeleniumStatemachine[Context]):
    """Owncloud user activity state machine"""

    def setup_context(self):
        driver = self.get_driver()

        self.context = ContextModel(
            driver=driver,
            main_window=driver.current_window_handle,
            fake=self.fake,
        )


class StatemachineFactory(sm.StatemachineFactory):
    """Owncloud user activity state machine factory"""

    @property
    def name(self) -> str:
        return "OwncloudUserStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def build(self, config: StatemachineConfig):
        idle = config.idle
        user_config = config.owncloud_user
        states_config = config.states

        (
            goto_owncloud,
            pause,
            logged_in_check,
            login_page,
            logout_choice,
        ) = get_base_activity(
            idle=idle,
            owncloud=user_config,
            login_config=states_config.login_page,
            logout_config=states_config.logout_choice,
        )

        (
            selecting_menu,
            all_files,
            favorites,
            sharing_in,
            sharing_out,
            upload_menu,
        ) = get_file_view_activity(
            idle=idle,
            download_config=config.selenium.download,
            owncloud=user_config,
            menu_config=states_config.selecting_menu,
            all_files_config=states_config.all_files,
            favorites_config=states_config.favorites,
            sharing_in_config=states_config.sharing_in,
            sharing_out_config=states_config.sharing_out,
            upload_menu_config=states_config.upload_menu,
            pause_owncloud=pause,
        )

        (file_details, sharing_details, close_check) = get_file_details_activity(
            idle=idle,
            details_config=states_config.file_details,
            sharing_config=states_config.sharing_details,
        )

        idle_transition = IdleTransition(
            idle_amount=idle.big,
            end_time=config.end_time,
            name="idle",
            target="selecting_activity",
        )

        initial = ActivitySelectionState(
            name="selecting_activity",
            owncloud_transition=goto_owncloud,
            idle_transition=idle_transition,
            owncloud_max_daily=user_config.max_daily,
            owncloud_weight=states_config.selecting_activity.owncloud,
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
                all_files,
                favorites,
                sharing_in,
                sharing_out,
                upload_menu,
                file_details,
                sharing_details,
                close_check,
            ],
            selenium_config=config.selenium,
            start_time=config.start_time,
            end_time=config.end_time,
            work_schedule=config.schedule,
            max_errors=config.max_errors,
        )
