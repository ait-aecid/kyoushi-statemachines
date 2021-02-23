from typing import Optional

from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation import states
from cr_kyoushi.simulation.transitions import Transition
from cr_kyoushi.simulation.util import now

from ..core.states import ActivityState
from .actions import get_comments
from .context import Context
from .wait import (
    check_post_rated,
    check_posts_can_next,
    check_posts_can_previous,
)


class ActivitySelectionState(states.AdaptiveProbabilisticState):
    """The main activity selection state for the wpdiscuz user.

    This will decide between either entering the wpdiscuz activity or idling.
    """

    def __init__(
        self,
        name: str,
        wpdiscuz_transition: Transition,
        idle_transition: Transition,
        wpdiscuz_max_daily: int = 10,
        wpdiscuz_weight: float = 0.6,
        idle_weight: float = 0.4,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            wpdiscuz_transition: The transition to enter the wpdiscuz activity
            idle_transition: The idle transition
            wpdiscuz_max_daily: The maximum amount of times to enter the wpdiscuz activity per day.
            wpdiscuz_weight: The propability of entering the wpdiscuz activity.
            idle_weight: The propability of entering the idle activity.
        """
        super().__init__(
            name=name,
            transitions=[wpdiscuz_transition, idle_transition],
            weights=[wpdiscuz_weight, idle_weight],
            name_prefix=name_prefix,
        )
        self.__wpdiscuz = wpdiscuz_transition
        self.__wpdiscuz_count = 0
        self.__wpdiscuz_max = wpdiscuz_max_daily
        self.__day = now().date()

    def adapt_before(self, log: BoundLogger, context: Context):
        """Sets the propability of entering the wpdiscuz activity to 0 if the daylie maximum is reached"""
        super().adapt_before(log, context)

        # reset wpdiscuz count and modifiers if we have a new day
        current_day = now().date()
        if self.__day != current_day:
            self.__day = current_day
            self.__wpdiscuz_count = 0
            self.reset()

        # if we reached the wpdiscuz limit set the transition probability to 0
        if self.__wpdiscuz_count >= self.__wpdiscuz_max:
            self._modifiers[self.__wpdiscuz] = 0

    def adapt_after(self, log, context, selected):
        """Increases the wpdiscuz activity enter count"""
        super().adapt_after(log, context, selected)

        # increase wpdiscuz count if we selected the transition
        if selected == self.__wpdiscuz:
            self.__wpdiscuz_count += 1


class PostsPage(ActivityState):
    """The posts page state"""

    def __init__(
        self,
        name: str,
        nav_older: Transition,
        nav_newer: Transition,
        nav_post: Transition,
        ret_transition: Transition,
        nav_older_weight: float = 0.15,
        nav_newer_weight: float = 0.25,
        nav_post_weight: float = 0.35,
        ret_weight: float = 0.25,
        ret_increase: float = 1.5,
        max_page: int = 3,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            transitions=[nav_older, nav_newer, nav_post, ret_transition],
            ret_transition=ret_transition,
            weights=[nav_older_weight, nav_newer_weight, nav_post_weight, ret_weight],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self._next: Transition = nav_older
        self._previous: Transition = nav_newer
        self._post: Transition = nav_post
        self._max_page: int = max_page

    def adapt_before(self, log: BoundLogger, context: Context):
        super().adapt_before(log, context)

        if (
            # enable/disable next depending on if we are already
            # on the maximum allowed page
            context.wpdiscuz.posts_page < self._max_page
            # or if there is no next button
            and check_posts_can_next(context.driver)
        ):
            self._modifiers[self._next] = 1
        else:
            self._modifiers[self._next] = 0

        # enable/disable previous if there is not previous button
        if check_posts_can_previous(context.driver):
            self._modifiers[self._previous] = 1
        else:
            self._modifiers[self._previous] = 0

        # enable/disable post nav depending on if there are posts
        posts = context.driver.find_elements_by_xpath(
            "//main[@class='site-content']/article"
        )
        if len(posts) > 0:
            self._modifiers[self._post] = 1
        else:
            self._modifiers[self._post] = 0


class CloseChoice(states.ProbabilisticState):
    """Close wordpress decision state

    Used for randomly deciding if the wordpress page gets closed
    or left open in the background.
    """

    def __init__(
        self,
        name: str,
        leave_open: Transition,
        close: Transition,
        leave_open_weight: float = 0.6,
        close_weight: float = 0.4,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            [leave_open, close],
            [leave_open_weight, close_weight],
            name_prefix=name_prefix,
        )


class PostPage(ActivityState):
    """Post page state

    Controls the action a user taks when they have opend a post.
    """

    def __init__(
        self,
        name: str,
        rate_post: Transition,
        down_vote: Transition,
        up_vote: Transition,
        comment: Transition,
        reply: Transition,
        ret_transition: Transition,
        rate_post_weight: float = 0.1,
        down_vote_weight: float = 0.1,
        up_vote_weight: float = 0.15,
        comment_weight: float = 0.25,
        reply_weight: float = 0.2,
        ret_weight: float = 0.2,
        ret_increase: float = 1.5,
        comment_max_level: int = 3,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            transitions=[
                rate_post,
                down_vote,
                up_vote,
                comment,
                reply,
                ret_transition,
            ],
            ret_transition=ret_transition,
            weights=[
                rate_post_weight,
                down_vote_weight,
                up_vote_weight,
                comment_weight,
                reply_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self._up_vote: Transition = up_vote
        self._down_vote: Transition = down_vote
        self._rate: Transition = rate_post
        self._reply: Transition = reply
        self._max_level: int = comment_max_level

    def adapt_before(self, log: BoundLogger, context: Context):
        super().adapt_before(log, context)

        # enable/disable voting depending on if there are comments
        # not by the author
        vote_comments = get_comments(context.driver, context.wpdiscuz.author)
        if len(vote_comments) > 0:
            self._modifiers[self._up_vote] = 1
            self._modifiers[self._down_vote] = 1
        else:
            self._modifiers[self._up_vote] = 0
            self._modifiers[self._down_vote] = 0

        # enabled/disable rating depending on if the post is already rated
        if not check_post_rated(context.driver):
            self._modifiers[self._rate] = 1
        else:
            self._modifiers[self._rate] = 0

        # enable/disable voting depending on if there are comments
        # not by the author not deeper than the max level
        reply_comments = get_comments(
            context.driver,
            context.wpdiscuz.author,
            self._max_level,
        )
        if len(reply_comments) > 0:
            self._modifiers[self._reply] = 1
        else:
            self._modifiers[self._reply] = 0


CommentCompose = states.SequentialState
"""Comment compose state"""
