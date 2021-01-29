from datetime import datetime
from typing import (
    List,
    Optional,
)

from faker import Faker

from cr_kyoushi.simulation import sm
from cr_kyoushi.simulation.config import get_seed
from cr_kyoushi.simulation.model import WorkSchedule
from cr_kyoushi.simulation.states import State

from ..core.selenium import (
    SeleniumConfig,
    get_webdriver,
    install_webdriver,
)
from ..core.transitions import IdleTransition
from .activities import (
    get_address_book_activity,
    get_admin_activity,
    get_base_activity,
    get_calendar_activity,
    get_mail_activity,
    get_menu_activity,
    get_notes_activity,
    get_preferences_activity,
    get_tasks_activity,
)
from .config import (
    Context,
    StatemachineConfig,
)
from .states import ActivitySelectionState


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(sm.WorkHoursStatemachine):
    _selenium_config: SeleniumConfig
    _webdriver_path: Optional[str]

    def __init__(
        self,
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
            start_time=start_time,
            end_time=end_time,
            work_schedule=work_schedule,
            max_errors=max_errors,
        )
        self._selenium_config = selenium_config
        self._webdriver_path = None
        self.context: Optional[Context] = None
        # seed faker random with global seed
        Faker.seed(get_seed())
        self.fake: Faker = Faker()

    def setup_context(self):
        # we assume we only install once at the start of the sm
        if self._webdriver_path is None:
            self._webdriver_path = install_webdriver(self._selenium_config)

        driver = get_webdriver(
            self._selenium_config,
            self._webdriver_path,
        )

        self.context = Context(
            driver=driver,
            main_window=driver.current_window_handle,
            fake=self.fake,
        )

    def destroy_context(self):
        if self.context is not None:
            self.context.driver.quit()

    def _resume_work(self):
        self.current_state = self.initial_state
        # reset context
        self.destroy_context()
        self.setup_context()


class StatemachineFactory(sm.StatemachineFactory):
    @property
    def name(self) -> str:
        return "HordeUserStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def build(self, config: StatemachineConfig):
        # get base states and transitions

        (
            # transitions
            horde_transition,
            pause_horde,
            return_select,
            # states
            login_check,
            login_page,
            logout_choice,
        ) = get_base_activity(config)

        # mail states and nav
        (
            nav_mail,
            mails_page,
            mail_view,
            mail_info,
            mail_compose,
        ) = get_mail_activity(config, return_select)

        # preferences states and nav
        (
            nav_preferences,
            preferences_page,
            preferences_personal_page,
        ) = get_preferences_activity(config)

        # admin states and nav

        (
            nav_admin,
            # states
            admin_page,
            admin_config_page,
            admin_groups_page,
            admin_group_added,
            admin_group_deleting,
            admin_php_shell_page,
            admin_sql_shell_page,
            admin_cli_shell_page,
        ) = get_admin_activity(config, return_select)

        # notes states and nav

        (
            nav_notes,
            # states
            notes_page,
            note_creator,
            note_editor,
        ) = get_notes_activity(config, return_select)

        # tasks states and nav

        (
            nav_tasks,
            # states
            tasks_page,
            task_creator,
            task_editor,
        ) = get_tasks_activity(config, return_select)

        # address book states and nav

        (
            nav_address_book,
            # states
            address_book_page,
            contact_compose,
            contacts_browser,
            contact_info,
            contact_delete_confirming,
        ) = get_address_book_activity(config, return_select)

        # calendar states and nav

        (
            nav_calendar,
            # states
            calendar_page,
            event_compose,
            event_edit,
        ) = get_calendar_activity(config, return_select)

        # horde main menu state

        selecting_menu = get_menu_activity(
            config,
            nav_mail,
            nav_preferences,
            nav_admin,
            nav_notes,
            nav_tasks,
            nav_address_book,
            nav_calendar,
            pause_horde,
        )

        # sm config

        idle_transition = IdleTransition(
            idle_amount=config.idle.big,
            end_time=config.end_time,
            name="idle",
            target="selecting_activity",
        )

        initial = ActivitySelectionState(
            name="selecting_activity",
            horde_transition=horde_transition,
            idle_transition=idle_transition,
        )

        return Statemachine(
            initial_state="selecting_activity",
            states=[
                initial,
                login_check,
                login_page,
                selecting_menu,
                logout_choice,
                mails_page,
                mail_view,
                mail_info,
                mail_compose,
                preferences_page,
                preferences_personal_page,
                admin_page,
                admin_config_page,
                admin_groups_page,
                admin_group_added,
                admin_group_deleting,
                admin_php_shell_page,
                admin_sql_shell_page,
                admin_cli_shell_page,
                notes_page,
                note_creator,
                note_editor,
                tasks_page,
                task_creator,
                task_editor,
                address_book_page,
                contact_compose,
                contacts_browser,
                contact_info,
                contact_delete_confirming,
                calendar_page,
                event_compose,
                event_edit,
            ],
            selenium_config=config.selenium,
            start_time=config.start_time,
            end_time=config.end_time,
            work_schedule=config.schedule,
            max_errors=config.max_errors,
        )
