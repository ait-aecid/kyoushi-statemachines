from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation import states
from cr_kyoushi.simulation.transitions import (
    NoopTransition,
    Transition,
)
from cr_kyoushi.simulation.util import now

from ..core.states import ActivityState
from .config import Context
from .wait import (
    check_login_page,
    check_mail_page,
)


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
        horde_weight: float = 0.8,
        idle_weight: float = 0.2,
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
    def __init__(
        self,
        name: str,
        login_state: str,
        selecting_menu_state: str,
    ):
        super().__init__(
            name,
            self.check_logged_in,
            yes=NoopTransition(name="logged_in_yes", target=selecting_menu_state),
            no=NoopTransition(name="logged_in_no", target=login_state),
        )

    def check_logged_in(self, log: BoundLogger, context: Context) -> bool:
        if check_login_page(context.driver):
            return False
        return True


class LoginPage(states.AdaptiveProbabilisticState):
    def __init__(
        self,
        name: str,
        login: Transition,
        fail_login: Transition,
        fail_weight: float = 0.05,
        fail_decrease_factor: float = 0.9,
    ):
        super().__init__(
            name=name,
            transitions=[login, fail_login],
            weights=[1 - fail_weight, fail_weight],
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
    def __init__(
        self,
        name: str,
        nav_mail: Transition,
        nav_preferences: Transition,
        nav_admin: Transition,
        nav_notes: Transition,
        ret_transition: Transition,
        nav_mail_weight: float = 0.5,
        nav_preferences_weight: float = 0.1,
        nav_admin_weight: float = 0,
        nav_notes_weight: float = 0.2,
        ret_weight: float = 0.2,
        ret_increase=1.2,
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
                ret_transition,
            ],
            ret_transition,
            [
                nav_mail_weight,
                nav_preferences_weight,
                nav_admin_weight,
                nav_notes_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
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
    def __init__(self, name: str, logout: Transition, logout_prob: float = 0.05):
        super().__init__(
            name,
            [
                logout,
                # if we do not log out we do nothing
                NoopTransition(name="background_horde", target=logout.target),
            ],
            [logout_prob, 1 - logout_prob],
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
    def __init__(
        self,
        name: str,
        delete_mail: Transition,
        open_mail: Transition,
        do_nothing: Transition,
        delete_mail_prob: float = 0.3,
        open_mail_prob: float = 0.4,
        do_nothing_prob: float = 0.3,
    ):

        super().__init__(
            name=name,
            transitions=[
                delete_mail,
                open_mail,
                do_nothing,
            ],
            weights=[
                delete_mail_prob,
                open_mail_prob,
                do_nothing_prob,
            ],
        )


class MailInfo(states.ProbabilisticState):
    def __init__(
        self,
        name: str,
        delete_mail: Transition,
        reply_mail: Transition,
        delete_mail_weight: float = 0.3,
        reply_mail_weight: float = 0.7,
    ):
        super().__init__(
            name=name,
            transitions=[delete_mail, reply_mail],
            weights=[delete_mail_weight, reply_mail_weight],
        )


ComposeMail = states.SequentialState

PreferencesPage = states.SequentialState

PreferencesPersonalPage = states.SequentialState


class AdminPage(ActivityState):
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
        )


AdminConfigPage = states.SequentialState


class AdminGroupsPage(ActivityState):
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

AdminGroupDeleting = states.SequentialState

AdminPHPShellPage = states.SequentialState

AdminSQLShellPage = states.SequentialState

AdminCLIShellPage = states.SequentialState


class NotesPage(ActivityState):
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
    ):
        super().__init__(
            name=name,
            transitions=[new_note, edit_note, ret_transition],
            ret_transition=ret_transition,
            weights=[new_note_weight, edit_note_weight, ret_weight],
            modifiers=None,
            ret_increase=ret_increase,
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


class NoteEditor(states.ProbabilisticState):
    def __init__(
        self,
        name: str,
        write_note: Transition,
        delete_note: Transition,
        write_note_weight: float = 0.6,
        delete_note_weight: float = 0.4,
    ):
        super().__init__(
            name,
            [write_note, delete_note],
            [write_note_weight, delete_note_weight],
        )


class TasksPage(ActivityState):
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
    ):
        super().__init__(
            name=name,
            transitions=[new_task, edit_task, ret_transition],
            ret_transition=ret_transition,
            weights=[new_task_weight, edit_task_weight, ret_weight],
            modifiers=None,
            ret_increase=ret_increase,
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

TaskEditor = states.SequentialState
