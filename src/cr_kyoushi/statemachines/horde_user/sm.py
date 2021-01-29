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

        # admin transitions

        nav_admin = DelayedTransition(
            transition_function=nav.navigate_admin_configuration,
            name="nav_admin",
            target="admin_page",
            delay_after=5,
        )

        nav_config = DelayedTransition(
            transition_function=nav.navigate_admin_configuration,
            name="nav_config",
            target="admin_config_page",
            delay_after=5,
        )

        check_versions = DelayedTransition(
            transition_function=actions.admin_check_versions,
            name="check_versions",
            target="admin_page",
            delay_after=5,
        )

        nav_groups = DelayedTransition(
            transition_function=nav.navigate_admin_groups,
            name="nav_groups",
            target="admin_groups_page",
            delay_after=5,
        )

        group_add = DelayedTransition(
            transition_function=actions.add_user_group,
            name="group_add",
            target="admin_group_added",
            delay_after=5,
        )

        group_delete = DelayedTransition(
            transition_function=actions.delete_user_group,
            name="group_delete",
            target="admin_group_deleting",
            delay_after=5,
        )

        group_delete_confirm = DelayedTransition(
            transition_function=actions.confirm_delete_user_group,
            name="group_delete_confirm",
            target="admin_groups_page",
            delay_after=5,
        )

        nav_users = DelayedTransition(
            transition_function=nav.navigate_admin_users,
            name="nav_users",
            target="admin_page",
            delay_after=5,
        )

        nav_sessions = DelayedTransition(
            transition_function=nav.navigate_admin_sessions,
            name="nav_sessions",
            target="admin_page",
            delay_after=5,
        )

        nav_alarms = DelayedTransition(
            transition_function=nav.navigate_admin_alarms,
            name="nav_alarms",
            target="admin_page",
            delay_after=5,
        )

        nav_locks = DelayedTransition(
            transition_function=nav.navigate_admin_locks,
            name="nav_locks",
            target="admin_page",
            delay_after=5,
        )

        nav_permissions = DelayedTransition(
            transition_function=nav.navigate_admin_permissions,
            name="nav_permissions",
            target="admin_page",
            delay_after=5,
        )

        nav_php_shell = DelayedTransition(
            transition_function=nav.navigate_admin_php_shell,
            name="nav_php_shell",
            target="admin_php_shell_page",
            delay_after=5,
        )

        exec_php = DelayedTransition(
            transition_function=actions.admin_exec_php,
            name="exec_php",
            target="admin_page",
            delay_after=5,
        )

        nav_sql_shell = DelayedTransition(
            transition_function=nav.navigate_admin_sql_shell,
            name="nav_sql_shell",
            target="admin_sql_shell_page",
            delay_after=5,
        )

        exec_sql = DelayedTransition(
            transition_function=actions.admin_exec_sql,
            name="exec_sql",
            target="admin_page",
            delay_after=5,
        )

        nav_cli_shell = DelayedTransition(
            transition_function=nav.navigate_admin_cli,
            name="nav_cli_shell",
            target="admin_cli_shell_page",
            delay_after=5,
        )

        exec_cli = DelayedTransition(
            transition_function=actions.admin_exec_cli,
            name="exec_cli",
            target="admin_page",
            delay_after=5,
        )

        # notes transitions

        nav_notes = DelayedTransition(
            transition_function=nav.navigate_notes_menu,
            name="nav_notes",
            target="notes_page",
            delay_after=5,
        )

        new_note = DelayedTransition(
            transition_function=actions.new_note,
            name="new_note",
            target="note_creator",
            delay_after=5,
        )

        write_note = DelayedTransition(
            transition_function=actions.write_note,
            name="write_note",
            target="notes_page",
            delay_after=5,
        )

        edit_note = DelayedTransition(
            transition_function=actions.edit_note,
            name="edit_note",
            target="note_editor",
            delay_after=5,
        )

        delete_note = DelayedTransition(
            transition_function=actions.delete_note,
            name="delete_note",
            target="notes_page",
            delay_after=5,
        )

        # tasks transitions

        nav_tasks = DelayedTransition(
            transition_function=nav.navigate_tasks_menu,
            name="nav_tasks",
            target="tasks_page",
            delay_after=5,
        )

        new_task = DelayedTransition(
            transition_function=actions.new_task,
            name="new_task",
            target="task_creator",
            delay_after=5,
        )

        save_task = DelayedTransition(
            transition_function=actions.save_new_task,
            name="save_task",
            target="tasks_page",
            delay_after=5,
        )

        edit_task = DelayedTransition(
            transition_function=actions.edit_task,
            name="edit_task",
            target="task_editor",
            delay_after=5,
        )

        delete_task = DelayedTransition(
            transition_function=actions.delete_task,
            name="delete_task",
            target="tasks_page",
            delay_after=5,
        )

        # address book transitions

        nav_address_book = DelayedTransition(
            transition_function=nav.navigate_address_book_menu,
            name="nav_address_book",
            target="address_book_page",
            delay_after=5,
        )

        new_contact = DelayedTransition(
            transition_function=actions.start_add_contact,
            name="new_contact",
            target="contact_compose",
            delay_after=5,
        )

        submit_contact = DelayedTransition(
            transition_function=actions.submit_new_contact,
            name="submit_contact",
            target="address_book_page",
            delay_after=5,
        )

        nav_contacts_browse = DelayedTransition(
            transition_function=nav.navigate_address_book_browse,
            name="nav_contacts_browse",
            target="contacts_browser",
            delay_after=5,
        )

        contacts_do_nothing = DelayedTransition(
            transition_function=nav.navigate_address_book_menu,
            name="do_nothing",
            target="address_book_page",
            delay_after=5,
        )

        view_contact = DelayedTransition(
            transition_function=nav.navigate_address_book_contact,
            name="view_contact",
            target="contact_info",
            delay_after=5,
        )

        delete_contact = DelayedTransition(
            transition_function=actions.delete_contact,
            name="delete_contact",
            target="contact_delete_confirming",
            delay_after=5,
        )

        delete_contact_confirm = DelayedTransition(
            transition_function=actions.confirm_delete_contact,
            name="delete_contact_confirm",
            target="address_book_page",
            delay_after=5,
        )

        # calendar transitions

        nav_calendar = DelayedTransition(
            transition_function=nav.navigate_calendar_menu,
            name="nav_calendar",
            target="calendar_page",
            delay_after=5,
        )

        new_event = DelayedTransition(
            transition_function=actions.new_calendar_event,
            name="new_event",
            target="event_compose",
            delay_after=5,
        )

        write_event = DelayedTransition(
            transition_function=actions.write_calendar_event,
            name="write_event",
            target="calendar_page",
            delay_after=5,
        )

        edit_event = DelayedTransition(
            transition_function=actions.edit_calendar_event,
            name="edit_event",
            target="event_edit",
            delay_after=5,
        )

        delete_event = DelayedTransition(
            transition_function=actions.delete_calendar_event,
            name="delete_event",
            target="calendar_page",
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
            nav_admin=nav_admin,
            nav_notes=nav_notes,
            nav_tasks=nav_tasks,
            nav_address_book=nav_address_book,
            nav_calendar=nav_calendar,
            ret_transition=pause_horde,
            # nav_mail_weight=0.0,
            # nav_preferences_weight=0.0,
            # nav_admin_weight=0.0,
            # nav_notes_weight=0.0,
            # nav_tasks_weight=0.8,
            # nav_address_book_weight=0.0,
            # nav_calendar_weight=0.0,
            # ret_weight=0.2,
        )

        logout_choice = states.LogoutChoice(
            name="logout?",
            logout=horde_logout,
        )

        # mail states

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

        # preferences states

        preferences_page = states.PreferencesPage(
            name="preferences_page",
            transition=nav_preferences_personal,
        )

        preferences_personal_page = states.PreferencesPersonalPage(
            name="preferences_personal_page",
            transition=set_preferences_personal,
        )

        # admin states

        admin_page = states.AdminPage(
            name="admin_page",
            nav_config=nav_config,
            nav_groups=nav_groups,
            nav_users=nav_users,
            nav_sessions=nav_sessions,
            nav_alarms=nav_alarms,
            nav_locks=nav_locks,
            nav_permissions=nav_permissions,
            nav_php_shell=nav_php_shell,
            nav_sql_shell=nav_sql_shell,
            nav_cli_shell=nav_cli_shell,
            ret_transition=return_select,
        )

        admin_config_page = states.AdminConfigPage(
            name="admin_config_page",
            transition=check_versions,
        )

        admin_groups_page = states.AdminGroupsPage(
            name="admin_groups_page",
            group_add=group_add,
            group_delete=group_delete,
            ret_transition=return_select,
        )

        admin_group_added = states.AdminGroupAdded(
            name="admin_group_added",
            transition=nav_groups,
        )

        admin_group_deleting = states.AdminGroupDeleting(
            name="admin_group_deleting",
            transition=group_delete_confirm,
        )

        admin_php_shell_page = states.AdminPHPShellPage(
            name="admin_php_shell_page",
            transition=exec_php,
        )

        admin_sql_shell_page = states.AdminSQLShellPage(
            name="admin_sql_shell_page",
            transition=exec_sql,
        )

        admin_cli_shell_page = states.AdminCLIShellPage(
            name="admin_cli_shell_page",
            transition=exec_cli,
        )

        # note states

        notes_page = states.NotesPage(
            name="notes_page",
            new_note=new_note,
            edit_note=edit_note,
            ret_transition=return_select,
        )

        note_creator = states.NoteCreator(
            name="note_creator",
            transition=write_note,
        )

        note_editor = states.NoteEditor(
            name="note_editor",
            write_note=write_note,
            delete_note=delete_note,
        )

        # task states

        tasks_page = states.TasksPage(
            name="tasks_page",
            new_task=new_task,
            edit_task=edit_task,
            ret_transition=return_select,
        )

        task_creator = states.TaskCreator(
            name="task_creator",
            transition=save_task,
        )

        task_editor = states.TaskEditor(
            name="task_editor",
            transition=delete_task,
        )

        # address book states

        address_book_page = states.AddressBookPage(
            name="address_book_page",
            new_contact=new_contact,
            browse_contacts=nav_contacts_browse,
            ret_transition=return_select,
        )

        contact_compose = states.ContactCompose(
            name="contact_compose",
            transition=submit_contact,
        )

        contacts_browser = states.ContactsBrowser(
            name="contacts_browser",
            new_contact=new_contact,
            view_contact=view_contact,
        )

        contact_info = states.ContactInfo(
            name="contact_info",
            delete_contact=delete_contact,
            do_nothing=contacts_do_nothing,
        )

        contact_delete_confirming = states.ContactDeleteConfirming(
            name="contact_delete_confirming",
            transition=delete_contact_confirm,
        )

        # calendar states

        calendar_page = states.CalendarPage(
            name="calendar_page",
            new_event=new_event,
            edit_event=edit_event,
            ret_transition=return_select,
        )

        event_compose = states.EventCompose(
            name="event_compose",
            transition=write_event,
        )

        event_edit = states.EventEdit(
            name="event_edit",
            write_event=write_event,
            delete_event=delete_event,
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
