"""
A collection of helper functions used to create the various sub activities of the Web Browser user activity.
"""

from typing import Tuple

from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    Transition,
)

from ..core.config import IdleConfig
from . import (
    config,
    states,
    transitions,
)


def get_browser_activity(
    idle: IdleConfig,
    user_config: config.UserConfig,
    states_config: config.WebBrowserStates,
    root: str = "selecting_activity",
    # transitions
    web_browser_transition: str = "visit_website",
    visit_link: str = "visit_link",
    background_website: str = "background_website",
    close_website: str = "close_website",
    leave_website: str = "leave_website",
    # states
    on_website: str = "on_website",
    leaving_website: str = "leaving_website",
) -> Tuple[
    # transitions
    Transition,
    # states
    states.WebsiteState,
    states.LeavingWebsite,
]:
    """Creates the web browser activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The web browser activity states and the entry transition as a tuple of format:
        (
            visit_website,
            on_website,
            leaving_website,
        )
    """

    t_visit_website = DelayedTransition(
        transition_function=transitions.VisitWebsite(
            user_config.websites,
            root,
        ),
        name=web_browser_transition,
        target=on_website,
        delay_after=idle.medium,
    )

    t_visit_link = DelayedTransition(
        transition_function=transitions.OpenLink(root),
        name=visit_link,
        target=on_website,
        delay_after=idle.medium,
    )

    t_background_website = DelayedTransition(
        transition_function=transitions.background_website,
        name=background_website,
        target=root,
        delay_after=idle.small,
    )

    t_close_website = DelayedTransition(
        transition_function=transitions.close_website,
        name=close_website,
        target=root,
        delay_after=idle.small,
    )

    t_leave_website = Transition(
        transition_function=transitions.leave_website,
        name=leave_website,
        target=leaving_website,
    )

    s_on_website = states.WebsiteState(
        name=on_website,
        website_transition=t_visit_link,
        website_weight=states_config.on_website.visit_link,
        leave_transition=t_leave_website,
        leave_weight=states_config.on_website.leave_website,
        max_depth=user_config.max_depth,
    )

    s_leaving_website = states.LeavingWebsite(
        name=leaving_website,
        transitions=[t_background_website, t_close_website],
        weights=[
            states_config.leaving_website.background,
            states_config.leaving_website.close,
        ],
    )

    return (
        # transitions
        t_visit_website,
        # states
        s_on_website,
        s_leaving_website,
    )
