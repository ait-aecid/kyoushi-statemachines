import random

from typing import (
    Any,
    Dict,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from structlog.stdlib import BoundLogger

from .config import (
    Context,
    HordeContext,
)
from .wait import (
    CheckNewContactTab,
    check_address_book_page,
    check_admin_groups_page,
    check_contact_delete_confirm_page,
    check_contact_page,
    check_home_page,
    check_horde_action,
    check_horde_action_success,
    check_horde_group_delete_confirm,
    check_logged_out,
    check_new_contact_page,
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


def start_add_contact(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_address_book_page(driver):
        log.info("Start adding new contact")
        driver.find_element(By.LINK_TEXT, "New Contact").click()

        # wait for new contacts page to load
        horde_wait(driver, check_new_contact_page)
    else:
        log.error(
            "Invalid action for current page",
            horde_action="start_add_contact",
            current_page=driver.current_url,
        )


def __goto_new_contact_tab(
    driver: webdriver.Remote, name: str, section_id: int
) -> WebElement:
    driver.find_element_by_xpath(f"//a[@href='#' and text()='{name}']").click()

    horde_wait(driver, CheckNewContactTab(section_id))


def submit_new_contact(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_new_contact_page(driver):

        # generate random contact information
        # can also add more fields
        contact: Dict[str, Any] = {
            "first_name": context.fake.first_name(),
            "last_name": context.fake.last_name(),
            "email": context.fake.ascii_email(),
        }

        # bind contact info to log context
        log = log.bind(contact=contact)

        # ensure we are on the Personal tab (we should start here anyways)
        __goto_new_contact_tab(driver, "Personal", 0)

        driver.find_element(By.ID, "object_firstname_").send_keys(contact["first_name"])
        driver.find_element(By.ID, "object_lastname_").send_keys(contact["last_name"])

        # goto comm tab
        __goto_new_contact_tab(driver, "Communications", 2)

        driver.find_element(By.ID, "object_email_").send_keys(contact["email"])

        # submit contact
        log.info("Submitting new contact")
        driver.find_element_by_css_selector(
            "form[id='turba_form_addcontact'] * input[value='Add'][type='submit']"
        ).click()

        horde_wait(driver, check_horde_action)
        if check_horde_action_success(driver):
            log.info("Added contact")
        else:
            log.info("Failed to add contact")

    else:
        log.error(
            "Invalid action for current page",
            horde_action="submit_contact",
            current_page=driver.current_url,
        )


def delete_contact(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if check_contact_page(driver):
        log = log.bind(contact=horde.contact)

        log.info("Deleting contacting")
        driver.find_element_by_id("tabDeleteContact").find_element_by_link_text(
            "Delete"
        ).click()

        # wait for delete confirm page to load
        horde_wait(driver, check_contact_delete_confirm_page)
    else:
        log.error(
            "Invalid action for current page",
            horde_action="delete_contact",
            current_page=driver.current_url,
        )


def confirm_delete_contact(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if check_contact_delete_confirm_page(driver):
        log = log.bind(contact=horde.contact)

        log.info("Confirming delete contact")
        driver.find_element_by_xpath(
            "//div[@class='headerbox']/input[@name='delete']"
        ).click()

        # horde wait for success/fail message
        horde_wait(driver, check_horde_action)

        if check_horde_action_success(driver):
            log.info("Deleted contact")
        else:
            log.info("Failed to remove contact")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="delete_contact",
            current_page=driver.current_url,
        )


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
    horde: HordeContext = context.horde

    if check_admin_groups_page(driver):
        group_rows = driver.find_elements_by_xpath(
            "//div[@id='admin_groups']/div[contains(@class,'horde-tree-row')]"
        )
        if len(group_rows) > 0:
            group_row = random.choice(group_rows)

            # get group name and group id from link
            group_link = group_row.find_element_by_xpath(".//span[position()=3]/a")
            horde.group.gid = int(
                parse_qs(urlparse(group_link.get_attribute("href")).query).get(
                    "gid", ["-1"]
                )[0]
            )
            horde.group.name = group_link.text

            # add gid and group name to log context
            log = log.bind(
                horde_gid=horde.group.gid,
                horde_group=horde.group.name,
            )

            log.info("Deleting group")
            # get delete icon and click on it
            group_row.find_element_by_xpath(
                ".//span/a/img[@alt='Delete Group']"
            ).click()

            # wait for confirm page to load
            horde_wait(driver, check_horde_group_delete_confirm)

        else:
            log.warn("No group to delete")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="delete_group",
            current_page=driver.current_url,
        )


def confirm_delete_user_group(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde

    if check_horde_group_delete_confirm(driver):
        # add gid and group name to log context
        log = log.bind(
            horde_gid=horde.group.gid,
            horde_group=horde.group.name,
        )

        log.info("Confirming delete group")
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
        log.error(
            "Invalid action for current page",
            horde_action="confirm_delete_group",
            current_page=driver.current_url,
        )
