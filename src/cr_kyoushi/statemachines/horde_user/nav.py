"""Horde activities selenium navigation operations i.e., actions that move between pages or views"""

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

from ..core.selenium import (
    driver_wait,
    wait_for_page_load,
)
from .context import (
    Context,
    HordeContext,
)
from .wait import (
    CheckTitleContains,
    check_address_book_browse,
    check_address_book_page,
    check_admin_cli_page,
    check_admin_configuration_page,
    check_admin_groups_page,
    check_admin_php_page,
    check_admin_sql_page,
    check_calendar_page,
    check_home_page,
    check_mail_page,
    check_notes_page,
    check_personal_information,
    check_tasks_page,
    check_view_contact_page,
)


__all__ = [
    "GoToHordeWebsite",
    "navigate_mail_menu",
    "navigate_calendar_menu",
    "navigate_address_book_menu",
    "navigate_address_book_browse",
    "navigate_address_book_contact",
    "navigate_tasks_menu",
    "navigate_notes_menu",
    "navigate_admin_configuration",
    "navigate_admin_users",
    "navigate_admin_groups",
    "navigate_admin_permissions",
    "navigate_admin_locks",
    "navigate_admin_alarms",
    "navigate_admin_sessions",
    "navigate_admin_php_shell",
    "navigate_admin_sql_shell",
    "navigate_admin_cli",
    "navigate_preferences_global",
    "navigate_preferences_personal",
]


class GoToHordeWebsite:
    """Go to horde action opens horde

    The url can be configured"""

    def __init__(self, horde_url: AnyUrl):
        self.horde_url: AnyUrl = horde_url

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        if not check_home_page(context.driver):
            log.info("Opening horde")
            context.driver.get(self.horde_url)
            driver_wait(context.driver, check_home_page)
            log.info("Opened horde")
        else:
            log.info("Already on horde")


class NavigateMainMenu:
    """Base class for navigation on the main menu"""

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
                with wait_for_page_load(context.driver):
                    menu_element.click()
        except NoSuchElementException:
            log.info(f"{self.name} already active")

    def wait_page(self, log: BoundLogger, context: Context):
        pass

    def prepare_page(self, log: BoundLogger, context: Context):
        pass

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        self.click_menu(log, context)
        self.wait_page(log, context)
        self.prepare_page(log, context)


class NavigateMailMenu(NavigateMainMenu):
    def __init__(self):
        super().__init__(menu_item=1, name="Mail")

    def wait_page(self, log: BoundLogger, context: Context):
        driver_wait(context.driver, check_mail_page)

    def prepare_page(self, log: BoundLogger, context: Context):
        try:
            date_sorter = context.driver.find_element_by_xpath(
                "//div[@id='msglistHeaderHoriz']//div[contains(@class, 'msgDate') and contains(@class, 'sep') and contains(@class, 'sortdown')]"
            )
            if date_sorter is not None:
                log.info("Sorting mail by date ascending")
                date_sorter.click()
        except NoSuchElementException:
            # already sorted correctly
            pass


navigate_mail_menu = NavigateMailMenu()
"""Navigate to the mails menu"""


class NavigateCalendarMenu(NavigateMainMenu):
    def __init__(self):
        super().__init__(menu_item=2, name="Calendar")

    def wait_page(self, log: BoundLogger, context: Context):
        driver_wait(context.driver, check_calendar_page)

    def prepare_page(self, log: BoundLogger, context: Context):
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
"""Navigate to the calendar menu"""


class NavigateAddressBookMenu(NavigateMainMenu):
    def __init__(self):
        super().__init__(menu_item=3, name="AddressBook")

    def wait_page(self, log: BoundLogger, context: Context):
        driver_wait(context.driver, check_address_book_page)


navigate_address_book_menu = NavigateAddressBookMenu()
"""Navigate to the address book menu"""


