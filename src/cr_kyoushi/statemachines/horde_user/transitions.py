import random

from urllib.parse import parse_qs
from urllib.parse import urlparse

from pydantic import AnyUrl
from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from structlog.stdlib import BoundLogger

from .config import Context
from .wait import check_address_book_page
from .wait import check_admin_groups_page
from .wait import check_calendar_page
from .wait import check_home_page
from .wait import check_horde_action
from .wait import check_horde_action_success
from .wait import check_horde_delete_confirm
from .wait import check_logged_out
from .wait import check_mail_page
from .wait import check_notes_page
from .wait import check_personal_information
from .wait import check_tasks_page
from .wait import horde_wait


# from cr_kyoushi.simulation import transitions
# from cr_kyoushi.simulation.errors import TransitionExecutionError


class GoToHordeWebsite:
    def __init__(self, horde_url: AnyUrl):
        self.horde_url: AnyUrl = horde_url

    def __call__(self, log: BoundLogger, context: Context):
        context.driver.get(self.horde_url)
        horde_wait(context.driver, check_home_page)


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


class NavigateMainMenu:
    def __init__(self, menu_item: int, name: str):
        self.menu_item: int = menu_item
        self.name: str = name

    def click_menu(self, log: BoundLogger, context: Context):

        try:
            menu_element = context.driver.find_element(
                By.CSS_SELECTOR,
                f".horde-navipoint:nth-child({self.menu_item}) .horde-point-center > .horde-mainnavi",
            )
            log.info(f"Navigating to {self.name}")
            if menu_element is not None:
                menu_element.click()
        except NoSuchElementException:
            log.info(f"{self.name} already active")

    def wait_page(self, log: BoundLogger, context: Context):
        pass

    def prepare_page(self, log: BoundLogger, context: Context):
        pass

    def __call__(self, log: BoundLogger, context: Context):
        self.click_menu(log, context)
        self.wait_page(log, context)
        self.prepare_page(log, context)


class NavigateMailMenu(NavigateMainMenu):
    def __init__(self):
        super().__init__(menu_item=1, name="Mail")

    def wait_page(self, log: BoundLogger, context: Context):
        horde_wait(context.driver, check_mail_page)


navigate_mail_menu = NavigateMailMenu()


class NavigateCalendarMenu(NavigateMainMenu):
    def __init__(self):
        super().__init__(menu_item=2, name="Calendar")

    def wait_page(self, log: BoundLogger, context: Context):
        horde_wait(context.driver, check_calendar_page)

    def prepare_page(self, log, context):
        try:
            calendarActiveCheckbox = context.driver.find_element(
                By.CSS_SELECTOR,
                "div#kronolithMenuCalendars * span[class=horde-resource-off]",
            )
            # Calendar is not activated, tick checkbox
            calendarActiveCheckbox.click()
            log.info("Enabled calendar feature")
        except (NoSuchElementException, ElementNotInteractableException):
            # Calendar is activated, do nothing
            pass


navigate_calendar_menu = NavigateCalendarMenu()


class NavigateAddressBookMenu(NavigateMainMenu):
    def __init__(self):
        super().__init__(menu_item=3, name="AddressBook")

    def wait_page(self, log: BoundLogger, context: Context):
        horde_wait(context.driver, check_address_book_page)


navigate_address_book_menu = NavigateAddressBookMenu()


class NavigateTasksMenu(NavigateMainMenu):
    def __init__(self):
        super().__init__(menu_item=4, name="Tasks")

    def wait_page(self, log: BoundLogger, context: Context):
        horde_wait(context.driver, check_tasks_page)

    def prepare_page(self, log, context):
        try:
            tasksActiveCheckbox = context.driver.find_element(
                By.CSS_SELECTOR,
                "div[class=horde-resources] * a[class=horde-resource-off]",
            )
            # Tasks is not activated, tick checkbox
            tasksActiveCheckbox.click()
            log.info("Enabled tasks feature")
        except (NoSuchElementException, ElementNotInteractableException):
            # Tasks is activated, do nothing
            pass


navigate_tasks_menu = NavigateTasksMenu()


