from typing import (
    Any,
    Callable,
    Optional,
    Tuple,
    Union,
)

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import (
    POLL_FREQUENCY,
    WebDriverWait,
)


TIMEOUT = 30


class CheckTitleContains:
    def __init__(self, title: str):
        self.title = title

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        return self.title in driver.title


def horde_wait(
    driver: webdriver.Remote,
    check_func: Callable[[webdriver.Remote], Optional[Any]],
    timeout: Union[float, int] = TIMEOUT,
    poll_frequency: float = POLL_FREQUENCY,
    ignored_exceptions: Tuple[Exception, ...] = None,
):
    WebDriverWait(driver, timeout, poll_frequency, ignored_exceptions).until(check_func)


def check_login_page(driver: webdriver.Remote) -> Optional[Any]:
    return driver.find_element(by=By.ID, value="horde_login")


def check_logged_out(driver: webdriver.Remote) -> Optional[Any]:
    return ec.visibility_of_all_elements_located(
        (By.XPATH, '//div[@class="noticetext" and text()="You have been logged out."]')
    )(driver)


def check_menu_bar(driver: webdriver.Remote) -> Optional[Any]:
    element = driver.find_element(by=By.CSS_SELECTOR, value="#horde-logo > .icon")

    if element is None or not element.is_displayed() or not element.is_enabled():
        return False

    return True


def check_mail_page(driver: webdriver.Remote) -> Optional[Any]:
    return (
        # ensure the inbox view is present
        ec.element_to_be_clickable(
            (By.CSS_SELECTOR, 'div[class="horde-subnavi-icon inboxImg"]')
        )(driver)
        # ensure sidebar is loaded
        and driver.find_element(By.CLASS_NAME, "imp-sidebar-mbox")
        # ensure inbox view exists
        and driver.find_element(By.CSS_SELECTOR, 'span[id="mailboxName"]') is not None
        # ensure the inbox is loaded fully
        and "imp-loading"
        not in driver.find_element(
            By.ID,
            "checkmaillink",
        ).get_attribute("class")
    )


def check_calendar_page(driver: webdriver.Remote) -> Optional[Any]:
    return (
        # ensure mini calendar is loaded
        driver.find_element(
            By.CSS_SELECTOR,
            '#kronolith-minical * td[class*="kronolith-today"]',
        )
        # ensure big calendar is loaded
        and driver.find_element(
            By.CSS_SELECTOR,
            '#kronolith-month-body * td[class*="kronolith-today"]',
        )
        # ensure calendar list is loaded
        and driver.find_element(By.ID, "kronolithMyCalendars")
        and driver.find_element(By.ID, "kronolithAddtasklists")
    )


def check_address_book_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return CheckTitleContains("Address Book")(
            driver
        ) and ec.visibility_of_all_elements_located((By.LINK_TEXT, "New Contact"))(
            driver
        )
    except NoSuchElementException:
        return False


def check_address_book_search_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check if this is a address book subpage
            check_address_book_page(driver)
            # check search bar is loaded
            and ec.visibility_of_all_elements_located((By.NAME, "directory_search"))(
                driver
            )
        )
    except NoSuchElementException:
        return False


def check_new_contact_page(driver: webdriver.Remote) -> Optional[Any]:
    try:

        return CheckTitleContains("New Contact")(
            driver
        ) and ec.visibility_of_element_located((By.ID, "turba_form_addcontact_active"))(
            driver
        )
    except NoSuchElementException:
        return False


class CheckNewContactTab:
    def __init__(self, section_id: int):
        self.section_id: int = section_id

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            form_div = driver.find_element_by_id("turba_form_addcontact_active")
            return ec.visibility_of(
                form_div.find_element_by_xpath(
                    f".//li[@id='turba_form_addcontact_tab_{self.section_id}' and @class='horde-active']"
                )
            ) and ec.visibility_of_element_located(
                (By.ID, f"turba_form_addcontact_section_{self.section_id}")
            )(
                driver
            )
        except NoSuchElementException:
            return False


def check_address_book_browse(driver: webdriver.Remote):
    try:
        return (
            # check for empty contacts loaded
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//div[@id='horde-content']//em[text()='No matching contacts']",
                )
            )(driver)
            # if we have contacts check that the table is visible
            or ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//form[@id='contacts']/table",
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_view_contact_page(driver: webdriver.Remote):
    try:
        return (
            # check that the view form is visibale
            ec.visibility_of_element_located((By.ID, "Turba_View_Contact_inactive"))(
                driver
            )
            # and the user is loaded i.e., mandatory field last name is filled in
            and len(
                driver.find_element_by_id("object_lastname_").get_attribute("value")
            )
            > 0
        )
    except NoSuchElementException:
        return False


