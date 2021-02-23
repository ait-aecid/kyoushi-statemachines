"""Selenium DOM check functions used to verify and check for the current page state."""

from typing import (
    Any,
    Optional,
)

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec


class CheckTitleContains:
    def __init__(self, title: str):
        self.title = title

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        return self.title in driver.title


def check_login_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_element_located((By.ID, "horde_login"))(driver)
    except NoSuchElementException:
        return False


def check_login_failed_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # is login page
            check_login_page(driver)
            # and failed message is visible
            and ec.visibility_of_element_located((By.CLASS_NAME, "noticetext"))(driver)
        )
    except NoSuchElementException:
        return False


def check_logged_out(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                '//div[@class="noticetext" and text()="You have been logged out."]',
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_menu_bar(driver: webdriver.Remote) -> Optional[Any]:
    try:
        element = driver.find_element(by=By.CSS_SELECTOR, value="#horde-logo > .icon")

        if element is None or not element.is_displayed() or not element.is_enabled():
            return False

        return True
    except NoSuchElementException:
        return False


def check_mail_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # ensure the inbox view is present
            ec.element_to_be_clickable(
                (By.CSS_SELECTOR, 'div[class="horde-subnavi-icon inboxImg"]')
            )(driver)
            # ensure sidebar is loaded
            and driver.find_element(By.CLASS_NAME, "imp-sidebar-mbox")
            # ensure inbox view exists
            and driver.find_element(By.CSS_SELECTOR, 'span[id="mailboxName"]')
            is not None
            # ensure the inbox is loaded fully
            and "imp-loading"
            not in driver.find_element(
                By.ID,
                "checkmaillink",
            ).get_attribute("class")
        )
    except NoSuchElementException:
        return False


def check_mail_info_loading(driver: webdriver.Remote):
    try:
        loading_indicators = driver.find_elements_by_class_name("loadingImg")
        # ensure all loading indicators are invisible
        return all(
            ec.invisibility_of_element(element)(driver)
            for element in loading_indicators
        )
    except NoSuchElementException:
        return False


def check_mail_info_window(driver: webdriver.Remote):
    try:
        return (
            # ensure all loading indicators are invisible
            check_mail_info_loading(driver)
            # and reply button is clickable
            and ec.element_to_be_clickable((By.ID, "reply_link"))(driver)
            # and msg data is visible
            and ec.visibility_of_element_located((By.ID, "msgData"))(driver)
        )
    except NoSuchElementException:
        return False


def check_mail_compose_window(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # ensure all loading indicators are invisible
            check_mail_info_loading(driver)
            # and send button usable
            and ec.element_to_be_clickable((By.ID, "send_button"))(driver)
            # and mail body textarea here
            and ec.visibility_of_element_located((By.ID, "composeMessage"))(driver)
        )
    except NoSuchElementException:
        return False


def check_mail_info_write_window(driver: webdriver.Remote):
    # special type of compose window that closes on send
    try:
        return (
            # check is compose windo
            check_mail_compose_window(driver)
            # and writemsg div is present
            and ec.presence_of_element_located((By.ID, "msgData"))(driver)
        )
    except NoSuchElementException:
        return False


class CheckMailExtendedView:
    def __init__(self, subject: Optional[str]):
        self.subject: Optional[str] = subject

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return (
                # ensure loading indicator is invisible
                ec.invisibility_of_element_located((By.ID, "msgLoading"))(driver)
                # and subject text of details view matches
                and driver.find_element_by_xpath(
                    "//div[@id='msgHeadersColl']//span[contains(@class, 'subject')]"
                ).text
                == self.subject
                # and mail body is visible
                and ec.visibility_of_element_located((By.ID, "messageBody"))
            )
            # messageBody
        except NoSuchElementException:
            return False


