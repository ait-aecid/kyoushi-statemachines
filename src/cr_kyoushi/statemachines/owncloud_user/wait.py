"""Selenium DOM check functions used to verify and check for the current page state."""
import os
import re
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
            # and everything is loaded
            and check_loaded(driver)
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
            and (
                # and file list is visible
                ec.visibility_of_all_elements_located(
                    (By.XPATH, f"//div[@id='{content_id}']//tbody[@id='fileList']")
                )(driver)
                # or empty file list
                or ec.visibility_of_all_elements_located(
                    (By.XPATH, f"//div[@id='{content_id}']//div[@id='emptycontent']")
                )(driver)
            )
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
    return not check_loading_mask(driver) and check_no_file_busy(driver)


def check_no_file_busy(driver: webdriver.Remote) -> Optional[Any]:
    try:
        content_id = get_current_content_id(driver)
        # check star icons are present
        busy_files = driver.find_elements_by_xpath(
            f"//div[@id='{content_id}']//tbody[@id='fileList']/tr[contains(@class, 'busy')]"
        )
        # check that all busy files are invisible
        return all(ec.invisibility_of_element(busy)(driver) for busy in busy_files)
    except NoSuchElementException:
        # if there are no busy files we are good
        return True


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


def check_no_details_view(driver: webdriver.Remote) -> Optional[Any]:
    try:
        # check details view is visible
        side_bars = driver.find_elements_by_xpath(
            "//div[@id='app-sidebar' and contains(@class,'detailsView')]"
        )
        return all(ec.invisibility_of_element(bar)(driver) for bar in side_bars)
    except NoSuchElementException:
        return True


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


def check_error_page(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check error container is present
            ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//body/div/div/ul/li[contains(@class, 'error')]",
                )
            )(driver)
            # and home hint is present
            and ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    "//p[contains(@class,'hint')]/a",
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


class CheckFileDownloaded:
    def __init__(
        self,
        download_dir: str,
        file: str,
        is_dir: bool = False,
        check_new: bool = True,
    ):
        self.download_dir: str = download_dir

        # configure match patterns for new file check
        # note on chrome this does not work as in auto download mode
        # files are overridden and no "<name> (NR).ext" files are created
        if is_dir:
            name = file
            ext = ".zip"
        else:
            (name, ext) = os.path.splitext(file)
        self.pattern = re.escape(name) + r"( ?\(\d*\))?" + re.escape(ext)
        self.check_new = check_new

        # anti patterns i.e., partial download files
        # that disappear once the download is finished
        self.anti_pattern = [
            # firefox download part file
            self.pattern + re.escape(".part"),
            # chrome download incomplete file
            self.pattern + re.escape(".crdownload"),
        ]

        # set current file count
        self.count: int = self.get_file_count(self.pattern)

    def update_count(self):
        self.count = self.get_file_count(self.pattern)

    def get_file_count(self, pattern: str):
        return len(
            [f for f in os.listdir(self.download_dir) if re.fullmatch(pattern, f)]
        )

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        return (
            # check that no part files are present
            not any(self.get_file_count(anti) > 0 for anti in self.anti_pattern)
            # check that the file is present atleast once
            and (self.get_file_count(self.pattern) > 0)
            # and check that new file was created correctly (optional)
            and (not self.check_new or self.get_file_count(self.pattern) > self.count)
        )


class CheckFileDownloadStatus:
    def __init__(
        self,
        download_dir: str,
        file: str,
        is_dir: bool = False,
        check_new: bool = True,
    ):
        self.download_check = CheckFileDownloaded(download_dir, file, is_dir, check_new)

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        return (
            # check download error
            check_error_page(driver)
            # or downloaded
            or self.download_check(driver)
        )


