import random

from typing import (
    Any,
    Callable,
    Optional,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)

from pydantic import AnyUrl
from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
)
from selenium.webdriver.common.by import By
from structlog.stdlib import BoundLogger

from .config import (
    Context,
    HordeContext,
)
from .wait import (
    CheckTitleContains,
    check_address_book_browse,
    check_address_book_page,
    check_admin_configuration_page,
    check_admin_groups_page,
    check_calendar_page,
    check_home_page,
    check_mail_page,
    check_notes_page,
    check_personal_information,
    check_tasks_page,
    check_view_contact_page,
    horde_wait,
)


# from cr_kyoushi.simulation import transitions
# from cr_kyoushi.simulation.errors import TransitionExecutionError


class GoToHordeWebsite:
    def __init__(self, horde_url: AnyUrl):
        self.horde_url: AnyUrl = horde_url

    def __call__(self, log: BoundLogger, context: Context):
        context.driver.get(self.horde_url)
        horde_wait(context.driver, check_home_page)


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


def navigate_address_book_browse(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    if check_address_book_page(driver):
        log.info("Navigate to address book browse")
        driver.find_element(By.LINK_TEXT, "Browse").click()

        # wait for browse page to load
        horde_wait(driver, check_address_book_browse)
    else:
        log.error(
            "Invalid action for current page",
            horde_action="goto_address_book_browse",
            current_page=driver.current_url,
        )


def navigate_address_book_contact(log: BoundLogger, context: Context):
    driver: webdriver.Remote = context.driver
    horde: HordeContext = context.horde
    if (
        check_address_book_browse(driver)
        # can only navigate if there are contacts
        and len(driver.find_elements(By.CSS_SELECTOR, 'a[href^="/turba/contact.php"]'))
        > 0
    ):
        contacts = driver.find_elements(
            By.CSS_SELECTOR, 'a[href^="/turba/contact.php"]'
        )

        # choose random contact
        contact_link = random.choice(contacts)
        # parse contact link
        parsed_query = parse_qs(urlparse(contact_link.get_attribute("href")).query)

        # get selected contacts info
        horde.contact.source = parsed_query.get("source", [""])[0]
        horde.contact.key = parsed_query.get("key", [""])[0]
        horde.contact.name = contact_link.text

        log.info("Navigate to contact page", contact=horde.contact)
        contact_link.click()

        # wait for contact view page to load
        horde_wait(driver, check_view_contact_page)

    else:
        log.error(
            "Invalid action for current page",
            horde_action="goto_contact",
            current_page=driver.current_url,
        )


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
    def __init__(
        self,
        sub_menu: int,
        link_text: str,
        on_page_check: Callable[[webdriver.Remote], Optional[Any]],
        name: str,
    ):
        self.sub_menu: int = sub_menu
        self.link_text: str = link_text
        self.on_page_check: Callable[[webdriver.Remote], Optional[Any]] = on_page_check
        super().__init__(7, name)

    def click_menu(self, log: BoundLogger, context: Context):
        if not self.on_page_check(context.driver):
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
            on_page_check=check_admin_configuration_page,
            name="Admin Configuration",
        )


navigate_admin_configuration = NavigateAdminConfiguration()


class NavigateAdminUsers(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Users",
            on_page_check=CheckTitleContains("User Administration"),
            name="Admin Users",
        )


navigate_admin_users = NavigateAdminUsers()


class NavigateAdminGroups(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Groups",
            on_page_check=check_admin_groups_page,
            name="Admin Groups",
        )


navigate_admin_groups = NavigateAdminGroups()


class NavigateAdminPermissions(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Permissions",
            on_page_check=CheckTitleContains("Permissions Administration"),
            name="Admin Permissions",
        )


navigate_admin_permissions = NavigateAdminPermissions()


class NavigateAdminLocks(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Locks",
            on_page_check=CheckTitleContains("Locks"),
            name="Admin Locks",
        )


navigate_admin_locks = NavigateAdminLocks()


class NavigateAdminAlarms(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Alarms",
            on_page_check=CheckTitleContains("Alarms"),
            name="Admin Alarms",
        )


navigate_admin_alarms = NavigateAdminAlarms()


class NavigateAdminSessions(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="Sessions",
            on_page_check=CheckTitleContains("Session Administration"),
            name="Admin Sessions",
        )


navigate_admin_sessions = NavigateAdminSessions()


class NavigateAdminPHPShell(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="PHP Shell",
            on_page_check=CheckTitleContains("PHP Shell"),
            name="Admin PHPShell",
        )


navigate_admin_php_shell = NavigateAdminPHPShell()


class NavigateAdminSQLShell(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="SQL Shell",
            on_page_check=CheckTitleContains("SQL Shell"),
            name="Admin SQLShell",
        )


navigate_admin_sql_shell = NavigateAdminSQLShell()


class NavigateAdminCLI(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=1,
            link_text="CLI",
            on_page_check=CheckTitleContains("Command Shell"),
            name="Admin CLI",
        )


navigate_admin_cli = NavigateAdminCLI()


class NavigatePreferencesGlobal(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            sub_menu=2,
            link_text="Global Preferences",
            on_page_check=CheckTitleContains("User Preferences"),
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
