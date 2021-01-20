import random

from typing import List
from typing import Optional
from urllib.parse import urlparse

from pydantic import AnyUrl
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from structlog import BoundLogger

from cr_kyoushi.simulation import transitions
from cr_kyoushi.simulation.errors import TransitionExecutionError

from .config import Context


__all__ = [
    "VisitWebsite",
    "OpenLink",
    "leave_website",
    "background_website",
    "close_website",
]


def _get_available_links(log: BoundLogger, context: Context):
    available_links = context.driver.find_elements(by=By.TAG_NAME, value="a")

    # only consider http links
    context.available_links = [
        link
        for link in available_links
        if urlparse(link.get_attribute("href")).scheme in ["http", "https"]
    ]


class VisitWebsite:
    """Transition function that randomly selects a website and opens it"""

    def __init__(self, websites: List[AnyUrl], fallback_state: Optional[str] = None):
        self.websites: List[AnyUrl] = websites
        self.fallback_state: Optional[str] = fallback_state

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        try:
            # increase website visit count
            context.website_count += 1

            context.current_website = random.choice(self.websites)
            log.info(
                "Visiting website",
                website=context.current_website,
                link=context.current_website,
                visit_count=context.website_count,
            )
            context.driver.get(context.current_website)

            # check new available links
            _get_available_links(log, context)
        except WebDriverException as webdriver_exception:
            # don't count unreachable sites to website count
            context.website_count -= 1

            raise TransitionExecutionError(
                "Selenium error",
                cause=webdriver_exception,
                fallback_state=self.fallback_state,
            )


class OpenLink:
    def __init__(self, fallback_state: Optional[str] = None):
        self.fallback_state: Optional[str] = fallback_state

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        # update website depth
        context.website_depth += 1

        try:
            selected_link: WebElement = random.choice(context.available_links)
            log.info(
                "Visiting link on website",
                website=context.current_website,
                link=selected_link.get_attribute("href"),
                visit_count=context.website_count,
                link_depth=context.website_depth,
            )
            context.driver.get(selected_link.get_attribute("href"))

            # update context
            context.current_website = context.driver.current_url
            _get_available_links(log, context)
        except WebDriverException as webdriver_exception:
            raise TransitionExecutionError(
                "Selenium error",
                cause=webdriver_exception,
                fallback_state=self.fallback_state,
            )


@transitions.transition(target="leaving_website")
def leave_website(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    context.website_depth = 0
    context.current_website = None
    context.available_links = []


@transitions.transition(target="selecting_activity")
def background_website(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    """Do nothing"""


@transitions.transition(target="selecting_activity")
def close_website(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    # close current site by opening an empty data page
    context.driver.get("data:,")
