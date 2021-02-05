"""Wordpress wordpress editor selenium navigation operations i.e., actions that move between pages or views"""


from typing import (
    Any,
    Callable,
    Optional,
)

from pydantic import HttpUrl
from selenium import webdriver
from structlog.stdlib import BoundLogger

from ..core.selenium import driver_wait
from .context import Context
from .wait import (
    CheckAdminMenuSelection,
    check_admin_posts,
    check_home_page,
    check_post_editor,
)


class GoToWordpressAdmin:
    """Go to wordpress admin action opens the wordpress admin main page

    The url can be configured"""

    def __init__(self, url: HttpUrl):
        self.url: HttpUrl = url

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        log = log.bind(wp_admin_url=self.url)
        if not check_home_page(context.driver):
            log.info("Opening wp admin")
            context.driver.get(self.url)
            driver_wait(context.driver, check_home_page)
            log.info("Opened wp admin")
        else:
            log.info(
                "Already on wp admin",
                current_page=context.driver.current_url,
            )


class NavMainMenu:
    def __init__(self, name: str, menu_id: str):
        self.name: str = name
        self.menu_id: str = menu_id
        self.check_menu: Callable[
            [webdriver.Remote], Optional[Any]
        ] = CheckAdminMenuSelection(menu_id)

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        if not self.check_menu(context.driver):
            menu_link = context.driver.find_element_by_xpath(
                f"//li[@id='{self.menu_id}']/a"
            ).get_attribute("href")
            # bind menu link to log context
            log = log.bind(wp_menu_url=menu_link)

            log.info(f"Opening {self.name} menu")
            context.driver.get(menu_link)
            driver_wait(context.driver, self.check_menu)
            log.info(f"Opened {self.name} menu")
        else:
            log.info(
                f"Already on {self.name} menu",
                current_page=context.driver.current_url,
            )


nav_dashboard = NavMainMenu("dashboard", "menu-dashboard")
nav_posts = NavMainMenu("posts", "menu-posts")
nav_media = NavMainMenu("media", "menu-media")
nav_comments = NavMainMenu("comments", "menu-comments")


def nav_posts_home(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver

    if check_post_editor(driver):

        home_link = driver.find_element_by_xpath(
            "//div[@class='edit-post-header']//a[@aria-label='View Posts']"
        ).get_attribute("href")

        log.info("Leaving post editor")

        driver.get(home_link)
        driver_wait(driver, check_admin_posts)

        log.info("Left post editor")

    else:
        log.error(
            "Invalid action for current page",
            wp_editor_action="nav_posts_home",
            current_page=driver.current_url,
        )
