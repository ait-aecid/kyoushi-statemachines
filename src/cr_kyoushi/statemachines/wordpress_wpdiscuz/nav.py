"""Wordpress wpDiscuz selenium navigation operations i.e., actions that move between pages or views"""

import random

from datetime import datetime
from typing import Optional

from pydantic import AnyUrl
from selenium import webdriver
from structlog.stdlib import BoundLogger

from ..core.selenium import driver_wait
from .context import Context
from .wait import (
    CheckNthPostsPage,
    CheckWordpressHome,
    check_post_page,
    check_posts_can_next,
    check_posts_can_previous,
    check_posts_page,
)


class GoToWordpress:
    """Go to wordpress action opens the wordpress main page

    The url can be configured"""

    def __init__(self, url: AnyUrl, title: str):
        self.url: AnyUrl = url
        self.title: str = title

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        log = log.bind(wordpress_url=self.url)
        check_wordpress_home = CheckWordpressHome(self.title)
        if not check_wordpress_home(context.driver):
            log.info("Opening wordpress")
            context.driver.get(self.url)
            driver_wait(context.driver, check_wordpress_home)
            log.info("Opened wordpress")
            context.wpdiscuz.posts_page = 1
        else:
            log.info("Already on wordpress")


def nav_post(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    if check_posts_page(driver):
        posts = driver.find_elements_by_xpath("//main[@class='site-content']/article")
        if len(posts) > 0:
            # reset post info
            post_info = context.wpdiscuz.post
            post_info.clear()

            post_article = random.choice(posts)
            title_link = post_article.find_element_by_xpath(
                ".//header/h2[contains(@class, 'post__title')]/a"
            )

            # set id, title and author
            post_info.pid = post_article.get_attribute("id").replace("post-", "")
            post_info.title = title_link.text
            post_info.link = title_link.get_attribute("href")
            post_info.author = post_article.find_element_by_xpath(
                ".//header/div//li[contains(@class, 'post-author')]/span[@class='meta-text']/a"
            ).text

            # get publish date str and convert iso format to python datetime
            publish_date_str = post_article.find_element_by_xpath(
                ".//header/div//li[contains(@class, 'post-date')]//time"
            ).get_attribute("datetime")
            post_info.publish_date = datetime.fromisoformat(publish_date_str)

            # bind log context
            log = log.bind(wordpress_post=post_info)

            log.info("Opening wordpress post")
            context.driver.get(post_info.link)
            driver_wait(context.driver, check_post_page)
            log.info("Opened wordpress post")
        else:
            log.warning("No posts to view")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="nav_posts",
            current_page=driver.current_url,
        )


def nav_posts_next(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    if check_posts_page(driver) and check_posts_can_next(driver):
        # up posts page
        context.wpdiscuz.posts_page += 1

        # create check function for next page
        check_next_page = CheckNthPostsPage(context.wpdiscuz.posts_page)

        # bind log context
        log = log.bind(
            wordpress_page_current=context.wpdiscuz.posts_page - 1,
            wordpress_page_next=context.wpdiscuz.posts_page,
        )

        next_link = driver.find_element_by_xpath(
            "//a[contains(@class, 'next') and span[contains(@class, 'nav-next-text')]]"
        )
        log.info("Opening next posts page")

        driver.get(next_link.get_attribute("href"))
        driver_wait(context.driver, check_next_page)

        log.info("Opened next post page")

    else:
        log.error(
            "Invalid action for current page",
            horde_action="nav_posts_next",
            current_page=driver.current_url,
        )


def nav_posts_previous(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    if check_posts_page(driver) and check_posts_can_previous(driver):
        # up posts page
        context.wpdiscuz.posts_page -= 1

        # create check function for next page
        check_previous_page = CheckNthPostsPage(context.wpdiscuz.posts_page)

        # bind log context
        log = log.bind(
            wordpress_page_current=context.wpdiscuz.posts_page + 1,
            wordpress_page_previous=context.wpdiscuz.posts_page,
        )

        previous_link = driver.find_element_by_xpath(
            "//a[contains(@class, 'prev') and span[contains(@class, 'nav-prev-text')]]"
        )
        log.info("Opening previous posts page")

        driver.get(previous_link.get_attribute("href"))
        driver_wait(context.driver, check_previous_page)

        log.info("Opened previous post page")

    else:
        log.error(
            "Invalid action for current page",
            horde_action="nav_posts_previous",
            current_page=driver.current_url,
        )


def close_wordpress(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    log.info("Leaving website", current_page=context.driver.current_url)
    context.driver.get("data:,")
