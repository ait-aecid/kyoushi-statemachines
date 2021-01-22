import random

from urllib.parse import (
    parse_qs,
    urlparse,
)

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from structlog.stdlib import BoundLogger

from .config import Context
from .wait import (
    check_admin_groups_page,
    check_home_page,
    check_horde_action,
    check_horde_action_success,
    check_horde_delete_confirm,
    check_logged_out,
    horde_wait,
)


class LoginToHorde:
    def __init__(self, username: str, password: str):
        self.username: str = username
        self.password: str = password

    def __call__(self, log: BoundLogger, context: Context):
        driver: webdriver.Remote = context.driver

        # find input fields
        user_field = driver.find_element(By.ID, "horde_user")
        password_field = driver.find_element(By.ID, "horde_pass")
        submit_button = driver.find_element(By.ID, "login-button")

        # clear fields
        user_field.clear()
        password_field.clear()

        user_field.send_keys(self.username)
        password_field.send_keys(self.password)

        # trigger login
        submit_button.click()

        # ensure the page loaded after login
        horde_wait(context.driver, check_home_page)


def logout_of_horde(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver

    logout_icon = driver.find_element_by_css_selector(
        "#horde-head div#horde-logout a.icon"
    )
    ActionChains(driver).move_to_element(logout_icon).click().perform()

    horde_wait(driver, check_logged_out)


def add_user_group(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_admin_groups_page(driver):
        group_name = context.fake.word()

        # add group to log context
        log = log.bind(horde_group=group_name)

        driver.find_element(By.ID, value="name").send_keys(group_name)

        submit_button = driver.find_element_by_xpath(
            "//input[@type='submit' and @value='Add']"
        )

        log.info("Adding group")
        submit_button.click()

        horde_wait(driver, check_horde_action)
        if check_horde_action_success(driver):
            log.info("Added group")
        else:
            log.info("Failed to add group")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="add_group",
            current_page=driver.current_url,
        )


def delete_user_group(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_admin_groups_page(driver):
        group_rows = driver.find_elements_by_xpath(
            "//div[@id='admin_groups']/div[contains(@class,'horde-tree-row')]"
        )
        if len(group_rows) > 0:
            group_row = random.choice(group_rows)

            # get group name and group id from link
            group_link = group_row.find_element_by_xpath(".//span[position()=3]/a")
            group_id = parse_qs(urlparse(group_link.get_attribute("href")).query).get(
                "gid", ["-1"]
            )[0]
            group_name = group_link.text

            # add gid and group name to log context
            log = log.bind(horde_gid=group_id, horde_group=group_name)

            log.info("Deleting group")
            # get delete icon and click on it
            group_row.find_element_by_xpath(
                ".//span/a/img[@alt='Delete Group']"
            ).click()

            # wait for confirm page to load
            horde_wait(driver, check_horde_delete_confirm)

            log.info("Confirming delete")
            # get delete confirm button and click on it
            driver.find_element_by_xpath(
                "//input[@class='horde-delete' and @type='submit' and @name='confirm' and @value='Delete']"
            ).click()

            # horde wait for success/fail message
            horde_wait(driver, check_horde_action)

            if check_horde_action_success(driver):
                log.info("Deleted group")
            else:
                log.info("Failed to remove group")
        else:
            log.warn("No group to delete")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="delete_group",
            current_page=driver.current_url,
        )