def check_calendar_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # ensure mini calendar is loaded
            ec.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    '#kronolith-minical * td[class*="kronolith-today"]',
                )
            )(driver)
            # ensure big calendar is loaded
            and ec.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    '#kronolith-month-body * td[class*="kronolith-today"]',
                )
            )(driver)
            # ensure calendar list is loaded
            and ec.visibility_of_element_located(
                (
                    By.ID,
                    "kronolithMyCalendars",
                )
            )(driver)
            and ec.visibility_of_element_located(
                (
                    By.ID,
                    "kronolithAddtasklists",
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_calendar_page_full(driver: webdriver.Remote) -> Optional[Any]:
    """Also checks that the loading icon is not visible.

    This is not part of the normal check as horde 5.2.17 has a bug
    so that the icon gets stuck if you add a calendar event after a delete.
    """
    try:
        return (
            check_calendar_page(driver)
            # and loading indicator is not visible
            and ec.invisibility_of_element_located((By.ID, "kronolithLoading"))(driver)
        )
    except NoSuchElementException:
        return False


def check_calendar_write_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check event input for is visible
            ec.visibility_of_element_located((By.ID, "kronolithEventForm"))(driver)
            # and save button is visible
            and ec.visibility_of_element_located((By.ID, "kronolithEventSave"))(driver)
            # and the title is focused
            # (if we don't wait for this we might loose the first char of the title)
            and driver.find_element_by_id("kronolithEventTitle")
            == driver.switch_to.active_element
        )
    except NoSuchElementException:
        return False


def check_calendar_edit_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check event input dialog
            check_calendar_write_view(driver)
            # and has delete button
            and ec.visibility_of_element_located((By.ID, "kronolithEventDelete"))
            # and save as new button
            and ec.visibility_of_element_located((By.ID, "kronolithEventSaveAsNew"))
        )
    except NoSuchElementException:
        return False


def check_calendar_delete_confirm_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.element_to_be_clickable(
            (
                By.ID,
                "kronolithEventDeleteConfirm",
            )
        )(driver)
    except NoSuchElementException:
        return False


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


def check_input_suggestions_visible(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_any_elements_located(
            (By.XPATH, "//div[@class='KeyNavList']")
        )(driver)
    except NoSuchElementException:
        return False


def check_input_suggestions_invisible(driver: webdriver.Remote) -> Optional[Any]:
    return not check_input_suggestions_visible(driver)


def check_tasks_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_element_located((By.ID, "nag-toggle-my"))(driver)
    except NoSuchElementException:
        return False


def check_new_task_general_tab(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # verify that we are on the general tab
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//li[@id='nag_form_task_tab_1' and @class='horde-active']",
                )
            )(driver)
            # verify input form is ready (due date has current date prefilled)
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//input[@id='due_date' and @value!='']",
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_edit_task_general_tab(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # verify that we are on the general tab
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//li[@id='nag_form_task_tab_1' and @class='horde-active']",
                )
            )(driver)
            # verify input form is ready (due date has current date prefilled)
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//input[@id='due_date' and @value!='']",
                )
            )(driver)
            # and delete button is loaded
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//div[@class='horde-form-buttons']/input[@type='submit' and @value='Delete']",
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_notes_empty_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        # ensure the memos table is not present
        return not ec.presence_of_element_located((By.ID, "memos"))(driver)
    except NoSuchElementException:
        try:
            # ensure the no notes message is present
            return ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//p/em[text()='No notes match the current criteria.']",
                )
            )(driver)
        except NoSuchElementException:
            return False


def check_notes_present_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check either notes table is present
            ec.visibility_of_element_located((By.ID, "memos"))(driver)
            # notes empty message is not displayed
            and not ec.visibility_of_element_located((By.ID, "notes_empty"))(driver)
        )
    except NoSuchElementException:
        return False


def check_notes_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check notes toggle is present
            ec.visibility_of_element_located((By.ID, "mnemo-toggle-my"))(driver)
            and (check_notes_present_page(driver) or check_notes_empty_page(driver))
        )
    except NoSuchElementException:
        return False


def check_new_note_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check title is correct
            CheckTitleContains("New Note")(driver)
            # and notice form is present
            and ec.visibility_of_element_located((By.ID, "mnemo-body"))(driver)
        )
    except NoSuchElementException:
        return False


