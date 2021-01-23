import random
import re

from typing import (
    Any,
    Dict,
    Union,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select
from structlog.stdlib import BoundLogger
from titlecase import titlecase

from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.simulation.util import sleep

from ..core.selenium import (
    slow_type,
    type_linebreak,
)
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
    check_edit_task_general_tab,
    check_home_page,
    check_horde_action,
    check_horde_action_success,
    check_horde_group_delete_confirm,
    check_logged_out,
    check_new_contact_page,
    check_new_note_page,
    check_new_task_general_tab,
    check_note_write_page,
    check_notes_page,
    check_tasks_page,
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
            horde_action="confirm_delete_contact",
            current_page=driver.current_url,
        )


def new_task(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_tasks_page(driver):
        log.info("Adding task")
        driver.find_element_by_xpath(
            "//div[@class='horde-new']//span[@class='horde-new-link']/a"
        ).click()
        # wait for new task form to load
        horde_wait(driver, check_new_task_general_tab)
    else:
        log.error(
            "Invalid action for current page",
            horde_action="new_task",
            current_page=driver.current_url,
        )


def save_new_task(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    form_delay: Union[ApproximateFloat, float] = context.horde.form_field_delay
    if check_new_task_general_tab(driver):
        # fill out form
        # set task name
        name = " ".join(context.fake.words(2))
        slow_type(
            element=driver.find_element_by_id("name"),
            text=name,
        )
        sleep(form_delay)

        # set tags field
        tags_count = random.randint(0, 3)
        tags = []
        if tags_count > 0:
            tags = context.fake.words(tags_count)
            log.info("Enter tags", horde_tags=tags)
            slow_type(
                element=driver.find_element_by_id("tags"),
                text=", ".join(tags),
            )
            sleep(form_delay)

        # set assignee
        assignee_select = Select(driver.find_element(By.CSS_SELECTOR, "#assignee"))
        assignee_index = random.randint(
            0,
            len(assignee_select.options) - 1,
        )
        # get selected assignee value ("" means no assignee)
        assignee = assignee_select.options[assignee_index].get_attribute("value")
        assignee_select.select_by_index(assignee_index)
        sleep(form_delay)

        # set private setting
        private = bool(random.getrandbits(1))
        if private:
            driver.find_element_by_id("private").click()
        sleep(form_delay)

        # select priority
        priority_select = Select(driver.find_element(By.CSS_SELECTOR, "#priority"))
        priority_index = random.randint(
            0,
            len(priority_select.options) - 1,
        )
        # get selected priority value ("" means no priority)
        priority = priority_select.options[priority_index].get_attribute("value")
        priority_select.select_by_index(priority_index)
        sleep(form_delay)

        # set time estimate
        estimate = random.randint(1, 100)
        estimate_input = driver.find_element_by_id("estimate")
        slow_type(
            element=estimate_input,
            text=str(estimate),
        )
        sleep(form_delay)

        log.info(
            "Saving new task",
            name=name,
            tags=tags,
            assignee=assignee,
            private=private,
            priority=priority,
            estimate=estimate,
        )
        driver.find_element_by_xpath(
            "//form[@id='nag_form_task']//input[@type='submit' and @value='Save']"
        ).click()

        horde_wait(driver, check_horde_action)
        if check_horde_action_success(driver):
            log.info("Saved task")
        else:
            log.info("Failed to save task")

        # wait for task page to load
        horde_wait(driver, check_tasks_page)
    else:
        log.error(
            "Invalid action for current page",
            horde_action="save_task",
            current_page=driver.current_url,
        )


def edit_task(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if check_tasks_page(driver):
        tasks = driver.find_elements_by_xpath(
            "//tbody[@id='tasks-body']//a[contains(@title,'Edit')]"
        )
        if len(tasks) > 0:
            # select radom task
            task_link = random.choice(tasks)

            # get name of selected task
            link_title_pattern = r'^Edit "(.*)"$'
            name_match = re.match(
                pattern=link_title_pattern,
                string=task_link.get_attribute("title"),
            )
            if name_match is not None:
                horde.task.name = name_match.group(1)

            # get tasklist and task id
            parsed_link = parse_qs(urlparse(task_link.get_attribute("href")).query)
            horde.task.list_id = parsed_link.get("tasklist", [""])[0]
            horde.task.id = parsed_link.get("task", [""])[0]

            # bind info to log context
            log = log.bind(task=horde.task)

            log.info("Editing task")
            task_link.click()
            # wait for task info view to load
            horde_wait(driver, check_edit_task_general_tab)
        else:
            log.warn("No task to edit")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="edit_task",
            current_page=driver.current_url,
        )


def delete_task(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if check_edit_task_general_tab(driver):
        log = log.bind(task=horde.task)

        log.info("Deleting task")
        driver.find_element_by_xpath(
            "//div[@class='horde-form-buttons']/input[@type='submit' and @value='Delete']"
        ).click()

        # horde wait for success/fail message
        horde_wait(driver, check_horde_action)

        if check_horde_action_success(driver):
            log.info("Deleted task")
        else:
            log.info("Failed to remove task")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="delete_task",
            current_page=driver.current_url,
        )


def new_note(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_notes_page(driver):
        log.info("Adding note")
        driver.find_element_by_xpath(
            "//div[@class='horde-new']//a[contains(@title,'New Note')]"
        ).click()
        # wait for new note form to load
        horde_wait(driver, check_new_note_page)
    else:
        log.error(
            "Invalid action for current page",
            horde_action="new_note",
            current_page=driver.current_url,
        )


def write_note(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_note_write_page(driver):
        # get elements
        textarea = driver.find_element(By.ID, "mnemo-body")
        tags_input = driver.find_element(By.ID, "memo_tags")
        save_button = driver.find_element(
            By.XPATH,
            "//form[@name='memo']//input[@type='submit' and @value='Save']",
        )
        # get memo ids
        # the memo field does not exist for new notes
        memo = driver.find_element(
            By.XPATH,
            "//form[@name='memo']//input[@type='hidden' and @name='memo']",
        ).get_attribute("value")
        memolist_original = driver.find_element(
            By.XPATH,
            "//form[@name='memo']//input[@type='hidden' and @name='memolist_original']",
        ).get_attribute("value")
        notepad_target = driver.find_element(
            By.XPATH,
            "//form[@name='memo']//input[@type='hidden' and @name='notepad_target']",
        ).get_attribute("value")
        # bind memo ids to log context
        log = log.bind(
            memo=memo,
            memolist_original=memolist_original,
            notepad_target=notepad_target,
        )

        # generate content
        title = titlecase(context.fake.sentence(nb_words=3)[:-1])
        content = context.fake.paragraphs(random.randint(1, 4))
        tags = context.fake.words(random.randint(0, 3))
        # bind content to log context
        log = log.bind(title=title, content=content, tags=tags)

        log.info("Writing note")
        # clear textarea
        textarea.clear()

        # type note title
        slow_type(element=textarea, text=title)
        type_linebreak(context.driver, count=2)

        # type content
        for paragraph in content:
            slow_type(element=textarea, text=paragraph)
            type_linebreak(context.driver)

        # clear tags
        tags_input.clear()
        # type tags
        slow_type(element=tags_input, text=", ".join(tags))

        log.info("Saving note")
        save_button.click()

        horde_wait(driver, check_horde_action)
        if check_horde_action_success(driver):
            log.info("Saved note")
        else:
            log.info("Failed to save note")

        # ensure notes page is loaded
        horde_wait(driver, check_notes_page)
    else:
        log.error(
            "Invalid action for current page",
            horde_action="new_note",
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