class NavigateNotesMenu(NavigateMainMenu):
    def __init__(self):
        super().__init__(menu_item=5, name="Notes")

    def wait_page(self, log: BoundLogger, context: Context):
        horde_wait(context.driver, check_notes_page)

    def prepare_page(self, log, context):
        try:
            notepadActiveCheckbox = context.driver.find_element(
                By.CSS_SELECTOR,
                "div[class=horde-resources] * a[class=horde-resource-off]",
            )
            # Notepad is not activated, tick checkbox
            notepadActiveCheckbox.click()
            log.info("Enabled notepad feature")
        except (NoSuchElementException, ElementNotInteractableException):
            # Notepad is activated, do nothing
            pass


navigate_notes_menu = NavigateNotesMenu()


class NavigateSettingsMenu(NavigateMainMenu):
    def __init__(self, sub_menu: int, link_text: str, expected_title: str, name: str):
        self.sub_menu: int = sub_menu
        self.link_text: str = link_text
        self.expected_title: str = expected_title
        super().__init__(7, name)

    def click_menu(self, log: BoundLogger, context: Context):
        if self.expected_title not in context.driver.title:
            menu_nav = context.driver.find_element_by_css_selector(
                f"div.horde-navipoint:nth-child({self.menu_item}) > ul:nth-child(2) > li:nth-child(1) > ul:nth-child(2) > li:nth-child({self.sub_menu})"
            )

            target_menu = menu_nav.find_element_by_xpath(
                f".//a[ text() = '{self.link_text}' ]"
            )

            log.info(f"Navigating to {self.name}")
            context.driver.get(target_menu.get_attribute("href"))
        else:
            log.info(f"{self.name} already active")


class NavigateAdminConfiguration(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Configuration",
            expected_title="Horde Configuration",
            name="Admin Configuration",
        )


navigate_admin_configuration = NavigateAdminConfiguration()


class NavigateAdminUsers(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Users",
            expected_title="User Administration",
            name="Admin Users",
        )


navigate_admin_users = NavigateAdminUsers()


class NavigateAdminGroups(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Groups",
            expected_title="Group Administration",
            name="Admin Groups",
        )


navigate_admin_groups = NavigateAdminGroups()


def add_user_group(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_admin_groups_page(driver):
        group_name = "sometext"  # ToDo Randomize

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


class NavigateAdminPermissions(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Permissions",
            expected_title="Permissions Administration",
            name="Admin Permissions",
        )


navigate_admin_permissions = NavigateAdminPermissions()


class NavigateAdminLocks(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Locks",
            expected_title="Locks",
            name="Admin Locks",
        )


navigate_admin_locks = NavigateAdminLocks()


class NavigateAdminAlarms(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Alarms",
            expected_title="Alarms",
            name="Admin Alarms",
        )


navigate_admin_alarms = NavigateAdminAlarms()


class NavigateAdminSessions(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Sessions",
            expected_title="Session Administration",
            name="Admin Sessions",
        )


navigate_admin_sessions = NavigateAdminSessions()


class NavigateAdminPHPShell(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="PHP Shell",
            expected_title="PHP Shell",
            name="Admin PHPShell",
        )


navigate_admin_php_shell = NavigateAdminPHPShell()


class NavigateAdminSQLShell(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="SQL Shell",
            expected_title="SQL Shell",
            name="Admin SQLShell",
        )


navigate_admin_sql_shell = NavigateAdminSQLShell()


class NavigateAdminCLI(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="CLI",
            expected_title="Command Shell",
            name="Admin CLI",
        )


navigate_admin_cli = NavigateAdminCLI()


class NavigatePreferencesGlobal(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=2,
            link_text="Global Preferences",
            expected_title="User Preferences",
            name="Global Preferences",
        )


navigate_preferences_global = NavigatePreferencesGlobal()


def navigate_preferences_personal(log: BoundLogger, context: Context):
    # if we are not on the preference page navigate to it first
    if "User Preferences" not in context.driver.title:
        navigate_preferences_global(log, context)

    try:
        # checks for the selected identity label
        context.driver.find_element_by_xpath(
            './/label[@for="id" and text()="Identity\'s name:"]'
        )
        # if the element exists we are already on the page
        log.info("Personal Information already active")
    except NoSuchElementException:
        log.info("Navigate to Personal Information")
        link_element = context.driver.find_element_by_link_text("Personal Information")
        context.driver.get(link_element.get_attribute("href"))

    horde_wait(context.driver, check_personal_information)
