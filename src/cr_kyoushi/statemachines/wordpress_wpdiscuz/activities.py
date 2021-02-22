"""
A collection of helper functions used to create the various sub activities of the wordpress wpDiscuz user activity.
"""

from typing import (
    Optional,
    Tuple,
)

from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    NoopTransition,
    Transition,
)

from ..core.config import IdleConfig
from . import (
    actions,
    nav,
    states,
)
from .config import (
    CloseChoiceConfig,
    PostPageConfig,
    PostsPageConfig,
    WpDiscuzConfig,
)


def get_posts_activity(
    idle: IdleConfig,
    user_config: WpDiscuzConfig,
    posts_config: PostsPageConfig,
    close_config: CloseChoiceConfig,
    # states
    posts_page: str = "posts_page",
    post_page: str = "post_page",
    close_choice: str = "close_choice",
    root: str = "selecting_activity",
    # transitions
    goto_wordpress: str = "goto_wordpress",
    exit_wordpress: str = "exit_wordpress",
    leave_open: str = "leave_open",
    close: str = "close_wordpress",
    nav_older: str = "nav_older",
    nav_newer: str = "nav_newer",
    nav_post: str = "nav_post",
    name_prefix: Optional[str] = None,
) -> Tuple[Transition, states.PostsPage, states.CloseChoice]:
    """Creates the posts activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The goto_wordpress transition and the posts_page and close_choice states as tuple:
        `(goto_wordpress, posts_page, close_choice)`
    """
    if name_prefix:
        target_posts_page = f"{name_prefix}_{posts_page}"
        target_post_page = f"{name_prefix}_{post_page}"
        target_close_choice = f"{name_prefix}_{close_choice}"
    else:
        target_posts_page = posts_page
        target_post_page = post_page
        target_close_choice = close_choice

    t_goto_wordpress = DelayedTransition(
        nav.GoToWordpress(user_config.url, user_config.page_title),
        name=goto_wordpress,
        target=target_posts_page,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_exit_wordpress = NoopTransition(
        name=exit_wordpress,
        target=target_close_choice,
        name_prefix=name_prefix,
    )

    t_leave_open = NoopTransition(
        name=leave_open,
        target=root,
        name_prefix=name_prefix,
    )

    t_close_wordpress = Transition(
        nav.close_wordpress,
        name=close,
        target=root,
        name_prefix=name_prefix,
    )

    t_nav_older = DelayedTransition(
        nav.nav_posts_next,
        name=nav_older,
        target=target_posts_page,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_nav_newer = DelayedTransition(
        nav.nav_posts_previous,
        name=nav_newer,
        target=target_posts_page,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_nav_post = DelayedTransition(
        nav.nav_post,
        name=nav_post,
        target=target_post_page,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    # states

    s_posts_page = states.PostsPage(
        name=posts_page,
        nav_older=t_nav_older,
        nav_newer=t_nav_newer,
        nav_post=t_nav_post,
        ret_transition=t_exit_wordpress,
        nav_older_weight=posts_config.nav_older,
        nav_newer_weight=posts_config.nav_newer,
        nav_post_weight=posts_config.nav_post,
        ret_weight=posts_config.return_,
        ret_increase=posts_config.extra.return_increase,
        max_page=posts_config.extra.max_page,
        name_prefix=name_prefix,
    )

    s_close_choice = states.CloseChoice(
        name=close_choice,
        leave_open=t_leave_open,
        close=t_close_wordpress,
        leave_open_weight=close_config.leave_open,
        close_weight=close_config.close,
        name_prefix=name_prefix,
    )

    return (
        t_goto_wordpress,
        # states
        s_posts_page,
        s_close_choice,
    )


def get_post_activity(
    idle: IdleConfig,
    post_config: PostPageConfig,
    return_home: Transition,
    # states
    post_page: str = "post_page",
    comment_compose: str = "comment_compose",
    # transitions
    rate_post: str = "rate_post",
    down_vote: str = "down_vote_comment",
    up_vote: str = "up_vote_comment",
    comment: str = "new_comment",
    reply: str = "reply_to_comment",
    write_comment: str = "write_comment",
    name_prefix: Optional[str] = None,
) -> Tuple[states.PostPage, states.CommentCompose]:
    """Creates the post activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The the post_page and comment_compose states as tuple:
        `(post_page, comment_compose)`
    """

    if name_prefix:
        target_post_page = f"{name_prefix}_{post_page}"
        target_comment_compose = f"{name_prefix}_{comment_compose}"
    else:
        target_post_page = post_page
        target_comment_compose = comment_compose

    t_rate_post = DelayedTransition(
        actions.RatePost(
            min_rating=post_config.extra.min_rating,
            max_rating=post_config.extra.max_rating,
        ),
        name=rate_post,
        target=target_post_page,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_down_vote = DelayedTransition(
        actions.VoteComment(up_vote=False),
        name=down_vote,
        target=target_post_page,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_up_vote = DelayedTransition(
        actions.VoteComment(up_vote=True),
        name=up_vote,
        target=target_post_page,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_reply = DelayedTransition(
        actions.ReplyComment(max_level=post_config.extra.max_level),
        name=reply,
        target=target_comment_compose,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_comment = DelayedTransition(
        actions.new_comment,
        name=comment,
        target=target_comment_compose,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_write_comment = DelayedTransition(
        actions.write_comment,
        name=write_comment,
        target=target_post_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # states

    s_post_page = states.PostPage(
        name=post_page,
        rate_post=t_rate_post,
        down_vote=t_down_vote,
        up_vote=t_up_vote,
        comment=t_comment,
        reply=t_reply,
        ret_transition=return_home,
        rate_post_weight=post_config.rate_post,
        down_vote_weight=post_config.down_vote,
        up_vote_weight=post_config.up_vote,
        comment_weight=post_config.comment,
        reply_weight=post_config.reply,
        ret_weight=post_config.return_,
        ret_increase=post_config.extra.return_increase,
        comment_max_level=post_config.extra.max_level,
        name_prefix=name_prefix,
    )

    s_comment_compose = states.CommentCompose(
        name=comment_compose,
        transition=t_write_comment,
        name_prefix=name_prefix,
    )

    return (s_post_page, s_comment_compose)