def check_new_button(driver: webdriver.Remote) -> Optional[Any]:
    try:

        content_id = get_current_content_id(driver)
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                (
                    f"//div[@id='{content_id}']//div[@id='controls']"
                    "//a[contains(@class,'button') and contains(@class, 'new')]"
                ),
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_new_menu(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                "//div[contains(@class,'newFileMenu') and contains(@class,'open')]",
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_new_folder_input(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                (
                    "//div[contains(@class,'newFileMenu') and contains(@class,'open')]"
                    "//input[contains(@id,'-input-folder')]"
                ),
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_upload_progress(driver: webdriver.Remote) -> Optional[Any]:
    try:

        content_id = get_current_content_id(driver)
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                (
                    f"//div[@id='{content_id}']//div[@id='controls']"
                    "//div[@id='uploadprogressbar']"
                ),
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_no_upload_progress(driver: webdriver.Remote) -> Optional[Any]:
    try:

        content_id = get_current_content_id(driver)
        return ec.invisibility_of_element_located(
            (
                By.XPATH,
                (
                    f"//div[@id='{content_id}']//div[@id='controls']"
                    "//div[@id='uploadprogressbar']"
                ),
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_file_exists_dialog(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                (
                    "//div[contains(@class, 'oc-dialog')]"
                    "//div[@id='oc-dialog-fileexists-content']"
                ),
            )
        )(driver)
    except NoSuchElementException:
        return False


def check_no_file_exists_dialog(driver: webdriver.Remote) -> Optional[Any]:
    return not check_file_exists_dialog(driver)


def check_upload_action(driver: webdriver.Remote) -> Optional[Any]:
    return check_file_exists_dialog(driver) or check_upload_progress(driver)


def check_continue_button_enabled(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_all_elements_located(
            (
                By.XPATH,
                (
                    "//div[contains(@class, 'oc-dialog-buttonrow')]"
                    "//button[contains(@class, 'continue') and not(@disabled)]"
                ),
            )
        )(driver)
    except NoSuchElementException:
        return False


class CheckFileDetailsTabAvailable:
    def __init__(self, tab: str):
        self.tab: str = tab

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return (
                # check file details view is active
                check_details_view(driver)
                # and the specified tab is available
                and ec.visibility_of_all_elements_located(
                    (
                        By.XPATH,
                        (
                            "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
                            f"//li[contains(@class,'tabHeader') and @data-tabid='{self.tab}']"
                        ),
                    )
                )(driver)
            )
        except NoSuchElementException:
            return False


check_file_details_comments_available = CheckFileDetailsTabAvailable("commentsTabView")
check_file_details_share_available = CheckFileDetailsTabAvailable("shareTabView")
check_file_details_versions_available = CheckFileDetailsTabAvailable("versionsTabView")


class CheckFileDetailsTab:
    def __init__(self, tab: str):
        self.tab: str = tab

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return (
                # check file details view is active
                check_details_view(driver)
                # and the specified tab is active
                and ec.visibility_of_all_elements_located(
                    (
                        By.XPATH,
                        (
                            "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
                            "//li[contains(@class,'tabHeader') and "
                            f"contains(@class,'selected') and @data-tabid='{self.tab}']"
                        ),
                    )
                )(driver)
                # and the tab content is visible
                and ec.visibility_of_all_elements_located(
                    (
                        By.XPATH,
                        (
                            "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
                            f"//div[contains(@class,'tabsContainer')]//div[@id='{self.tab}']"
                        ),
                    )
                )(driver)
            )
        except NoSuchElementException:
            return False


check_file_details_comments = CheckFileDetailsTab("commentsTabView")
check_file_details_share = CheckFileDetailsTab("shareTabView")
check_file_details_versions = CheckFileDetailsTab("versionsTabView")


class CheckFileDetailsTabLoaded:
    def __init__(self, tab: str):
        self.tab: str = tab
        self.tab_check: CheckFileDetailsTab = CheckFileDetailsTab(tab)

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return (
                # check is the tab
                self.tab_check(driver)
                # and loading indicator is invisible
                and ec.invisibility_of_element_located(
                    (
                        By.XPATH,
                        (
                            "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
                            "//div[contains(@class,'tabsContainer')]"
                            f"//div[@id='{self.tab}']//div[contains(@class,'loading')]"
                        ),
                    )
                )(driver)
            )
        except NoSuchElementException:
            return False


check_file_details_comments_loaded = CheckFileDetailsTabLoaded("commentsTabView")
check_file_details_share_loaded = CheckFileDetailsTabLoaded("shareTabView")
check_file_details_versions_loaded = CheckFileDetailsTabLoaded("versionsTabView")


def check_file_sharable(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return (
            # check shares details view
            check_file_details_share_loaded(driver)
            # and no "no sharing" indicator
            and ec.invisibility_of_element_located(
                (
                    By.XPATH,
                    (
                        "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
                        "//div[contains(@class,'tabsContainer')]"
                        "//div[@id='shareTabView']//div[contains(@class,'noSharingPlaceholder')]"
                    ),
                )
            )(driver)
        )
    except NoSuchElementException:
        return False


def check_user_autocomplete(driver: webdriver.Remote) -> Optional[Any]:
    try:
        return ec.visibility_of_any_elements_located(
            (
                By.XPATH,
                "//ul[starts-with(@id,'ui-id-') and contains(@class, 'ui-autocomplete')]",
            )
        )(driver)
    except NoSuchElementException:
        return False


class CheckSharedUser:
    def __init__(self, user: str):
        self.user: str = user

    def __call__(self, driver: webdriver.Remote) -> Optional[Any]:
        try:
            return ec.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    (
                        "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
                        f"//ul[@id='shareWithList']/li[@data-share-with='{self.user}']"
                    ),
                )
            )(driver)
        except NoSuchElementException:
            return False