def navigate_address_book_browse(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    """Navigate to the address book browse sub page"""
    driver: webdriver.Remote = context.driver
    if check_address_book_page(driver):
        log.info("Navigate to address book browse")
        with wait_for_page_load(driver):
            driver.find_element(By.LINK_TEXT, "Browse").click()

        # wait for browse page to load
        driver_wait(driver, check_address_book_browse)
    else:
        log.error(
            "Invalid action for current page",
            horde_action="goto_address_book_browse",
            current_page=driver.current_url,
        )


def navigate_address_book_contact(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    """Navigate to the contact view for a random contact"""
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
        with wait_for_page_load(driver):
            contact_link.click()

        # wait for contact view page to load
        driver_wait(driver, check_view_contact_page)

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
        driver_wait(context.driver, check_tasks_page)

    def prepare_page(self, log: BoundLogger, context: Context):
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
"""Navigate to the tasks menu"""


class NavigateNotesMenu(NavigateMainMenu):
    def __init__(self):
        super().__init__(menu_item=5, name="Notes")

    def wait_page(self, log: BoundLogger, context: Context):
        driver_wait(context.driver, check_notes_page)

    def prepare_page(self, log: BoundLogger, context: Context):
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
"""Navigate to the notes menu"""


class NavigateSettingsMenu:
    """Base class for settings menu navigation"""

    def __init__(
        self,
        link_text: str,
        on_page_check: Callable[[webdriver.Remote], Optional[Any]],
        name: str,
    ):
        self.link_text: str = link_text
        self.on_page_check: Callable[[webdriver.Remote], Optional[Any]] = on_page_check
        self.name: str = name

    def click_menu(self, log: BoundLogger, context: Context):
        if not self.on_page_check(context.driver):
            menu_nav = context.driver.find_element_by_xpath(
                "//div[@id='horde-navigation']"
                "//ul[.//div[contains(@class, 'horde-icon-settings') and contains(@class, 'horde-settings')]]"
            )
            target_menu = menu_nav.find_element_by_xpath(
                f".//a[ text() = '{self.link_text}' ]"
            )

            log.info(f"Navigating to {self.name}")
            context.driver.get(target_menu.get_attribute("href"))
        else:
            log.info(f"{self.name} already active")

    def wait_page(self, log: BoundLogger, context: Context):
        pass

    def prepare_page(self, log: BoundLogger, context: Context):
        pass

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        self.click_menu(log, context)
        self.wait_page(log, context)
        self.prepare_page(log, context)


class NavigateAdminConfiguration(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="Configuration",
            on_page_check=check_admin_configuration_page,
            name="Admin Configuration",
        )


navigate_admin_configuration = NavigateAdminConfiguration()
"""Navigate to the admin configuration settings menu"""


class NavigateAdminUsers(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="Users",
            on_page_check=CheckTitleContains("User Administration"),
            name="Admin Users",
        )


navigate_admin_users = NavigateAdminUsers()
"""Navigate to the admin user settings menu"""


class NavigateAdminGroups(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="Groups",
            on_page_check=check_admin_groups_page,
            name="Admin Groups",
        )


navigate_admin_groups = NavigateAdminGroups()
"""Navigate to the admin groups settings menu"""


class NavigateAdminPermissions(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="Permissions",
            on_page_check=CheckTitleContains("Permissions Administration"),
            name="Admin Permissions",
        )


navigate_admin_permissions = NavigateAdminPermissions()
"""Navigate to the admin permissions settings menu"""


class NavigateAdminLocks(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="Locks",
            on_page_check=CheckTitleContains("Locks"),
            name="Admin Locks",
        )


navigate_admin_locks = NavigateAdminLocks()
"""Navigate to the admin locks settings menu"""


class NavigateAdminAlarms(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="Alarms",
            on_page_check=CheckTitleContains("Alarms"),
            name="Admin Alarms",
        )


navigate_admin_alarms = NavigateAdminAlarms()
"""Navigate to the admin alarms settings menu"""


class NavigateAdminSessions(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="Sessions",
            on_page_check=CheckTitleContains("Session Administration"),
            name="Admin Sessions",
        )


navigate_admin_sessions = NavigateAdminSessions()
"""Navigate to the admin sessions settings menu"""


class NavigateAdminPHPShell(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="PHP Shell",
            on_page_check=check_admin_php_page,
            name="Admin PHPShell",
        )


navigate_admin_php_shell = NavigateAdminPHPShell()
"""Navigate to the admin php shell menu"""


class NavigateAdminSQLShell(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="SQL Shell",
            on_page_check=check_admin_sql_page,
            name="Admin SQLShell",
        )


navigate_admin_sql_shell = NavigateAdminSQLShell()
"""Navigate to the admin sql shell menu"""


class NavigateAdminCLI(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="CLI",
            on_page_check=check_admin_cli_page,
            name="Admin CLI",
        )


navigate_admin_cli = NavigateAdminCLI()
"""Navigate to the admin cli shell menu"""


class NavigatePreferencesGlobal(NavigateSettingsMenu):
    def __init__(self):
        super().__init__(
            link_text="Global Preferences",
            on_page_check=CheckTitleContains("User Preferences"),
            name="Global Preferences",
        )


navigate_preferences_global = NavigatePreferencesGlobal()
"""Navigate to the preferences menu"""


def navigate_preferences_personal(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    """Navigate to the personal preferences settings page"""
    # if we are not on the preference page navigate to it first
    if "User Preferences" not in context.driver.title:
        navigate_preferences_global(log, current_state, context, target)

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

    driver_wait(context.driver, check_personal_information)
