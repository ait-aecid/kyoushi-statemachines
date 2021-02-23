from typing import (
    List,
    Optional,
)

from selenium.webdriver.remote.webelement import WebElement
from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation import states
from cr_kyoushi.simulation.transitions import (
    NoopTransition,
    Transition,
)
from cr_kyoushi.simulation.util import now

from ..core.states import ActivityState
from .actions import get_comments_by_others
from .context import Context
from .wait import check_login_page


class ActivitySelectionState(states.AdaptiveProbabilisticState):
    """The main activity selection state for the wordpress editor user.

    This will decide between either entering the wordpress editor activity or idling.
    """

    def __init__(
        self,
        name: str,
        wp_editor_transition: Transition,
        idle_transition: Transition,
        wp_editor_max_daily: int = 10,
        wp_editor_weight: float = 0.6,
        idle_weight: float = 0.4,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            wp_editor_transition: The transition to enter the wordpress editor activity
            idle_transition: The idle transition
            wp_editor_max_daily: The maximum amount of times to enter the wordpress editor activity per day.
            wp_editor_weight: The propability of entering the wordpress editor activity.
            idle_weight: The propability of entering the idle activity.
        """
        super().__init__(
            name=name,
            transitions=[wp_editor_transition, idle_transition],
            weights=[wp_editor_weight, idle_weight],
            name_prefix=name_prefix,
        )
        self.__wp_editor = wp_editor_transition
        self.__wp_editor_count = 0
        self.__wp_editor_max = wp_editor_max_daily
        self.__day = now().date()

    def adapt_before(self, log: BoundLogger, context: Context):
        """Sets the propability of entering the wordpress editor activity to 0 if the daylie maximum is reached"""
        super().adapt_before(log, context)

        # reset wp_editor count and modifiers if we have a new day
        current_day = now().date()
        if self.__day != current_day:
            self.__day = current_day
            self.__wp_editor_count = 0
            self.reset()

        # if we reached the wp_editor limit set the transition probability to 0
        if self.__wp_editor_count >= self.__wp_editor_max:
            self._modifiers[self.__wp_editor] = 0

    def adapt_after(self, log, context, selected):
        """Increases the wordpress editor activity enter count"""
        super().adapt_after(log, context, selected)

        # increase wp_editor count if we selected the transition
        if selected == self.__wp_editor:
            self.__wp_editor_count += 1


class LoggedInCheck(states.ChoiceState):
    """Dummy state used to detect if the user is already logged in or not."""

    def __init__(
        self,
        name: str,
        login_page: str,
        selecting_menu: str,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name to assign to this state
            login_page: The name of the login page state
            selecting_menu: The name of the selecting menu state
        """
        super().__init__(
            name,
            self.check_logged_in,
            yes=NoopTransition(
                name="logged_in_yes",
                target=selecting_menu,
                name_prefix=name_prefix,
            ),
            no=NoopTransition(
                name="logged_in_no",
                target=login_page,
                name_prefix=name_prefix,
            ),
            name_prefix=name_prefix,
        )

    def check_logged_in(self, log: BoundLogger, context: Context) -> bool:
        if check_login_page(context.driver):
            return False
        return True


class LoginPage(states.AdaptiveProbabilisticState):
    """The wordpress wp-admin login page state"""

    def __init__(
        self,
        name: str,
        login: Transition,
        fail_login: Transition,
        fail_weight: float = 0.05,
        fail_decrease_factor: float = 0.9,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name to assign to this state
            login: The login transition
            fail_login: The fail login transition
            fail_weight: The chance a failing login attemt will be executed.
            fail_decrease_factor: The factor the fail chance is decreased with each consecutive fail.
        """
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


class LogoutChoice(states.ProbabilisticState):
    """The wordpress editor logout choice state

    Used as a decision state to decide wether the user should logout
    of wordpress or simply leave it open in background when pausing the activity.
    """

    def __init__(
        self,
        name: str,
        logout: Transition,
        close: str = "close",
        logout_prob: float = 0.05,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name to assign to the state
            logout: The wordpress logout transition
            background: The name to use for the background transition
            logout_prob: The chance the user will logout of wordpress
        """
        super().__init__(
            name,
            [
                logout,
                # if we do not log out we do nothing
                NoopTransition(
                    name=close,
                    target=logout.target,
                    name_prefix=name_prefix,
                ),
            ],
            [logout_prob, 1 - logout_prob],
            name_prefix=name_prefix,
        )


class SelectingMenu(ActivityState):
    """The wordpress editor selecting menu state.

    This is the main state used to switch between the various wordpress editor
    menus and sub activities.
    """

    def __init__(
        self,
        name: str,
        nav_dashboard: Transition,
        nav_comments: Transition,
        nav_media: Transition,
        nav_posts: Transition,
        ret_transition: Transition,
        nav_dashboard_weight: float = 0.15,
        nav_comments_weight: float = 0.25,
        nav_media_weight: float = 0.15,
        nav_posts_weight: float = 0.3,
        ret_weight: float = 0.15,
        ret_increase=1.25,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name that will be assigned to the state
            nav_dashboard: The dashboard navigation transition
            nav_comments: The comments navigation transition
            nav_media: The media navigation transition
            nav_posts: The posts navigation transition
            ret_transition: The return to parent activity transition
            nav_dashboard_weight: The chance the user will go to the dashboard
            nav_comments_weight The chance the user will go to the comments
            nav_media_weight The chance the user will go to the media
            nav_posts_weight The chance the user will go to the posts
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
        """
        super().__init__(
            name,
            [
                nav_dashboard,
                nav_comments,
                nav_media,
                nav_posts,
                ret_transition,
            ],
            ret_transition,
            [
                nav_dashboard_weight,
                nav_comments_weight,
                nav_media_weight,
                nav_posts_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )


class CommentsPage(ActivityState):
    """The wordpress editor comments page it is possible to reply to comments from here."""

    def __init__(
        self,
        name: str,
        new_reply: Transition,
        ret_transition: Transition,
        username: str,
        new_reply_weight: float = 0.45,
        ret_weight: float = 0.55,
        ret_increase=1.25,
        reply_only_guests: bool = True,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name to assign to the state
            new_reply: The reply to comment transition
            ret_transition: The return to parent activity transition
            username: The username of the wordpress user
            new_reply_weight: The chance the user will reply to a random comment
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
            reply_only_guests: If only comments by guests should be replied to or not
        """
        super().__init__(
            name,
            [
                new_reply,
                ret_transition,
            ],
            ret_transition,
            [
                new_reply_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self._reply: Transition = new_reply
        self.only_guests: bool = reply_only_guests
        self.username: str = username

    def adapt_before(self, log, context):
        super().adapt_before(log, context)

        comments: List[WebElement] = get_comments_by_others(
            context.driver, self.username, self.only_guests
        )

        # enable/disable replying depending on if there are comments to reply to
        # and max comments has not been reach yet
        self._modifiers[self._reply] = 1 if len(comments) > 0 else 0


ReplyEditor = states.SequentialState


class PostsPage(ActivityState):
    """The posts page state"""

    def __init__(
        self,
        name: str,
        new_post: Transition,
        ret_transition: Transition,
        new_post_weight: float = 0.5,
        ret_weight: float = 0.5,
        ret_increase=1.25,
        max_posts_daily: int = 1,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name that will be assigned to the state
            new_post: The start writing new post transition
            ret_transition:
            new_post_weight The chance the user will post a new article
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
            max_posts_daily: The maximum number of posts a user will make per day
        """
        super().__init__(
            name,
            [
                new_post,
                ret_transition,
            ],
            ret_transition,
            [
                new_post_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self._post: Transition = new_post
        self.__post_count: int = 0
        self.__max_posts: int = max_posts_daily
        self.__day = now().date()

    def adapt_before(self, log, context):
        super().adapt_before(log, context)

        # reset post count if we have a new day
        current_day = now().date()
        if self.__day != current_day:
            self.__day = current_day
            self.__post_count = 0

        # if we reached the post limit set the transition probability to 0
        self._modifiers[self._post] = 0 if self.__post_count >= self.__max_posts else 1

    def adapt_after(self, log, context, selected):
        """Increases the post count"""
        super().adapt_after(log, context, selected)

        # increase post count if we selected the transition
        if selected == self._post:
            self.__post_count += 1


PostEditor = states.SequentialState

PostPublishing = states.SequentialState

PostPublished = states.SequentialState
