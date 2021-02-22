"""Selenium DOM check functions used to verify and check for the current page state."""

from typing import (
    Any,
    Optional,
)

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec

from ..core.selenium import element_in_viewport


def check_posts_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check body with class `home` is loaded
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//body[contains(@class, 'home')]",
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


class CheckNthPostsPage:
    def __init__(self, page_number: int = 1):
        self.page_number: int = page_number

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            # must be a posts page
            if check_posts_page(driver):
                pagination_nav = driver.find_element_by_xpath(
                    "//nav[contains(@class, 'navigation') and contains(@class, 'pagination')]"
                )
                return (
                    # if we have a nav element we have to check if the current page is page number
                    pagination_nav.find_element_by_xpath(
                        ".//span[contains(@class, 'page-numbers') and contains(@class, 'current')]"
                    ).text
                    == str(self.page_number)
                )
            else:
                return False
        except NoSuchElementException:
            # if there is only one page then the nav does not exist
            # then we are always on page 1
            return True if self.page_number == 1 else False


class CheckWordpressHome:
    def __init__(self, title: str):
        self.title: str = title
        self.is_first_page: CheckNthPostsPage = CheckNthPostsPage(page_number=1)

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        return (
            # check that the page header is loaded with expected wordpress title
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    f"//header[@id='site-header']//h1[@class='site-title' and text()='{self.title}']",
                )
            )(driver)
            # and is first post page
            and self.is_first_page(driver)
        )


def check_post_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check is single post body
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//body[contains(@class, 'single-post')]",
                )
            )(driver)
            # and comments area is present
            and ec.visibility_of_element_located((By.ID, "comments"))(driver)
        )
    except NoSuchElementException:
        return False


def check_post_rated(driver: webdriver.Remote) -> Optional[Any]:
    try:
        rating_div = driver.find_element_by_id("wpd-post-rating")
        if "wpd-not-rated" in rating_div.get_attribute("class"):
            return False
        else:
            return True
    except NoSuchElementException:
        # if the rating element does not exist
        # then we consider the post rated
        return True


def check_rating_stars_visible(driver: webdriver.Remote) -> Optional[Any]:
    # f".//div[@class='wpd-rating-stars']/*[name()='svg' and position()={post_info.rating}]"
    try:
        stars = driver.find_elements_by_xpath(
            "//div[@id='wpd-post-rating']//div[@class='wpd-rating-stars']/*[name()='svg']"
        )

        return (
            # check rating stars are visible and in the viewport
            all(
                ec.visibility_of(star)(driver) and element_in_viewport(driver, star)
                for star in stars
            )
        )
    except NoSuchElementException:
        return False


class CheckVoteRegistered:
    def __init__(self, cid: str, up_vote: bool = True):
        """
        Args:
            cid: The id of the comment to check for
            up_vote: If the vote was an up or down vote
        """
        self.cid: str = cid
        self.check: str = (
            "div[contains(@class,'wpd-vote-up') and contains(@class, 'wpd-up')]"
            if up_vote
            else "div[contains(@class,'wpd-vote-down') and contains(@class, 'wpd-down')]"
        )

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return (
                # check if vote was set
                ec.visibility_of_element_located(
                    (
                        By.XPATH,
                        f"//div[@id='comment-{self.cid}']//div[@class='wpd-vote']/{self.check}",
                    )
                )(driver)
            )
        except NoSuchElementException:
            return False


def check_loading_bar_invisible(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.invisibility_of_element_located((By.ID, "wpdiscuz-loading-bar"))(
            driver
        )
    except NoSuchElementException:
        # if the loading bar element does not exist we consider it invisible
        return True


def check_comment_action_failed(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_element_located(
            (
                By.XPATH,
                "//div[@id='wpdiscuz-comment-message']//div[contains(@class, 'wpdiscuz-message-error')]",
            )
        )(driver)
    except NoSuchElementException:
        return False


class CheckVoted:
    def __init__(self, cid: str, up_vote: bool = True):
        """
        Args:
            cid: The id of the comment to check for
            up_vote: If the vote was an up or down vote
        """

        self.check_vote_registed: CheckVoteRegistered = CheckVoteRegistered(
            cid, up_vote
        )

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        return (
            # check if vote was set
            self.check_vote_registed(driver)
            # vote failed message
            or check_comment_action_failed(driver)
        )


class CheckCommentBase:
    def __init__(self, parent_cid: str = "0", cid: str = "0"):
        self.parent_cid: str = parent_cid
        self.cid: str = cid


class CheckCommentEditor(CheckCommentBase):
    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return ec.visibility_of_element_located(
                (By.ID, f"wpd-editor-{self.cid}_{self.parent_cid}")
            )(driver)
        except NoSuchElementException:
            return False


class CheckCommentSubmit(CheckCommentBase):
    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return ec.visibility_of_element_located(
                (By.ID, f"wpd-field-submit-{self.cid}_{self.parent_cid}")
            )(driver)
        except NoSuchElementException:
            return False


class CheckCommentWriter(CheckCommentBase):
    def __init__(self, parent_cid="0", cid="0"):
        super().__init__(parent_cid=parent_cid, cid=cid)
        self.check_submit = CheckCommentSubmit(parent_cid=parent_cid, cid=cid)
        self.check_editor = CheckCommentEditor(parent_cid=parent_cid, cid=cid)

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        return self.check_editor(driver) and self.check_submit(driver)


def check_comment_submitted(driver: webdriver.Remote) -> Optional[Any]:
    return check_loading_bar_invisible(driver) or check_comment_action_failed(driver)


def check_posts_can_next(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                "//a[contains(@class, 'next') and span[contains(@class, 'nav-next-text')]]",
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_posts_can_previous(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                "//a[contains(@class, 'prev') and span[contains(@class, 'nav-prev-text')]]",
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_is_logged_in(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_element_located(
            (
                By.ID,
                "wpadminbar",
            )
        )(driver)
    except NoSuchElementException:
        return False
