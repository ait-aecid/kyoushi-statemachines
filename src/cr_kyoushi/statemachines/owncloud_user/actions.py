"""Owncloud user selenium action operations i.e., actions that use website features etc."""

import random

from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

import numpy as np

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.simulation.util import sleep

from ..core.selenium import (
    TIMEOUT,
    driver_wait,
    scroll_to,
    slow_type,
)
from .context import (
    Context,
    FileInfo,
    UploadInfo,
)
from .gather import (
    OwncloudPermissions,
    get_current_content,
    get_current_directory,
    get_data,
    get_dirs,
    get_favored_files,
    get_file_info,
    get_sharable_users,
    get_share_pending,
    get_shared_users,
    get_unfavored_files,
)
from .wait import (
    CheckFileActionsMenu,
    CheckFileDeleted,
    CheckFileDetailsTab,
    CheckFileDetailsTabAvailable,
    CheckFileDetailsTabLoaded,
    CheckFileDownloadStatus,
    CheckFileNotBusy,
    CheckSharedUser,
    FileCheck,
    check_all_files_content,
    check_continue_button_enabled,
    check_details_view,
    check_error_page,
    check_favorite_stars,
    check_file_exists_dialog,
    check_file_sharable,
    check_file_view,
    check_files_main_menu,
    check_loaded,
    check_login_failed_page,
    check_login_page,
    check_new_button,
    check_new_folder_input,
    check_new_menu,
    check_no_details_view,
    check_no_file_exists_dialog,
    check_no_upload_progress,
    check_sharingin_content,
    check_upload_action,
    check_upload_progress,
    check_user_autocomplete,
)


class LoginToOwncloud:
    def __init__(self, username: str, password: str):
        self.username: str = username
        self.password: str = password

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver

        if check_login_page(driver):
            user_input = driver.find_element_by_id("user")
            password_input = driver.find_element_by_id("password")

            # bind login creds to log context
            log = log.bind(owncloud_user=self.username, owncloud_password=self.password)

            user_input.clear()
            slow_type(user_input, self.username)

            password_input.clear()
            slow_type(password_input, self.password)

            log.info("Logging into owncloud")

            driver.find_element_by_id("submit").click()
            driver_wait(driver, check_files_main_menu)

            log.info("Logged into owncloud")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="login",
                current_page=driver.current_url,
            )


def logout_of_owncloud(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    if check_files_main_menu(driver):
        logout_link = driver.find_element_by_id("logout").get_attribute("href")

        log.info("Logging out of owncloud")

        driver.get(logout_link)
        driver_wait(driver, check_login_page)

        log.info("Logged out of owncloud")
    else:
        log.error(
            "Invalid action for current page",
            owncloud_action="logout",
            current_page=driver.current_url,
        )


class FailLoginToOwncloud:
    def __init__(self, username: str, password: str):
        self.username: str = username
        self.password: str = password

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver
        if check_login_page(driver):
            user_input = driver.find_element_by_id("user")
            password_input = driver.find_element_by_id("password")

            incorrect_password = context.fake.pystr(max_chars=len(self.password))
            # bind login creds to log context
            log = log.bind(
                owncloud_user=self.username,
                owncloud_password=incorrect_password,
            )

            user_input.clear()
            slow_type(user_input, self.username)

            password_input.clear()
            slow_type(password_input, incorrect_password)

            log.info("Failing login into owncloud")

            driver.find_element_by_id("submit").click()
            driver_wait(driver, check_login_failed_page)

            log.info("Failed login into owncloud")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="login",
                current_page=driver.current_url,
            )


def scrollAppRelative(driver: webdriver.Remote, pixel: int):
    driver.execute_script(
        f'document.getElementById("app-content").scrollBy(0, {pixel})'
    )


def _scroll_to_file(log: BoundLogger, driver: webdriver.Remote, element: WebElement):
    log.info("Scrolling to file")
    scroll_to(driver, element)
    # scroll back a bit as the header bar will obscure the file otherwise
    scrollAppRelative(driver, -100)
    log.info("Scrolled to file")


