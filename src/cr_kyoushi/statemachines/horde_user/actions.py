import random
import re

from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Dict,
    List,
    Union,
    cast,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select
from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.simulation.util import sleep

from ..core.selenium import (
    js_set_text,
    slow_type,
    type_linebreak,
)
from ..core.util import get_title
from .config import (
    Context,
    HordeContext,
    MemoInfo,
)
from .wait import (
    CheckNewContactTab,
    check_address_book_page,
    check_admin_cli_execute_view,
    check_admin_cli_page,
    check_admin_configuration_page,
    check_admin_groups_page,
    check_admin_php_execute_view,
    check_admin_php_page,
    check_admin_sql_execute_view,
    check_admin_sql_page,
    check_admin_version_check_view,
    check_calendar_delete_confirm_view,
    check_calendar_edit_view,
    check_calendar_page,
    check_calendar_write_view,
    check_contact_delete_confirm_page,
    check_contact_page,
    check_edit_note_page,
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


def new_calendar_event(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_calendar_page(driver):
        log.info("Adding calendar event")
        context.horde.event.clear()
        driver.find_element_by_id("kronolithNewEvent").click()
        # wait for new calender form view to load
        horde_wait(driver, check_calendar_write_view)
    else:
        log.error(
            "Invalid action for current page",
            horde_action="new_event",
            current_page=driver.current_url,
        )


def write_calendar_event(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if check_calendar_write_view(driver):
        date_format = "%m/%d/%y"
        time_format = "%I:%M %p"

        # get elements
        title_input = driver.find_element_by_id("kronolithEventTitle")
        start_input = driver.find_element_by_id("kronolithEventStartDate")
        start_time_input = driver.find_element_by_id("kronolithEventStartTime")
        end_input = driver.find_element_by_id("kronolithEventEndDate")
        end_time_input = driver.find_element_by_id("kronolithEventEndTime")
        location_input = driver.find_element_by_id("kronolithEventLocation")
        description_input = driver.find_element_by_id("kronolithEventDescription")
        save_button = driver.find_element_by_id("kronolithEventSave")

        write_title = False
        # generate content
        if horde.event.title is None:
            # we generate a title for new events
            horde.event.title = get_title(context.fake)
            write_title = True

        horde.event.start = cast(
            datetime,  # casting due to Faker missing annotations
            context.fake.date_time_this_month(before_now=True, after_now=True),
        )
        # end time is randomly selected between the start time and the end of that day
        end_max = (horde.event.start + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        horde.event.end = cast(
            datetime,  # casting due to Faker missing annotations
            context.fake.date_time_between_dates(
                datetime_start=horde.event.start,
                datetime_end=end_max,
            ),
        )
        horde.event.location = cast(
            str,  # casting due to Faker missing annotations
            context.fake.address(),
        )
        horde.event.description = cast(
            List[str],  # casting due to Faker missing annotations
            context.fake.paragraphs(random.randint(0, 3)),
        )

        # bind event to log context
        log = log.bind(calendar_event=horde.event)

        log.info("Writing calendar event")

        # fill out calendar event
        if write_title:
            slow_type(element=title_input, text=horde.event.title)
        else:
            # if we do not change the title we jump to the end of it
            # we do this to prevent the first title char from being deleted
            # by our next send keys
            title_input.send_keys(Keys.CONTROL + Keys.END)

        # set start and end time
        # we set the date and time fields directly to avoid triggering
        # the incorrect format warning (causes a image request)
        # for a normal user this request would not be made
        js_set_text(driver, start_input, horde.event.start.strftime(date_format))
        js_set_text(driver, start_time_input, horde.event.start.strftime(time_format))
        js_set_text(driver, end_input, horde.event.start.strftime(date_format))
        js_set_text(driver, end_time_input, horde.event.end.strftime(time_format))

        # set location
        location_input.clear()
        slow_type(element=location_input, text=horde.event.location)

        # set description
        description_input.clear()
        for paragraph in horde.event.description:
            slow_type(element=description_input, text=paragraph)
            type_linebreak(driver)

        log.info("Saving calendar event")

        save_button.click()

        # ensure calendar page is loaded
        horde_wait(driver, check_calendar_page)

        log.info("Saved calendar event")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="write_calendar_event",
            current_page=driver.current_url,
        )


def edit_calendar_event(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if check_calendar_page(driver):
        # clear event info
        horde.event.clear()

        events = driver.find_elements(By.CSS_SELECTOR, "div[id^=kronolithEventmonth]")
        if len(events) > 0:
            # select radom event
            event_div = random.choice(events)

            # get infos about selected event
            date_str = (
                event_div.find_element_by_xpath("..")
                .get_attribute("id")
                .replace("kronolithMonthDay", "")
            )
            id_pattern = r"^kronolithEventmonth(internal)(.*)" + date_str + r"(.*)$"
            id_match = re.match(
                pattern=id_pattern,
                string=event_div.get_attribute("id"),
            )
            if id_match is not None:
                horde.event.calendar = f"{id_match.group(1)}|{id_match.group(2)}"
                horde.event.id = id_match.group(3)
            horde.event.title = event_div.get_attribute("title")

            # bind info to log context
            log = log.bind(calendar_event=horde.event)

            log.info("Editing calendar event")
            event_div.click()
            # wait for calendar edit view to load
            horde_wait(driver, check_calendar_edit_view)
        else:
            log.warn("No calendar event to edit")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="edit_calendar_event",
            current_page=driver.current_url,
        )


def delete_calendar_event(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if check_calendar_edit_view(driver):
        log = log.bind(calendar_event=horde.event)

        log.info("Deleting calendar event")
        driver.find_element_by_id("kronolithEventDelete").click()

        # wait for delete confirm view to load
        horde_wait(driver, check_calendar_delete_confirm_view)

        driver.find_element(By.ID, "kronolithEventDeleteConfirm").click()

        # wait for the calendar view to be visible again
        horde_wait(driver, check_calendar_page)

        log.info("Deleted calendar event")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="delete_calendar_event",
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
    horde.contact.clear()


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
    horde.task.clear()


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

        # generate content
        title = get_title(context.fake)
        content = context.fake.paragraphs(random.randint(1, 4))
        tags = context.fake.words(random.randint(0, 3))

        # bind content to log context
        # bind memo ids to log context
        log = log.bind(
            memo=MemoInfo(
                id=memo,
                list_id=memolist_original,
                target_list_id=notepad_target,
                title=title,
                content=content,
                tags=tags,
            ),
        )

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


def edit_note(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if check_notes_page(driver):
        memos = driver.find_elements_by_xpath(
            "//tbody[@id='notes_body']//a[contains(@title,'Edit')]"
        )
        if len(memos) > 0:
            # select radom memo
            memo_link = random.choice(memos)

            # get title of selected memo
            link_title_pattern = r'^Edit "(.*)"$'
            title_match = re.match(
                pattern=link_title_pattern,
                string=memo_link.get_attribute("title"),
            )
            if title_match is not None:
                horde.memo.title = title_match.group(1)

            # get tasklist and task id
            parsed_link = parse_qs(urlparse(memo_link.get_attribute("href")).query)
            horde.memo.list_id = parsed_link.get("memolist", [""])[0]
            horde.memo.id = parsed_link.get("memo", [""])[0]

            # bind info to log context
            log = log.bind(memo=horde.memo)

            log.info("Editing note")
            memo_link.click()
            # wait for memo edit view to load
            horde_wait(driver, check_edit_note_page)
        else:
            log.warn("No note to edit")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="edit_note",
            current_page=driver.current_url,
        )


def delete_note(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if check_edit_note_page(driver):
        log = log.bind(memo=horde.memo)

        log.info("Deleting note")
        driver.find_element_by_xpath("//form[@name='memo']//a[text()='Delete']").click()

        # horde wait for success/fail message
        horde_wait(driver, check_horde_action)

        if check_horde_action_success(driver):
            log.info("Deleted note")
        else:
            log.info("Failed to remove note")
    else:
        log.error(
            "Invalid action for current page",
            horde_action="delete_note",
            current_page=driver.current_url,
        )
    horde.memo.clear()


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
        log = log.bind(group=horde.group)

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
    horde.group.clear()


def admin_check_versions(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_admin_configuration_page(driver):
        log.info("Checking software versions")
        driver.find_element_by_xpath(
            "//input[@value='Check for newer versions' and @type='submit']"
        ).click()

        # wait for version table to load
        horde_wait(driver, check_admin_version_check_view)
        log.info("Checked software versions")

    else:
        log.error(
            "Invalid action for current page",
            horde_action="check_versions",
            current_page=driver.current_url,
        )


def admin_exec_php(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_admin_php_page(driver):
        # in future versions we can make this a configurable
        # list of code templates and add error handling
        # to support incorrect php code
        fn_name = context.fake.word()
        php_code = (
            f"function {fn_name}() {{\n"
            f'    echo "{context.fake.sentence()}";\n'
            "}\n"
            f"{fn_name}();\n"
        )
        # choose horde app context
        app_select = Select(driver.find_element(By.ID, "app"))
        app_index = random.randint(
            0,
            len(app_select.options) - 1,
        )
        # get selected assignee value ("" means no assignee)
        horde_app = app_select.options[app_index].get_attribute("value")

        log = log.bind(php_code=php_code, horde_app=horde_app)

        log.info("Write PHP code")

        # set horde app selection
        app_select.select_by_index(app_index)

        # write php code
        code_area = driver.find_element_by_id("php")
        for line in php_code.split("\n"):
            slow_type(element=code_area, text=line)
            type_linebreak(driver)

        log.info("Executing PHP code")
        driver.find_element_by_xpath(
            "//input[@value='Execute' and @type='submit']"
        ).click()

        # wait for version table to load
        horde_wait(driver, check_admin_php_execute_view)
        log.info("Executed PHP code")

    else:
        log.error(
            "Invalid action for current page",
            horde_action="exec_php",
            current_page=driver.current_url,
        )


def admin_exec_sql(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_admin_sql_page(driver):
        # in future versions we can make this a configurable
        # list of code templates and tables and add error handling
        # to support incorrect sql code
        tables = [
            "kronolith_events",
            "turba_objects",
            "content_schema_info",
            "horde_groups",
            "rampage_objects",
            "nag_tasks",
        ]
        table = random.choice(tables)
        sql_code = f"select * from {table}"

        # bind info to context
        log = log.bind(sql_code=sql_code, table=table)

        log.info("Write SQL code")

        # write php code
        code_area = driver.find_element_by_id("sql")
        for line in sql_code.split("\n"):
            slow_type(element=code_area, text=line)
            type_linebreak(driver)

        log.info("Executing SQL code")
        driver.find_element_by_xpath(
            "//input[@value='Execute' and @type='submit']"
        ).click()

        # wait for version table to load
        horde_wait(driver, check_admin_sql_execute_view)
        log.info("Executed SQL code")

    else:
        log.error(
            "Invalid action for current page",
            horde_action="exec_sql",
            current_page=driver.current_url,
        )


def admin_exec_cli(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_admin_cli_page(driver):
        # in future versions we can make this a configurable
        # list of command templates and add error handling
        # to support incorrect cli code
        commands = ["pwd", "id", "ls", "whoami", "cat groups.php"]
        cli_commands = []
        for i in range(
            0,
            random.randint(
                1,
                min(3, len(commands)),
            ),
        ):
            cli_commands.append(random.choice(commands))

        # bind info to context
        log = log.bind(cli_commands=cli_commands)

        log.info("Write CLI command")

        # write php code
        code_area = driver.find_element_by_id("cmd")
        for line in cli_commands:
            slow_type(element=code_area, text=line)
            type_linebreak(driver)

        log.info("Executing CLI command")
        driver.find_element_by_xpath(
            "//input[@value='Execute' and @type='submit']"
        ).click()

        # wait for version table to load
        horde_wait(driver, check_admin_cli_execute_view)
        log.info("Executed CLI command")

    else:
        log.error(
            "Invalid action for current page",
            horde_action="exec_cli",
            current_page=driver.current_url,
        )
