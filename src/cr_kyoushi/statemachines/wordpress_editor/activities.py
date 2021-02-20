"""
A collection of helper functions used to create the various sub activities of the wordpress editor user activity.
"""

from typing import (
    Optional,
    Tuple,
)

from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    NoopTransition,
    Transition,
    noop,
)

from ..core.config import IdleConfig
from . import (
    actions,
    nav,
    states,
)
from .config import (
    CommentsPageConfig,
    LoginPageConfig,
    LogoutChoiceConfig,
    PostsPageConfig,
    SelectingMenuConfig,
    WordpressEditorConfig,
)


def get_base_activity(
    idle: IdleConfig,
    user_config: WordpressEditorConfig,
    login_config: LoginPageConfig,
    logout_config: LogoutChoiceConfig,
    # states
    login_check: str = "login_check",
    login_page: str = "login_page",
    selecting_menu: str = "selecting_menu",
    logout_choice: str = "logout?",
    root: str = "selecting_activity",
    # transitions
    wordpress_editor: str = "goto_wp_admin",
    login: str = "login",
    fail_login: str = "fail_login",
    pause_wordpress: str = "pause_wordpress",
    logout: str = "logout",
    close: str = "close",
    name_prefix: Optional[str] = None,
) -> Tuple[
    Transition,
    Transition,
    states.LoggedInCheck,
    states.LoginPage,
    states.LogoutChoice,
]:
    """Creates the wordpress editor base activity (i.e., login and logout) and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The goto wp admin and pause transitions and the login/logout states as tuple of form:
        (goto_wp_admin, pause_wordpress, logged_in_check, login_page, logout_choice)
    """

    if name_prefix:
        target_login_check = f"{name_prefix}_{login_check}"
        target_login_page = f"{name_prefix}_{login_page}"
        target_selecting_menu = f"{name_prefix}_{selecting_menu}"
        target_logout_choice = f"{name_prefix}_{logout_choice}"
    else:
        target_login_check = login_check
        target_login_page = login_page
        target_selecting_menu = selecting_menu
        target_logout_choice = logout_choice

    t_goto_wp_admin = Transition(
        nav.GoToWordpressAdmin(user_config.url),
        name=wordpress_editor,
        target=target_login_check,
        name_prefix=name_prefix,
    )

    t_fail_login = DelayedTransition(
        actions.fail_login_to_wordpress,
        name=fail_login,
        target=target_login_page,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_login = DelayedTransition(
        actions.login_to_wordpress,
        name=login,
        target=target_selecting_menu,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_pause = NoopTransition(
        name=pause_wordpress,
        target=target_logout_choice,
        name_prefix=name_prefix,
    )

    t_logout = DelayedTransition(
        actions.logout_of_wordpress,
        name=logout,
        target=root,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    s_login_check = states.LoggedInCheck(
        name=login_check,
        login_page=target_login_page,
        selecting_menu=target_selecting_menu,
        name_prefix=name_prefix,
    )

    s_login_page = states.LoginPage(
        name=login_page,
        login=t_login,
        fail_login=t_fail_login,
        fail_weight=login_config.fail_chance,
        fail_decrease_factor=login_config.fail_decrease,
        name_prefix=name_prefix,
    )

    s_logout_choice = states.LogoutChoice(
        name=logout_choice,
        logout=t_logout,
        close=close,
        logout_prob=logout_config.logout_chance,
        name_prefix=name_prefix,
    )

    return (t_goto_wp_admin, t_pause, s_login_check, s_login_page, s_logout_choice)


def get_editor_activity(
    idle: IdleConfig,
    user_config: WordpressEditorConfig,
    menu_config: SelectingMenuConfig,
    comments_config: CommentsPageConfig,
    posts_config: PostsPageConfig,
    pause_wordpress: Transition,
    # states
    selecting_menu: str = "selecting_menu",
    comments_page: str = "comments_page",
    reply_editor: str = "reply_editor",
    posts_page: str = "posts_page",
    post_editor: str = "post_editor",
    post_publishing: str = "post_publishing",
    post_published: str = "post_published",
    # transitions
    do_nothing: str = "do_nothing",
    nav_dashboard: str = "nav_dashboard",
    nav_comments: str = "nav_comments",
    new_reply: str = "new_reply",
    write_reply: str = "write_reply",
    nav_media: str = "nav_media",
    nav_posts: str = "nav_posts",
    new_post: str = "new_post",
    write_post: str = "write_post",
    publish_post: str = "publish_post",
    nav_posts_home: str = "nav_posts_home",
    name_prefix: Optional[str] = None,
) -> Tuple[
    states.SelectingMenu,
    states.CommentsPage,
    states.ReplyEditor,
    states.PostsPage,
    states.PostEditor,
    states.PostPublishing,
    states.PostPublished,
]:
    """Creates the wordpress editor main activity (i.e., navigating the admin menu, posting, etc.)
       and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The activities states as tuple of the form:
        (
            selecting_menu,
            comments_page,
            reply_editor,
            posts_page,
            post_editor,
            post_publishing,
            post_published,
        )
    """
    if name_prefix:
        target_selecting_menu = f"{name_prefix}_{selecting_menu}"
        target_comments_page = f"{name_prefix}_{comments_page}"
        target_reply_editor = f"{name_prefix}_{reply_editor}"
        target_posts_page = f"{name_prefix}_{posts_page}"
        target_post_editor = f"{name_prefix}_{post_editor}"
        target_post_publishing = f"{name_prefix}_{post_publishing}"
        target_post_published = f"{name_prefix}_{post_published}"
    else:
        target_selecting_menu = selecting_menu
        target_comments_page = comments_page
        target_reply_editor = reply_editor
        target_posts_page = posts_page
        target_post_editor = post_editor
        target_post_publishing = post_publishing
        target_post_published = post_published

    t_do_nothing = DelayedTransition(
        noop,
        name=do_nothing,
        target=target_selecting_menu,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_dashboard = DelayedTransition(
        nav.nav_dashboard,
        name=nav_dashboard,
        target=target_selecting_menu,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_nav_comments = DelayedTransition(
        nav.nav_comments,
        name=nav_comments,
        target=target_comments_page,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_new_reply = DelayedTransition(
        actions.ReplyToComment(comments_config.extra.reply_only_guests),
        name=new_reply,
        target=target_reply_editor,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_write_reply = DelayedTransition(
        actions.write_comment_reply,
        name=write_reply,
        target=target_comments_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_media = DelayedTransition(
        nav.nav_media,
        name=nav_media,
        target=target_selecting_menu,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_nav_posts = DelayedTransition(
        nav.nav_posts,
        name=nav_posts,
        target=target_posts_page,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_new_post = DelayedTransition(
        actions.new_post,
        name=new_post,
        target=target_post_editor,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_write_post = DelayedTransition(
        actions.write_post,
        name=write_post,
        target=target_post_publishing,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_publish_post = DelayedTransition(
        actions.publish_post,
        name=publish_post,
        target=target_post_published,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_posts_home = DelayedTransition(
        nav.nav_posts_home,
        name=nav_posts_home,
        target=target_selecting_menu,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # states

    s_selecting_menu = states.SelectingMenu(
        name=selecting_menu,
        nav_dashboard=t_nav_dashboard,
        nav_comments=t_nav_comments,
        nav_media=t_nav_media,
        nav_posts=t_nav_posts,
        ret_transition=pause_wordpress,
        nav_dashboard_weight=menu_config.nav_dashboard,
        nav_comments_weight=menu_config.nav_comments,
        nav_media_weight=menu_config.nav_media,
        nav_posts_weight=menu_config.nav_posts,
        ret_weight=menu_config.return_,
        ret_increase=menu_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_comments_page = states.CommentsPage(
        name=comments_page,
        new_reply=t_new_reply,
        ret_transition=t_do_nothing,
        username=user_config.username,
        new_reply_weight=comments_config.new_reply,
        ret_weight=comments_config.return_,
        ret_increase=comments_config.extra.return_increase,
        reply_only_guests=comments_config.extra.reply_only_guests,
        name_prefix=name_prefix,
    )

    s_reply_editor = states.ReplyEditor(
        name=reply_editor,
        transition=t_write_reply,
        name_prefix=name_prefix,
    )

    s_posts_page = states.PostsPage(
        name=posts_page,
        new_post=t_new_post,
        ret_transition=t_do_nothing,
        new_post_weight=posts_config.new_post,
        ret_weight=posts_config.return_,
        ret_increase=posts_config.extra.return_increase,
        max_posts_daily=posts_config.extra.max_posts_daily,
        name_prefix=name_prefix,
    )

    s_post_editor = states.PostEditor(
        name=post_editor,
        transition=t_write_post,
        name_prefix=name_prefix,
    )

    s_post_publishing = states.PostPublishing(
        name=post_publishing,
        transition=t_publish_post,
        name_prefix=name_prefix,
    )

    s_post_published = states.PostPublished(
        name=post_published,
        transition=t_nav_posts_home,
        name_prefix=name_prefix,
    )

    return (
        s_selecting_menu,
        s_comments_page,
        s_reply_editor,
        s_posts_page,
        s_post_editor,
        s_post_publishing,
        s_post_published,
    )