def check_note_write_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check form is present
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//form[@name='memo']",
                )
            )(driver)
            # and save button is present
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//form[@name='memo']//input[@type='submit' and @value='Save']",
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_edit_note_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check if writable page
            check_note_write_page(driver)
            # and delete button present
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//form[@name='memo']//a[text()='Delete']",
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_file_manager_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_element_located((By.ID, "manager"))
    except NoSuchElementException:
        return False


def check_bookmarks_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_element_located((By.CLASS_NAME, "trean-browse"))(driver)
    except NoSuchElementException:
        return False


def check_filters_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_element_located((By.ID, "filterslist"))(driver)
    except NoSuchElementException:
        return False


def check_horde_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check horde logo visible
            ec.visibility_of_element_located((By.ID, "horde-logo"))(driver)
            # and logout button visible
            and ec.visibility_of_element_located((By.ID, "horde-logout"))(driver)
        )
    except NoSuchElementException:
        return False


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
    try:
        return (
            # is a user pref page
            ec.title_contains("User Preferences")(driver)
            # and identity selection is present
            and ec.visibility_of_element_located((By.ID, "default_identity"))(driver)
        )
    except NoSuchElementException:
        pass
    return False


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


def check_admin_configuration_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check title is correct
            ec.title_contains("Horde Configuration")(driver)
            # and check version button is present
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//input[@value='Check for newer versions' and @type='submit']",
                )
            )(driver)
        )
    except NoSuchElementException:
        pass
    return False


def check_admin_version_check_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check is config page
            check_admin_configuration_page(driver)
            # and version check table is loaded
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//table[@class='horde-table']/thead/tr/th[contains(text(), 'Version Check')]",
                )
            )(driver)
        )
    except NoSuchElementException:
        pass
    return False


def check_admin_php_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check title is correct
            ec.title_contains("PHP Shell")(driver)
            # and check php code text area is present
            and ec.visibility_of_element_located(
                (
                    By.ID,
                    "php",
                )
            )(driver)
        )
    except NoSuchElementException:
        pass
    return False


def check_admin_php_execute_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check is php page
            check_admin_php_page(driver)
            # and check php code highlight is visible
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//div[contains(@class,'syntaxhighlighter') and contains(@class, 'php')]",
                )
            )(driver)
        )
    except NoSuchElementException:
        pass
    return False


def check_admin_sql_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check title is correct
            ec.title_contains("SQL Shell")(driver)
            # and check sql code text area is present
            and ec.visibility_of_element_located(
                (
                    By.ID,
                    "sql",
                )
            )(driver)
        )
    except NoSuchElementException:
        pass
    return False


def check_admin_sql_execute_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check is sql page
            check_admin_sql_page(driver)
            # and sql query text is present
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//h1[@class='header' and text()='Query']",
                )
            )(driver)
            # and check sql result table is present
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//h1[@class='header' and text()='Results']",
                )
            )(driver)
        )
    except NoSuchElementException:
        pass
    return False


def check_admin_cli_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check title is correct
            ec.title_contains("Command Shell")(driver)
            # and check cmd command text area is present
            and ec.visibility_of_element_located(
                (
                    By.ID,
                    "cmd",
                )
            )(driver)
        )
    except NoSuchElementException:
        pass
    return False


def check_admin_cli_execute_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check is cli page
            check_admin_cli_page(driver)
            # and cli command text is present
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//h1[@class='header' and text()='Command:']",
                )
            )(driver)
            # and cli command results are present
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//h1[@class='header' and text()='Results:']",
                )
            )(driver)
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
    try:
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                "//div[@class='GrowlerNotice horde-success']/div[@class='GrowlerNoticeBody']",
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_horde_action_error(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                "//div[@class='GrowlerNotice horde-error']/div[@class='GrowlerNoticeBody']",
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_horde_group_delete_confirm(driver: webdriver.Remote) -> Optional[Any]:
    try:
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
    except NoSuchElementException:
        return False
