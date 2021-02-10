"""Selenium DOM check functions used to verify and check for the current page state."""

import sys

from typing import (
    Any,
    Callable,
    Optional,
)

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec

from .gather import get_current_content_id


if sys.version_info >= (3, 8):
    from typing import (
        Protocol,
        runtime_checkable,
    )
else:
    from typing_extensions import (
        Protocol,
        runtime_checkable,
    )


@runtime_checkable
class FileCheck(Protocol):
    def __init__(self, fid: str):
        ...

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        ...


def check_login_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check the owncloud disclaimer footer is present
            ec.visibility_of_all_elements_located(
                (By.XPATH, "//footer/p[@class='info']/a[text()='ownCloud']")
            )(driver)
            # and the login form is present
            and ec.visibility_of_all_elements_located(
                (By.XPATH, "//form[@name='login']")
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_login_failed_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check the owncloud disclaimer footer is present
            check_login_page(driver)
            # and the lost password warning is present
            and ec.visibility_of_element_located((By.ID, "lost-password"))(driver)
        )
    except NoSuchElementException:
        return False


def check_logged_in(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check the owncloud header is present
            ec.visibility_of_all_elements_located(
                (By.XPATH, "//div[@id='header']/a[@id='owncloud']")
            )(driver)
            # and the user profile menu is present
            and ec.visibility_of_all_elements_located(
                (By.XPATH, "//div[@id='settings']//span[@id='expandDisplayName']")
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_files_main_menu(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check logged in
            check_logged_in(driver)
            # and the navigation menu is for files features
            and ec.visibility_of_all_elements_located(
                (By.XPATH, "//div[@id='app-navigation']//li[@data-id='files']")
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_owncloud_main(driver: webdriver.Remote) -> Optional[Any]:
    return check_login_page(driver) or check_files_main_menu(driver)


class CheckFileView:
    def __init__(self, data_id: str):
        self.data_id: str = data_id

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return (
                # check nav entry is active
                ec.visibility_of_all_elements_located(
                    (
                        By.XPATH,
                        f"//div[@id='app-navigation']//li[@data-id='{self.data_id}' and contains(@class, 'active')]",
                    )
                )(driver)
                # and selected menus content is active
                and ec.visibility_of_element_located(
                    (By.ID, f"app-content-{self.data_id}")
                )(driver)
            )
        except NoSuchElementException:
            return False


check_all_files_content = CheckFileView("files")
check_favorites_content = CheckFileView("favorites")
check_sharingin_content = CheckFileView("sharingin")
check_sharingout_content = CheckFileView("sharingout")


def check_file_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        content_id = get_current_content_id(driver)
        return (
            # app content is visible
            ec.visibility_of_element_located((By.ID, content_id))(driver)
            # and file list is visible
            and ec.visibility_of_all_elements_located(
                (By.XPATH, f"//div[@id='{content_id}']//tbody[@id='fileList']")
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_loading_mask(driver: webdriver.Remote) -> Optional[Any]:
    try:
        # check if the loading gif mask is visible
        return ec.visibility_of_all_elements_located(
            (By.XPATH, "//div[@class='mask' and contains(@style, 'loading.gif')]")
        )(driver)
    except NoSuchElementException:
        return False


def check_loaded(driver: webdriver.Remote) -> Optional[Any]:
    return not check_loading_mask(driver)


def check_favorite_stars(driver: webdriver.Remote) -> Optional[Any]:
    try:
        content_id = get_current_content_id(driver)
        # check star icons are present
        return (
            # not sharing in view
            content_id != "app-content-sharingin"
            # and some star links are present
            and len(
                driver.find_elements_by_xpath(
                    f"//div[@id='{content_id}']//tbody[@id='fileList']//a[contains(@class, 'action-favorite')]"
                )
            )
            > 0
        )
    except NoSuchElementException:
        return False


class CheckFileBusy:
    def __init__(self, fid: str):
        self.fid: str = fid

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            content_id = get_current_content_id(driver)
            # check star icons are present
            return ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    f"//div[@id='{content_id}']//tbody[@id='fileList']/tr[@data-id='{self.fid}' and contains(@class, 'busy')]",
                )
            )(driver)
        except NoSuchElementException:
            return False


class CheckFileNotBusy:
    def __init__(self, fid: str):
        self.fid: str = fid

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            content_id = get_current_content_id(driver)
            # check star icons are present
            return ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    f"//div[@id='{content_id}']//tbody[@id='fileList']/tr[@data-id='{self.fid}' and not(contains(@class, 'busy'))]",
                )
            )(driver)
        except NoSuchElementException:
            return False


class CheckFileActionsMenu:
    def __init__(self, fid: str, action: str):
        self.fid: str = fid
        self.action: str = action

    # fileActionsMenu
    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            content_id = get_current_content_id(driver)
            tr = driver.find_element_by_xpath(
                f"//div[@id='{content_id}']//tbody[@id='fileList']/tr[@data-id='{self.fid}']"
            )
            actions_menu = tr.find_element_by_xpath(
                ".//div[contains(@class,'fileActionsMenu') and contains(@class,'open')]"
            )
            action = tr.find_element_by_xpath(f".//a[@data-action='{self.action}']")
            # check star icons are present
            return (
                # check actions menu is visible
                ec.visibility_of(actions_menu)
                # and actions button is visible
                and ec.visibility_of(action)
            )
        except NoSuchElementException:
            return False


def check_details_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        # check details view is visible
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                "//div[@id='app-sidebar' and contains(@class,'detailsView') and not(contains(@class,'disappear'))]",
            )
        )(driver)
    except NoSuchElementException:
        return False


class CheckFileAbsent:
    def __init__(self, fid: str):
        self.fid: str = fid

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            content_id = get_current_content_id(driver)
            return driver.find_element_by_xpath(
                f"//div[@id='{content_id}']//tbody[@id='fileList']/tr[@data-id='{self.fid}']"
            )
        except NoSuchElementException:
            return True


class CheckFileDeleted:
    def __init__(self, fid: str):
        self.absent: Callable[[webdriver.Remote], Optional[Any]] = CheckFileAbsent(fid)

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        return self.absent(driver) and check_loaded(driver)
