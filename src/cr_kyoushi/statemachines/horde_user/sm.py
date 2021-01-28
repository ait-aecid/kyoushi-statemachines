from datetime import datetime
from typing import (
    Dict,
    List,
    Optional,
    cast,
)

from faker import Faker

from cr_kyoushi.simulation import sm
from cr_kyoushi.simulation.config import get_seed
from cr_kyoushi.simulation.model import WorkSchedule
from cr_kyoushi.simulation.states import State
from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    NoopTransition,
    Transition,
)

from ..core.selenium import (
    SeleniumConfig,
    get_webdriver,
    install_webdriver,
)
from ..core.transitions import IdleTransition
from . import (
    actions,
    nav,
    states,
)
from .config import (
    Context,
    StatemachineConfig,
)


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
        # setup transitions

        idle_transition = IdleTransition(
            idle_amount=5,
            end_time=config.end_time,
            name="idle",
            target="selecting_activity",
        )

        horde_transition = Transition(
            transition_function=nav.GoToHordeWebsite(config.horde.url),
            name="go_to_horde",
            target="login_check",
        )

        login = DelayedTransition(
            transition_function=actions.LoginToHorde(
                username=config.horde.username,
                password=config.horde.password,
            ),
            name="login",
            target="selecting_menu",
            delay_after=5,
        )

        fail_login = DelayedTransition(
            transition_function=actions.LoginToHorde(
                username=config.horde.username,
                password=config.horde.password,
                fail=True,
            ),
            name="fail_login",
            target="login_page",
            delay_after=5,
        )

        pause_horde = NoopTransition(name="pause", target="logout?")

        horde_logout = DelayedTransition(
            transition_function=actions.logout_of_horde,
            name="horde_logout",
            target="selecting_activity",
            delay_after=5,
        )

        return_select = NoopTransition(name="return", target="selecting_menu")

        # mail transitions

        nav_mail_menu = DelayedTransition(
            transition_function=nav.navigate_mail_menu,
            name="nav_mail_menu",
            target="mails_page",
            delay_after=5,
        )

        refresh_mail = Transition(
            transition_function=actions.refresh_mail,
            name="refresh_mail",
            target="mails_page",
        )

        new_mail = DelayedTransition(
            transition_function=actions.new_mail,
            name="new_mail",
            target="mail_compose",
            delay_after=5,
        )

        view_mail = DelayedTransition(
            transition_function=actions.view_mail,
            name="view_mail",
            target="mail_view",
            delay_after=5,
        )

        delete_mail = DelayedTransition(
            transition_function=actions.delete_mail,
            name="delete_mail",
            target="mails_page",
            delay_after=5,
        )

        open_mail = DelayedTransition(
            transition_function=actions.open_mail,
            name="open_mail",
            target="mail_info",
            delay_after=5,
        )

        reply_mail = DelayedTransition(
            transition_function=actions.reply_mail,
            name="reply_mail",
            target="mail_compose",
            delay_after=5,
        )

        send_mail = Transition(
            transition_function=actions.SendMail(
                # we cast here since mypy does not recognize EmailStr as str
                contacts=cast(Dict[str, float], config.horde.contacts),
                attachments={
                    str(path.absolute()): p
                    for path, p in config.horde.attachments.items()
                },
            ),
            name="send_mail",
            target="mails_page",
        )

        # preferences transitions

        nav_preferences = DelayedTransition(
            transition_function=nav.navigate_preferences_global,
            name="nav_preferences",
            target="preferences_page",
            delay_after=5,
        )

        nav_preferences_personal = DelayedTransition(
            transition_function=nav.navigate_preferences_personal,
            name="nav_preferences_personal",
            target="preferences_personal_page",
            delay_after=5,
        )

        set_preferences_personal = DelayedTransition(
            transition_function=actions.SetPersonalPreferences(
                full_name=f"{config.horde.first_name} {config.horde.last_name}"
            ),
            name="set_preferences_personal",
            target="selecting_menu",
            delay_after=5,
        )

        # states

        initial = states.ActivitySelectionState(
            name="selecting_activity",
            horde_transition=horde_transition,
            idle_transition=idle_transition,
        )

        login_check = states.LoggedInCheck(
            name="login_check",
            login_state="login_page",
            selecting_menu_state="selecting_menu",
        )

        login_page = states.LoginPage(
            name="login_page",
            login=login,
            fail_login=fail_login,
        )

        selecting_menu = states.SelectingMenu(
            name="selecting_menu",
            nav_mail=nav_mail_menu,
            nav_preferences=nav_preferences,
            ret_transition=pause_horde,
            nav_mail_weight=0.7,
            nav_preferences_weight=0.1,
            ret_weight=0.2,  # ToDo replace for now only this
        )

        logout_choice = states.LogoutChoice(
            name="logout?",
            logout=horde_logout,
        )

        mails_page = states.MailsPage(
            name="mails_page",
            view_mail=view_mail,
            new_mail=new_mail,
            refresh_mail=refresh_mail,
            ret_transition=return_select,
        )

        mail_view = states.MailView(
            name="mail_view",
            delete_mail=delete_mail,
            open_mail=open_mail,
            do_nothing=NoopTransition("do_nothing", target="mails_page"),
        )

        mail_info = states.MailInfo(
            name="mail_info",
            delete_mail=delete_mail,
            reply_mail=reply_mail,
        )

        mail_compose = states.ComposeMail(
            name="mail_compose",
            transition=send_mail,
        )

        preferences_page = states.PreferencesPage(
            name="preferences_page",
            transition=nav_preferences_personal,
        )

        preferences_personal_page = states.PreferencesPersonalPage(
            name="preferences_personal_page",
            transition=set_preferences_personal,
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
            ],
            selenium_config=config.selenium,
            start_time=config.start_time,
            end_time=config.end_time,
            work_schedule=config.schedule,
            max_errors=config.max_errors,
        )