class Scroll:
    def __init__(self, step: int = 50 * 9):
        """
        Args:
            step: The amount of pixels to scroll.
                  Default was chosen as each data entry is 50px and
                  ownCloud dynamically loads entry in sets of 9
        """
        self.step: int = step

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver

        log = log.bind(scroll=self.step)

        if check_file_view(driver):

            log.info("Scrolling")
            scrollAppRelative(driver, self.step)
            log.info("Scrolled")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="scroll",
                current_page=driver.current_url,
            )


def favorite(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    if check_favorite_stars(driver):
        files = get_unfavored_files(driver)

        if len(files):
            file = random.choice(files)
            file_info = get_file_info(file)
            assert file_info.fid is not None

            # bind file info to log context
            log = log.bind(file=file_info)

            star_link = file.find_element_by_xpath(
                ".//a[contains(@class, 'action-favorite')]"
            )

            _scroll_to_file(log, driver, star_link)

            log.info("Favoring file")

            action = ActionChains(driver)
            action.move_to_element(file).move_to_element(star_link)
            action.click(star_link).release().perform()
            driver_wait(driver, CheckFileNotBusy(file_info.fid))

            log.info("Favored file")
        else:
            log.warn("No files to favorite")
    else:
        log.error(
            "Invalid action for current page",
            owncloud_action="favorite",
            current_page=driver.current_url,
        )


def unfavorite(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    if check_favorite_stars(driver):
        files = get_favored_files(driver)
        if len(files):
            file = random.choice(files)
            file_info = get_file_info(file)
            assert file_info.fid is not None

            # bind file info to log context
            log = log.bind(file=file_info)

            star_link = file.find_element_by_xpath(
                ".//a[contains(@class, 'action-favorite')]"
            )

            _scroll_to_file(log, driver, star_link)

            log.info("Unfavorite file")

            action = ActionChains(driver)
            action.move_to_element(file).move_to_element(star_link)
            action.click(star_link).release().perform()
            driver_wait(driver, CheckFileNotBusy(file_info.fid))

            log.info("Unfavored file")
        else:
            log.warn("No files to unfavorite")
    else:
        log.error(
            "Invalid action for current page",
            owncloud_action="unfavorite",
            current_page=driver.current_url,
        )


def open_directory(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver

    if check_file_view(driver):
        dirs = get_dirs(driver)
        if len(dirs) > 0:
            directory = random.choice(dirs)

            dir_info = get_file_info(directory)

            # bind dir info to log context
            log = log.bind(directory=dir_info)

            dir_link = directory.find_element_by_xpath(
                ".//td[contains(@class,'filename')]/a[contains(@class,'name')]/span[contains(@class,'nametext')]"
            )

            _scroll_to_file(log, driver, dir_link)

            log.info("Opening directory")
            ActionChains(driver).click(dir_link).perform()
            driver_wait(driver, check_loaded)
            driver_wait(driver, check_all_files_content)

            log.info("Opened directory")
        else:
            log.warn("No directories to open")
    else:
        log.error(
            "Invalid action for current page",
            owncloud_action="open_directory",
            current_page=driver.current_url,
        )


class MenuActionBase:
    def __init__(
        self,
        name: str,
        action: str,
        required_permissions: OwncloudPermissions,
        data_type: Optional[str] = None,
        exclude_type: bool = False,
    ):
        self.name: str = name
        self.action: str = action
        self.permissions: OwncloudPermissions = required_permissions
        self.data_type: Optional[str] = data_type
        self.exclude_type: bool = exclude_type

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver

        if check_file_view(driver):
            data = get_data(
                driver,
                data_type=self.data_type,
                exclude_type=self.exclude_type,
                permissions=self.permissions,
            )
            if len(data) > 0:
                obj = random.choice(data)

                context.owncloud.file = get_file_info(obj)
                obj_info = context.owncloud.file
                assert obj_info.fid is not None

                # bind obj info to log context
                log = log.bind(file=obj_info, menu_action=self.action)

                ellipsis = obj.find_element_by_xpath(".//a[@data-action='menu']")

                _scroll_to_file(log, driver, ellipsis)

                ellipsis.click()
                driver_wait(driver, CheckFileActionsMenu(obj_info.fid, self.action))

                log.info("Starting menu action")

                self._pre_hook(log, driver, obj, obj_info)

                obj.find_element_by_xpath(
                    (
                        ".//div[contains(@class,'fileActionsMenu') and contains(@class,'open')]"
                        f"//a[@data-action='{self.action}']"
                    )
                ).click()

                self._post_hook(log, driver, obj, obj_info)

                log.info("Finished menu action")
            else:
                log.warn(f"No entries to {self.name}")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="menu_action_{self.name}",
                current_page=driver.current_url,
            )

    def _pre_hook(
        self,
        log: BoundLogger,
        driver: webdriver.Remote,
        obj: WebElement,
        obj_info: FileInfo,
    ):
        pass

    def _post_hook(
        self,
        log: BoundLogger,
        driver: webdriver.Remote,
        obj: WebElement,
        obj_info: FileInfo,
    ):
        pass


class MenuAction(MenuActionBase):
    def __init__(
        self,
        name: str,
        action: str,
        required_permissions: OwncloudPermissions,
        check_function: Union[
            Type[FileCheck], Callable[[webdriver.Remote], Optional[Any]]
        ],
        data_type: Optional[str] = None,
        exclude_type: bool = False,
    ):
        super().__init__(name, action, required_permissions, data_type, exclude_type)
        self.check: Union[
            Type[FileCheck], Callable[[webdriver.Remote], Optional[Any]]
        ] = check_function

    def _pre_hook(
        self,
        log: BoundLogger,
        driver: webdriver.Remote,
        obj: WebElement,
        obj_info: FileInfo,
    ):
        assert obj_info.fid is not None
        # if we got a check that works with a specific file
        # then we need to init it before usage
        self.check = (
            self.check(obj_info.fid)
            if isinstance(self.check, type) and issubclass(self.check, FileCheck)
            else self.check
        )

    def _post_hook(
        self,
        log: BoundLogger,
        driver: webdriver.Remote,
        obj: WebElement,
        obj_info: FileInfo,
    ):
        driver_wait(driver, self.check)


show_details = MenuAction(
    name="details",
    action="Details",
    required_permissions=OwncloudPermissions.READ,
    check_function=check_details_view,
)

delete = MenuAction(
    name="delete",
    action="Delete",
    required_permissions=OwncloudPermissions.DELETE,
    check_function=CheckFileDeleted,
)

delete_file = MenuAction(
    name="delete",
    action="Delete",
    data_type="dir",
    exclude_type=True,
    required_permissions=OwncloudPermissions.DELETE,
    check_function=CheckFileDeleted,
)

delete_directory = MenuAction(
    name="delete",
    action="Delete",
    data_type="dir",
    exclude_type=False,
    required_permissions=OwncloudPermissions.DELETE,
    check_function=CheckFileDeleted,
)


class Download(MenuActionBase):
    def __init__(
        self,
        download_dir: str,
        data_type: Optional[str] = None,
        exclude_type: bool = False,
        check_new: bool = False,
        check_wait: Union[ApproximateFloat, float] = 2.0,
    ):
        super().__init__(
            "download",
            "Download",
            OwncloudPermissions.READ,
            data_type,
            exclude_type,
        )
        self.download_dir: str = download_dir
        self.check: Optional[CheckFileDownloadStatus] = None
        self.check_new: bool = check_new
        self.check_wait: Union[ApproximateFloat, float] = check_wait

    def _pre_hook(
        self,
        log: BoundLogger,
        driver: webdriver.Remote,
        obj: WebElement,
        obj_info: FileInfo,
    ):
        assert obj_info.name is not None
        # if we got a check that works with a specific file
        # then we need to init it before usage
        self.check = CheckFileDownloadStatus(
            self.download_dir,
            obj_info.name,
            obj_info.file_type == "dir",
            self.check_new,
        )

    def _post_hook(
        self,
        log: BoundLogger,
        driver: webdriver.Remote,
        obj: WebElement,
        obj_info: FileInfo,
    ):
        driver_wait(driver, check_loaded)
        if self.check is not None:
            sleep(self.check_wait)
            driver_wait(driver, self.check)
            # check if the download failed
            if check_error_page(driver):
                log.info("Download failed")

                # recover from error page by going back to previous page
                log.info("Going back")
                driver.back()
                log.info("Went back")
            else:
                log.info("Downloaded file")


class DownloadFile(Download):
    def __init__(
        self,
        download_dir,
        check_new: bool = False,
        check_wait: Union[ApproximateFloat, float] = 2.0,
    ):
        super().__init__(
            download_dir,
            data_type="dir",
            exclude_type=True,
            check_new=check_new,
            check_wait=check_wait,
        )


class DownloadDir(Download):
    def __init__(
        self,
        download_dir,
        check_new: bool = False,
        check_wait: Union[ApproximateFloat, float] = 2.0,
    ):
        super().__init__(
            download_dir,
            data_type="dir",
            exclude_type=False,
            check_new=check_new,
            check_wait=check_wait,
        )


def create_directory(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver

    if check_file_view(driver) and check_new_button(driver):
        names: List[str] = [d.get_attribute("data-file") for d in get_data(driver)]
        dir_name: Optional[str] = None
        while dir_name is None or dir_name in names:
            dir_name = context.fake.word()

        current_dir = get_current_directory(driver)

        # bind dir info to log context
        log = log.bind(current_dir=current_dir, directory=dir_name)

        get_current_content(driver).find_element_by_xpath(
            ".//div[@id='controls']//a[contains(@class,'button') and contains(@class, 'new')]"
        ).click()
        driver_wait(driver, check_new_menu)

        driver.find_element_by_xpath(
            "//div[contains(@class,'newFileMenu') and contains(@class,'open')]"
            "//a[contains(@class,'menuitem') and @data-action='folder']"
        ).click()
        driver_wait(driver, check_new_folder_input)

        folder_input = driver.find_element_by_xpath(
            "//div[contains(@class,'newFileMenu') and contains(@class,'open')]"
            "//input[contains(@id,'-input-folder')]"
        )

        folder_input.clear()
        slow_type(folder_input, dir_name)

        log.info("Creating directory")

        # folder_input.send_keys("\n")
        folder_input.submit()
        driver_wait(driver, check_loaded)

        log.info("Created directory")
    else:
        log.error(
            "Invalid action for current page",
            owncloud_action="create_directory",
            current_page=driver.current_url,
        )


class ProcessShare:
    def __init__(self, accept: bool = True):
        self.action: str = "Accept" if accept else "Reject"

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver

        if check_sharingin_content(driver):
            pending = get_share_pending(driver)
            if len(pending) > 0:
                share_in: WebElement = random.choice(pending)
                share_info = get_file_info(share_in)

                action_button = share_in.find_element_by_xpath(
                    f".//a[@data-action='{self.action}']"
                )

                # bind share info to log context
                log = log.bind(file=share_info, action=self.action)

                _scroll_to_file(log, driver, action_button)

                log.info("Processing pending share")

                action = ActionChains(driver)
                action.move_to_element(action_button).click().perform()

                driver_wait(driver, check_loaded)

                log.info("Processed pending share")
            else:
                log.warn("No pending shares")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="process_share",
                current_page=driver.current_url,
            )


accept_share = ProcessShare(accept=True)
decline_share = ProcessShare(accept=False)


class UploadFile:
    def __init__(self, upload_files: Dict[str, float]):
        self.upload_files: Dict[str, float] = upload_files

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver

        if check_file_view(driver) and check_new_button(driver):
            upload_info: UploadInfo = context.owncloud.upload
            # clear upload info
            upload_info.clear()
            upload_info.directory = get_current_directory(driver)
            upload_file: Path = Path(
                np.random.choice(
                    a=list(self.upload_files.keys()),
                    p=list(self.upload_files.values()),
                )
            )
            # set file info
            upload_info.source = str(upload_file.parent)
            upload_info.name = upload_file.name

            # bind upload info
            log = log.bind(upload=upload_info)

            upload_input = get_current_content(driver).find_element_by_xpath(
                ".//input[@id='file_upload_start']"
            )
            log.info("Starting file upload")

            upload_input.send_keys(str(upload_file.absolute()))
            driver_wait(driver, check_upload_action)

            log.info("Started file upload")

            if check_file_exists_dialog(driver):
                log.info("Uploaded file exists")
            else:
                log.info("Uploaded file")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="upload_file",
                current_page=driver.current_url,
            )


class UploadProcessReplace:
    def __init__(self, keep_new: bool = True, keep_old: bool = True):
        self.keep_new: bool = keep_new
        self.keep_old: bool = keep_old

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver
        upload_info: UploadInfo = context.owncloud.upload
        upload_info.keep_new = self.keep_new
        upload_info.keep_old = self.keep_old

        # bind upload info
        log = log.bind(upload=upload_info)

        if check_file_exists_dialog(driver):

            # select the check boxes
            if self.keep_new:
                log.info("Finishing upload")

                new_check = driver.find_element_by_xpath(
                    "//div[contains(@class, 'oc-dialog')]"
                    "//div[@id='oc-dialog-fileexists-content']"
                    "//input[@id='checkbox-allnewfiles']"
                )
                # need to use JS click since the checkbox is
                # considered offscreen by selenium
                driver.execute_script("arguments[0].click()", new_check)

            if self.keep_old:
                old_check = driver.find_element_by_xpath(
                    "//div[contains(@class, 'oc-dialog')]"
                    "//div[@id='oc-dialog-fileexists-content']"
                    "//input[@id='checkbox-allexistingfiles']"
                )
                # need to use JS click since the checkbox is
                # considered offscreen by selenium
                driver.execute_script("arguments[0].click()", old_check)

            # confirm the dialog
            if self.keep_new:
                # wait for continue button to enable
                driver_wait(driver, check_continue_button_enabled)
                button = driver.find_element_by_xpath(
                    "//div[contains(@class, 'oc-dialog-buttonrow')]"
                    "//button[contains(@class, 'continue')]"
                )

                ActionChains(driver).move_to_element(button).click(button).perform()
                # wait for progress bar to appear
                driver_wait(driver, check_upload_progress)
                # and then wait for complete
                driver_wait(driver, check_no_upload_progress)
                log.info("Uploaded file")
            # if keep_new == False the result will always lead to upload cancel
            # even if keep_old == True
            else:
                log.info("Canceling file upload")

                driver.find_element_by_xpath(
                    "//div[contains(@class, 'oc-dialog-buttonrow')]"
                    "//button[contains(@class, 'cancel')]"
                ).click()
                driver_wait(driver, check_no_file_exists_dialog)
                driver_wait(driver, check_loaded)
                log.info("Cancelled file upload")

        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="upload_process_replace",
                current_page=driver.current_url,
            )