def check_edit_contact_page(driver: webdriver.Remote):
    try:
        return (
            # check that the edit form is visible
            ec.visibility_of_element_located((By.ID, "Turba_View_EditContact_active"))(
                driver
            )
            # and the user is loaded i.e., mandatory field last name is filled in
            and len(
                driver.find_element_by_id("object_lastname_").get_attribute("value")
            )
            > 0
        )
    except NoSuchElementException:
        return False


def check_contact_page(driver: webdriver.Remote):
    return check_view_contact_page(driver) or check_edit_contact_page(driver)


def check_contact_delete_confirm_page(driver: webdriver.Remote):
    try:
        return (
            # check confirm dialog is present
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//div[@class='headerbox']/p[text()='Permanently delete this contact?']",
                )
            )(driver)
            # check delete button is present
            and ec.visibility_of_all_elements_located(
                (By.XPATH, "//div[@class='headerbox']/input[@name='delete']")
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_tasks_page(driver: webdriver.Remote) -> Optional[Any]:
    return ec.presence_of_element_located((By.ID, "nag-toggle-my"))(driver)


def check_notes_page(driver: webdriver.Remote) -> Optional[Any]:
    return ec.presence_of_element_located((By.ID, "mnemo-toggle-my"))(driver)


def check_file_manager_page(driver: webdriver.Remote) -> Optional[Any]:
    return ec.presence_of_element_located((By.ID, "manager"))


def check_bookmarks_page(driver: webdriver.Remote) -> Optional[Any]:
    return ec.presence_of_element_located((By.CLASS_NAME, "trean-browse"))(driver)


def check_filters_page(driver: webdriver.Remote) -> Optional[Any]:
    return ec.presence_of_element_located((By.ID, "filterslist"))(driver)


def check_horde_page(driver: webdriver.Remote) -> Optional[Any]:
    return ec.presence_of_element_located((By.ID, "portal"))(driver)


def check_home_page(driver: webdriver.Remote) -> Optional[Any]:
    """Checks wether the main page is fully loaded or not

    Args:
        driver: The webdriver

    Returns:
        `None` if the page is not yet loaded otherwise a webelement is returned
    """

    # if we are not logged in we will be redirected
    if "login.php" in driver.current_url:
        return check_login_page(driver)

    # verify that the menu bar is loaded
    if not check_menu_bar(driver):
        return False

    # depending on the configured homepage
    # check that it is loaded
    if "Mail ::" in driver.title:
        return check_mail_page(driver)
    elif "Calendar ::" in driver.title:
        return check_calendar_page(driver)
    elif "Address Book ::" in driver.title:
        return check_address_book_page(driver)
    elif "Tasks ::" in driver.title:
        return check_tasks_page(driver)
    elif "Notes ::" in driver.title:
        return check_notes_page(driver)
    elif "File Manager ::" in driver.title:
        return check_file_manager_page(driver)
    elif "Bookmarks ::" in driver.title:
        return check_bookmarks_page(driver)
    elif "Filters" in driver.title:
        return check_filters_page(driver)
    elif "Horde ::" in driver.title:
        return check_horde_page(driver)

    return False


def check_personal_information(driver: webdriver.Remote) -> Optional[Any]:
    return ec.visibility_of_element_located(
        (By.CSS_SELECTOR, "default_identity > option[selected='selected']")
    )(driver)


def check_admin_groups_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        # groups pages has this title
        if "Group Administration" in driver.title:
            # check if the group add form is present
            return driver.find_element_by_xpath(
                "//input[@type='hidden' and @name='actionID' and @value='addform']"
            )
    except NoSuchElementException:
        pass
    return False


def check_horde_action(driver: webdriver.Remote) -> Optional[Any]:
    return ec.visibility_of_any_elements_located(
        (
            By.XPATH,
            "//div[@class='GrowlerNotice horde-success' or @class='GrowlerNotice horde-error']/div[@class='GrowlerNoticeBody']",
        )
    )(driver)


def check_horde_action_success(driver: webdriver.Remote) -> Optional[Any]:
    return ec.visibility_of_any_elements_located(
        (
            By.XPATH,
            "//div[@class='GrowlerNotice horde-success']/div[@class='GrowlerNoticeBody']",
        )
    )(driver)


def check_horde_action_error(driver: webdriver.Remote) -> Optional[Any]:
    return ec.visibility_of_any_elements_located(
        (
            By.XPATH,
            "//div[@class='GrowlerNotice horde-error']/div[@class='GrowlerNoticeBody']",
        )
    )(driver)


def check_horde_group_delete_confirm(driver: webdriver.Remote) -> Optional[Any]:
    return (
        # check that the delete form is loaded
        ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                "//form[@name='delete' and @action='groups.php']/h1[@class='header']",
            )
        )(driver)
        # and check that delete button is loaded
        and ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                "//input[@class='horde-delete' and @type='submit' and @name='confirm' and @value='Delete']",
            )
        )(driver)
    )
