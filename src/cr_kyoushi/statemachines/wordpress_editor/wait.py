"""Selenium DOM check functions used to verify and check for the current page state."""

from typing import (
    Any,
    Optional,
)

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec


def check_login_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check the wp main login body is present
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//body[contains(@class,'login') and contains(@class, 'wp-core-ui')]",
                )
            )(driver)
            # and login button is present
            and ec.visibility_of_all_elements_located(
                (By.XPATH, "//input[@id='wp-submit' and @value='Log In']")
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_logged_out(driver):
    try:
        return (
            # check on login page
            check_login_page(driver)
            # and logout message is present
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//div[@id='login']/p[@class='message' and contains(text(), 'logged out')]",
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_login_error(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check is login page
            check_login_page(driver)
            # and shows login error
            and ec.visibility_of_element_located((By.ID, "login_error"))(driver)
        )
    except NoSuchElementException:
        return False


def check_admin_menu(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check profile bar is present
            ec.visibility_of_all_elements_located((By.ID, "wp-admin-bar-my-account"))(
                driver
            )
            # and the main dashboard is present
            and ec.visibility_of_all_elements_located((By.ID, "adminmenu"))(driver)
        )
    except NoSuchElementException:
        return False


class CheckAdminMenuSelection:
    def __init__(self, menu_id: str):
        self.menu_id: str = menu_id

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return (
                # check is admin menu
                check_admin_menu(driver)
                # and menu id is active
                and ec.visibility_of_all_elements_located(
                    (
                        By.XPATH,
                        f"//li[@id='{self.menu_id}' and not(contains(@class, 'not-current'))]",
                    )
                )(driver)
            )
        except NoSuchElementException:
            return False


check_admin_dashboard = CheckAdminMenuSelection("menu-dashboard")
check_admin_posts = CheckAdminMenuSelection("menu-posts")
check_admin_media = CheckAdminMenuSelection("menu-media")
check_admin_comments = CheckAdminMenuSelection("menu-comments")


def check_home_page(driver: webdriver.Remote) -> Optional[Any]:
    # should be either login pager or admin area with main menu
    return check_login_page(driver) or check_admin_menu(driver)


def check_post_welcome_guide(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_any_elements_located(
            (By.XPATH, "//div[contains(@class, 'edit-post-welcome-guide')]")
        )(driver)
    except NoSuchElementException:
        return False


def check_post_editor(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check editor is present
            ec.visibility_of_element_located((By.ID, "editor"))(driver)
            # and title input area is present
            and ec.visibility_of_element_located((By.ID, "post-title-0"))(driver)
        )
    except NoSuchElementException:
        return False


def check_post_editor_page(driver: webdriver.Remote) -> Optional[Any]:
    return check_post_welcome_guide(driver) or check_post_editor(driver)


def check_publish_button_active(driver: webdriver.Remote) -> Optional[Any]:
    try:
        # check button is present  and is clickable
        return ec.element_to_be_clickable(
            (
                By.XPATH,
                "//div[@class='editor-post-publish-panel']//button[contains(@class,'editor-post-publish-button')]",
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_publish_init_button_active(driver: webdriver.Remote) -> Optional[Any]:
    try:
        # check button is present  and is clickable
        return ec.element_to_be_clickable(
            (
                By.XPATH,
                "//div[@class='edit-post-header']//button[contains(@class,'editor-post-publish-button')]",
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_published_panel(driver: webdriver.Remote) -> Optional[Any]:
    try:
        # check view post button is present
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                "//div[@class='editor-post-publish-panel']//a[text()='View Post']",
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_comment_reply_editor(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_element_located((By.ID, "replycontainer"))(driver)
    except NoSuchElementException:
        return False


def check_reply_edit_waiting_spinner(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_any_elements_located(
            (
                By.XPATH,
                (
                    "//div[@id='replycontainer']"
                    "//span[contains(@class, 'waiting') and contains(@class, 'spinner') and contains(@class, 'is-active')]"
                ),
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_submitted_comment_reply(driver: webdriver.Remote) -> Optional[Any]:
    return (
        # ensure not loading animation
        not check_reply_edit_waiting_spinner(driver)
        # and not reply textarea open
        and not check_comment_reply_editor(driver)
    )