upload_keep_both = UploadProcessReplace(keep_new=True, keep_old=True)
upload_keep_new = UploadProcessReplace(keep_new=True, keep_old=False)
upload_keep_old = UploadProcessReplace(keep_new=False, keep_old=True)
upload_cancel = UploadProcessReplace(keep_new=False, keep_old=False)


def close_details(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver

    # bind obj info to log context
    log = log.bind(file=context.owncloud.file)

    if check_details_view(driver):
        close_button = driver.find_element_by_xpath(
            "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
            "/a[@alt='Close']"
        )

        log.info("Closing file details")
        close_button.click()
        driver_wait(driver, check_no_details_view)
        log.info("Closed file details")
    else:
        log.error(
            "Invalid action for current page",
            owncloud_action="close_details",
            current_page=driver.current_url,
        )


class OpenDetailsTab:
    def __init__(self, tab: str):
        self.tab: str = tab
        self.check: CheckFileDetailsTab = CheckFileDetailsTab(tab)
        self.loaded: CheckFileDetailsTabLoaded = CheckFileDetailsTabLoaded(tab)
        self.available: CheckFileDetailsTabAvailable = CheckFileDetailsTabAvailable(tab)

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver
        file_info: FileInfo = context.owncloud.file

        # bind obj info to log context
        log = log.bind(file=file_info, tab=self.tab)

        if check_details_view(driver) and self.available(driver):
            if not self.check(driver):
                tab_li = driver.find_element_by_xpath(
                    "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
                    "//li[contains(@class,'tabHeader') and "
                    f"@data-tabid='{self.tab}']"
                )

                log.info("Opening details tab")

                tab_li.click()
                driver_wait(driver, self.check)
                try:
                    driver_wait(driver, self.loaded, timeout=TIMEOUT / 2)
                    log.info("Opened details tab")
                except TimeoutException:
                    log.info("Details tab did not load")
            else:
                log.info("Tab already open")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="view_details_tab",
                current_page=driver.current_url,
            )


