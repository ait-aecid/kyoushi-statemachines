from typing import Optional

from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation import states
from cr_kyoushi.simulation.transitions import (
    NoopTransition,
    Transition,
)
from cr_kyoushi.simulation.util import now

from ..core.states import ActivityState
from .context import Context
from .wait import (
    check_login_page,
    check_mail_page,
)


__all__ = [
    "ActivitySelectionState",
    "LoggedInCheck",
    "LoginPage",
    "SelectingMenu",
    "LogoutChoice",
    "MailsPage",
    "MailView",
    "MailInfo",
    "MailCompose",
    "PreferencesPage",
    "PreferencesPersonalPage",
    "AdminPage",
    "AdminGroupsPage",
    "AdminConfigPage",
    "AdminGroupAdded",
    "AdminGroupDeleting",
    "AdminPHPShellPage",
    "AdminSQLShellPage",
    "AdminCLIShellPage",
    "NotesPage",
    "NoteCreator",
    "NoteEditor",
    "TasksPage",
    "TaskCreator",
    "TaskEditor",
    "AddressBookPage",
    "ContactsBrowser",
    "ContactInfo",
    "ContactCompose",
    "ContactDeleteConfirming",
    "CalendarPage",
    "EventEdit",
    "EventCompose",
]


class ActivitySelectionState(states.AdaptiveProbabilisticState):
    """The main activity selection state for the horde user.

    This will decide between either entering the horde activity or idling.
    """

    def __init__(
        self,
        name: str,
        horde_transition: Transition,
        idle_transition: Transition,
        horde_max_daily: int = 10,
        horde_weight: float = 0.6,
        idle_weight: float = 0.4,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            horde_transition: The transition to enter the horde activity
            idle_transition: The idle transition
            horde_max_daily: The maximum amount of times to enter the horde activity per day.
            horde_weight: The propability of entering the horde activity.
            idle_weight: The propability of entering the idle activity.
        """
        super().__init__(
            name=name,
            transitions=[horde_transition, idle_transition],
            weights=[horde_weight, idle_weight],
            name_prefix=name_prefix,
        )
        self.__horde = horde_transition
        self.__horde_count = 0
        self.__horde_max = horde_max_daily
        self.__day = now().date()

    def adapt_before(self, log, context):
        """Sets the propability of entering the horde activity to 0 if the daylie maximum is reached"""
        super().adapt_before(log, context)

        # reset horde count and modifiers if we have a new day
        current_day = now().date()
        if self.__day != current_day:
            self.__day = current_day
            self.__horde_count = 0
            self.reset()

        # if we reached the horde limit set the transition probability to 0
        if self.__horde_count >= self.__horde_max:
            self._modifiers[self.__horde] = 0

    def adapt_after(self, log, context, selected):
        """Increases the horde activity enter count"""
        super().adapt_after(log, context, selected)

        # increase horde count if we selected the transition
        if selected == self.__horde:
            self.__horde_count += 1


class LoggedInCheck(states.ChoiceState):
    """Dummy state used to detect if the user is already logged in or not."""

    def __init__(
        self,
        name: str,
        login_state: str,
        selecting_menu_state: str,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            self.check_logged_in,
            yes=NoopTransition(
                name="logged_in_yes",
                target=selecting_menu_state,
                name_prefix=name_prefix,
            ),
            no=NoopTransition(
                name="logged_in_no", target=login_state, name_prefix=name_prefix
            ),
            name_prefix=name_prefix,
        )

    def check_logged_in(self, log: BoundLogger, context: Context) -> bool:
        if check_login_page(context.driver):
            return False
        return True


class LoginPage(states.AdaptiveProbabilisticState):
    """The horde login page state"""

    def __init__(
        self,
        name: str,
        login: Transition,
        fail_login: Transition,
        fail_weight: float = 0.05,
        fail_decrease_factor: float = 0.9,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[login, fail_login],
            weights=[1 - fail_weight, fail_weight],
            name_prefix=name_prefix,
        )
        self.__fail = fail_login
        self.__fail_decrease = fail_decrease_factor

    def adapt_after(self, log, context, selected):
        """Reduces the chance of a failing login after each fail"""
        super().adapt_after(log, context, selected)

        if selected == self.__fail:
            self._modifiers[self.__fail] *= self.__fail_decrease
        else:
            self.reset()


class SelectingMenu(ActivityState):
    """The horde selecting menu state.

    This is the main state used to switch between the various horde
    sub activities.
    """

    def __init__(
        self,
        name: str,
        nav_mail: Transition,
        nav_preferences: Transition,
        nav_admin: Transition,
        nav_notes: Transition,
        nav_tasks: Transition,
        nav_address_book: Transition,
        nav_calendar: Transition,
        ret_transition: Transition,
        nav_mail_weight: float = 0.3,
        nav_preferences_weight: float = 0.1,
        nav_admin_weight: float = 0,
        nav_notes_weight: float = 0.15,
        nav_tasks_weight: float = 0.1,
        nav_address_book_weight: float = 0.125,
        nav_calendar_weight: float = 0.15,
        ret_weight: float = 0.075,
        ret_increase=1.25,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            ret_transition: The return to parent activity transition
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
        """
        super().__init__(
            name,
            [
                nav_mail,
                nav_preferences,
                nav_admin,
                nav_notes,
                nav_tasks,
                nav_address_book,
                nav_calendar,
                ret_transition,
            ],
            ret_transition,
            [
                nav_mail_weight,
                nav_preferences_weight,
                nav_admin_weight,
                nav_notes_weight,
                nav_tasks_weight,
                nav_address_book_weight,
                nav_calendar_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self.__preferences = nav_preferences
        self.__set_preferences = False

    def adapt_before(self, log, context):
        super().adapt_before(log, context)
        if self.__set_preferences:
            self._modifiers[self.__preferences] = 0

    def adapt_after(self, log, context, selected):
        super().adapt_after(log, context, selected)
        # disable preferences page navigation after first time)
        if selected == self.__preferences:
            self.__set_preferences = True


class LogoutChoice(states.ProbabilisticState):
    """The horde logout choice state

    Used as a decision state to decide wether the user should logout
    of horde or simply leave it open in background when pausing the activity.
    """

    def __init__(
        self,
        name: str,
        logout: Transition,
        logout_prob: float = 0.05,
        background: str = "background",
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            [
                logout,
                # if we do not log out we do nothing
                NoopTransition(
                    name=background,
                    target=logout.target,
                    name_prefix=name_prefix,
                ),
            ],
            [logout_prob, 1 - logout_prob],
            name_prefix=name_prefix,
        )


class MailsPage(ActivityState):
    """The state controling the transitions when the user is on the mails page."""

    def __init__(
        self,
        name: str,
        view_mail: Transition,
        new_mail: Transition,
        refresh_mail: Transition,
        ret_transition: Transition,
        view_mail_weight: float = 0.45,
        new_mail_weight: float = 0.35,
        refresh_mail_weight: float = 0.1,
        ret_weight: float = 0.1,
        ret_increase=1.2,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            view_mail: The transition used to view an email on the page
            new_mail: The transition used to initiate writing a new email
            ret_transition: The return to parent activity transition
            view_mail_weight: The base weight of the view mail transition
            new_mail_weight: The base weight of the new mail transition
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
        """
        super().__init__(
            name,
            [view_mail, new_mail, refresh_mail, ret_transition],
            ret_transition,
            [view_mail_weight, new_mail_weight, refresh_mail_weight, ret_weight],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self.__view_mail = view_mail
        self.__new_mail = new_mail

    def adapt_before(self, log: BoundLogger, context: Context):
        """Checks if mails are present in the inbox and disables the view mail transition if not."""
        super().adapt_before(log, context)
        if check_mail_page(context.driver):
            mail_divs = context.driver.find_elements_by_css_selector("div[id^=VProw]")
            # if there are mail divs present then view_mail is active
            if len(mail_divs) > 0:
                self._modifiers[self.__view_mail] = 1
            # if there are not we disable it by setting its propability to 0
            else:
                self._modifiers[self.__view_mail] = 0
        else:
            log.error(
                "Invalid state for current page",
                current_page=context.driver.current_url,
            )
            # set all transitions but ret to 0
            # we try to by leaving this activity
            self._modifiers[self.__view_mail] = 0
            self._modifiers[self.__new_mail] = 0


class MailView(states.ProbabilisticState):
    """The horde mail view state"""

    def __init__(
        self,
        name: str,
        delete_mail: Transition,
        open_mail: Transition,
        do_nothing: Transition,
        delete_mail_weight: float = 0.3,
        open_mail_weight: float = 0.4,
        do_nothing_weight: float = 0.3,
        name_prefix: Optional[str] = None,
    ):

        super().__init__(
            name=name,
            transitions=[
                delete_mail,
                open_mail,
                do_nothing,
            ],
            weights=[
                delete_mail_weight,
                open_mail_weight,
                do_nothing_weight,
            ],
            name_prefix=name_prefix,
        )


class MailInfo(states.ProbabilisticState):
    """The horde mail info state"""

    def __init__(
        self,
        name: str,
        delete_mail: Transition,
        reply_mail: Transition,
        delete_mail_weight: float = 0.3,
        reply_mail_weight: float = 0.7,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[delete_mail, reply_mail],
            weights=[delete_mail_weight, reply_mail_weight],
            name_prefix=name_prefix,
        )


MailCompose = states.SequentialState
"""The horde mail compose state"""

PreferencesPage = states.SequentialState
"""The horde preferences page state"""

PreferencesPersonalPage = states.SequentialState
"""The horde preferences personal page state"""


class AdminPage(ActivityState):
    """The horde admin page state

    Used to control the selection of all admin sub activities.
    Similar to how the selecting menu state is used to switch between the
    higher level horder sub activities.
    """

    def __init__(
        self,
        name: str,
        nav_config: Transition,
        nav_groups: Transition,
        nav_users: Transition,
        nav_sessions: Transition,
        nav_alarms: Transition,
        nav_locks: Transition,
        nav_permissions: Transition,
        nav_php_shell: Transition,
        nav_sql_shell: Transition,
        nav_cli_shell: Transition,
        ret_transition: Transition,
        nav_config_weight: float = 0.15,
        nav_groups_weight: float = 0.15,
        nav_users_weight: float = 0.09,
        nav_sessions_weight: float = 0.09,
        nav_alarms_weight: float = 0.09,
        nav_locks_weight: float = 0.09,
        nav_permissions_weight: float = 0.09,
        nav_php_shell_weight: float = 0.05,
        nav_sql_shell_weight: float = 0.05,
        nav_cli_shell_weight: float = 0.05,
        ret_weight: float = 0.1,
        ret_increase=2,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[
                nav_config,
                nav_groups,
                nav_users,
                nav_sessions,
                nav_alarms,
                nav_locks,
                nav_permissions,
                nav_php_shell,
                nav_sql_shell,
                nav_cli_shell,
                ret_transition,
            ],
            ret_transition=ret_transition,
            weights=[
                nav_config_weight,
                nav_groups_weight,
                nav_users_weight,
                nav_sessions_weight,
                nav_alarms_weight,
                nav_locks_weight,
                nav_permissions_weight,
                nav_php_shell_weight,
                nav_sql_shell_weight,
                nav_cli_shell_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )


AdminConfigPage = states.SequentialState


class AdminGroupsPage(ActivityState):
    """The horde admin groups page state"""

    def __init__(
        self,
        name: str,
        group_add: Transition,
        group_delete: Transition,
        ret_transition: Transition,
        group_add_weight: float = 0.45,
        group_delete_weight: float = 0.35,
        ret_weight: float = 0.2,
        ret_increase=2,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            transitions=[
                group_add,
                group_delete,
                ret_transition,
            ],
            ret_transition=ret_transition,
            weights=[
                group_add_weight,
                group_delete_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self.__group_delete = group_delete

    def adapt_before(self, log, context):
        super().adapt_before(log, context)
        groups = context.driver.find_elements_by_xpath(
            "//div[@id='admin_groups']/div[contains(@class,'horde-tree-row')]"
        )
        # if there are no groups we have nothing to delete
        if len(groups) > 0:
            self._modifiers[self.__group_delete] = 1
        else:
            self._modifiers[self.__group_delete] = 0


AdminGroupAdded = states.SequentialState
"""The horde group added state"""

AdminGroupDeleting = states.SequentialState
"""The horde admin group deleting state"""

AdminPHPShellPage = states.SequentialState
"""The horde php shell page state"""

AdminSQLShellPage = states.SequentialState
"""The horde sql shell state"""

AdminCLIShellPage = states.SequentialState
"""The horde cli shell state"""


class NotesPage(ActivityState):
    """The horde notes page state"""

    def __init__(
        self,
        name: str,
        new_note: Transition,
        edit_note: Transition,
        ret_transition: Transition,
        new_note_weight: float = 0.5,
        edit_note_weight: float = 0.4,
        ret_weight: float = 0.1,
        ret_increase=2,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[new_note, edit_note, ret_transition],
            ret_transition=ret_transition,
            weights=[new_note_weight, edit_note_weight, ret_weight],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self.__edit_note = edit_note

    def adapt_before(self, log, context):
        super().adapt_before(log, context)
        memos = context.driver.find_elements_by_xpath(
            "//tbody[@id='notes_body']//a[contains(@title,'Edit')]"
        )
        if len(memos) > 0:
            self._modifiers[self.__edit_note] = 1
        else:
            self._modifiers[self.__edit_note] = 0


NoteCreator = states.SequentialState
"""The horde note creator state"""


class NoteEditor(states.ProbabilisticState):
    """The horde note editor state"""

    def __init__(
        self,
        name: str,
        write_note: Transition,
        delete_note: Transition,
        write_note_weight: float = 0.6,
        delete_note_weight: float = 0.4,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            [write_note, delete_note],
            [write_note_weight, delete_note_weight],
            name_prefix=name_prefix,
        )


class TasksPage(ActivityState):
    """The horde tasks page state"""

    def __init__(
        self,
        name: str,
        new_task: Transition,
        edit_task: Transition,
        ret_transition: Transition,
        new_task_weight: float = 0.5,
        edit_task_weight: float = 0.4,
        ret_weight: float = 0.1,
        ret_increase=1.4,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[new_task, edit_task, ret_transition],
            ret_transition=ret_transition,
            weights=[new_task_weight, edit_task_weight, ret_weight],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self.__edit_task = edit_task

    def adapt_before(self, log, context):
        super().adapt_before(log, context)
        tasks = context.driver.find_elements_by_xpath(
            "//tbody[@id='tasks-body']//a[contains(@title,'Edit')]"
        )
        if len(tasks) > 0:
            self._modifiers[self.__edit_task] = 1
        else:
            self._modifiers[self.__edit_task] = 0


TaskCreator = states.SequentialState
"""The horde task creator state"""

TaskEditor = states.SequentialState
"""The horde task editor state"""


class AddressBookPage(ActivityState):
    """The horde address book page state"""

    def __init__(
        self,
        name: str,
        new_contact: Transition,
        browse_contacts: Transition,
        ret_transition: Transition,
        new_contact_weight: float = 0.2,
        browse_contacts_weight: float = 0.675,
        ret_transition_weight: float = 0.125,
        ret_increase=1.4,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[
                new_contact,
                browse_contacts,
                ret_transition,
            ],
            ret_transition=ret_transition,
            weights=[
                new_contact_weight,
                browse_contacts_weight,
                ret_transition_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )


class ContactsBrowser(states.AdaptiveProbabilisticState):
    """The horde contacts browser state"""

    def __init__(
        self,
        name: str,
        new_contact: Transition,
        view_contact: Transition,
        new_contact_weight: float = 0.35,
        view_contact_weight: float = 0.65,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[new_contact, view_contact],
            weights=[new_contact_weight, view_contact_weight],
            name_prefix=name_prefix,
        )
        self.__view_contact = view_contact

    def adapt_before(self, log, context):
        super().adapt_before(log, context)
        contacts = context.driver.find_elements_by_css_selector(
            'a[href^="/turba/contact.php"]'
        )
        if len(contacts) > 0:
            self._modifiers[self.__view_contact] = 1
        else:
            self._modifiers[self.__view_contact] = 0


ContactCompose = states.SequentialState
"""The horde contact compose state"""


class ContactInfo(states.ProbabilisticState):
    """The horde contact info state"""

    def __init__(
        self,
        name: str,
        delete_contact: Transition,
        do_nothing: Transition,
        delete_contact_weight: float = 0.4,
        do_nothing_weight: float = 0.6,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[delete_contact, do_nothing],
            weights=[delete_contact_weight, do_nothing_weight],
            name_prefix=name_prefix,
        )


ContactDeleteConfirming = states.SequentialState
"""The horde contact delete confirming state"""


class CalendarPage(ActivityState):
    """The horde calendar page state"""

    def __init__(
        self,
        name: str,
        new_event: Transition,
        edit_event: Transition,
        ret_transition: Transition,
        new_event_weight: float = 0.4,
        edit_event_weight: float = 0.35,
        ret_weight: float = 0.25,
        ret_increase=2,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[new_event, edit_event, ret_transition],
            ret_transition=ret_transition,
            weights=[new_event_weight, edit_event_weight, ret_weight],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self.__edit_event = edit_event

    def adapt_before(self, log, context):
        super().adapt_before(log, context)
        events = context.driver.find_elements_by_css_selector(
            "div[id^=kronolithEventmonth]"
        )
        if len(events) > 0:
            self._modifiers[self.__edit_event] = 1
        else:
            self._modifiers[self.__edit_event] = 0


EventCompose = states.SequentialState
"""The horde event compose state"""


class EventEdit(states.ProbabilisticState):
    """The horde event edit state"""

    def __init__(
        self,
        name: str,
        write_event: Transition,
        delete_event: Transition,
        write_event_weight: float = 0.6,
        delete_event_weight: float = 0.4,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            [write_event, delete_event],
            [write_event_weight, delete_event_weight],
            name_prefix=name_prefix,
        )