open_details_comments = OpenDetailsTab("commentsTabView")
open_details_share = OpenDetailsTab("shareTabView")
open_details_versions = OpenDetailsTab("versionsTabView")


class ShareFile:
    def __init__(self, users: Dict[str, float]):
        self.users = users

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver
        file_info: FileInfo = context.owncloud.file

        # bind obj info to log context
        log = log.bind(file=file_info)

        if check_file_sharable(driver):

            sharable_users = get_sharable_users(driver, self.users)
            if len(sharable_users) > 0:
                user = np.random.choice(
                    a=list(sharable_users.keys()),
                    p=list(sharable_users.values()),
                )

                # bind user info to log context
                log = log.bind(user=user)

                user_input = driver.find_element_by_xpath(
                    "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
                    "//div[@id='shareTabView']//input[starts-with(@id, 'shareWith-view')]"
                )

                log.info("Sharing file")

                slow_type(user_input, user)
                # wait for autocomplete to show
                # (cannot insert otherwise)
                driver_wait(driver, check_user_autocomplete)
                user_input.send_keys("\n")
                # wait for user to appear in the share list
                driver_wait(driver, CheckSharedUser(user))

                log.info("Shared file")

            else:
                log.warn("No user to share")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="share_file",
                current_page=driver.current_url,
            )
            from structlog import get_context

            tid = get_context(log)["transition_id"]
            log.error("Saved screen shot")
            driver.save_screenshot(f"/tmp/asddfasdadasdasdad/{tid}.png")


def unshare_file(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    file_info: FileInfo = context.owncloud.file

    # bind obj info to log context
    log = log.bind(file=file_info)

    if check_file_sharable(driver):

        shared_users = get_shared_users(driver)
        if len(shared_users) > 0:
            user_li: WebElement = random.choice(shared_users)
            user = user_li.get_attribute("data-share-with")

            # bind user info to log context
            log = log.bind(user=user)

            log.info("Scrolling to share user")
            scroll_to(driver, user_li)
            log.info("Scrolled to share user")

            log.info("Unsharing file")

            user_li.find_element_by_xpath(".//a[contains(@class,'unshare')]").click()
            # wait for user to disappear from share list
            driver_wait(driver, lambda driver: not CheckSharedUser(user)(driver))

            log.info("Unshared file")

        else:
            log.warn("No user to unshare")
    else:
        log.error(
            "Invalid action for current page",
            owncloud_action="unshare_file",
            current_page=driver.current_url,
        )
