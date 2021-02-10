"""Owncloud user selenium action operations i.e., actions that use website features etc."""

import random

from typing import (
    Any,
    Callable,
    Optional,
    Type,
    Union,
)

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from structlog.stdlib import BoundLogger

from ..core.selenium import (
    driver_wait,
    scroll_to,
    slow_type,
)
from .context import Context
from .gather import (
    OwncloudPermissions,
    get_data,
    get_dirs,
    get_favored_files,
    get_file_info,
    get_unfavored_files,
)
from .wait import (
    CheckFileActionsMenu,
    CheckFileDeleted,
    CheckFileNotBusy,
    FileCheck,
    check_all_files_content,
    check_details_view,
    check_favorite_stars,
    check_file_view,
    check_files_main_menu,
    check_loaded,
    check_login_failed_page,
    check_login_page,
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


def favorite_file(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    if check_favorite_stars(driver):
        files = get_favored_files(driver)
        print(len(files))
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
            action.click(star_link).perform()
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


def unfavorite_file(
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

            log.info("Unfavorite file")

            action = ActionChains(driver)
            action.move_to_element(file).move_to_element(star_link)
            action.click(star_link).perform()
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
            ActionChains(driver).double_click(dir_link).perform()
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


class MenuAction:
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
        self.name: str = name
        self.action: str = action
        self.permissions: OwncloudPermissions = required_permissions
        self.data_type: Optional[str] = data_type
        self.exclude_type: bool = exclude_type
        self.check: Union[
            Type[FileCheck], Callable[[webdriver.Remote], Optional[Any]]
        ] = check_function

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

                obj_info = get_file_info(obj)
                assert obj_info.fid is not None

                # bind obj info to log context
                log = log.bind(file=obj_info, menu_action=self.action)

                ellipsis = obj.find_element_by_xpath(".//a[@data-action='menu']")

                _scroll_to_file(log, driver, ellipsis)

                ellipsis.click()
                driver_wait(driver, CheckFileActionsMenu(obj_info.fid, self.action))

                log.info("Starting menu action")

                obj.find_element_by_xpath(
                    (
                        ".//div[contains(@class,'fileActionsMenu') and contains(@class,'open')]"
                        f"//a[@data-action='{self.action}']"
                    )
                ).click()

                # if we got a check that works with a specific file
                # then we need to init it before usage
                if isinstance(self.check, type) and issubclass(self.check, FileCheck):
                    driver_wait(driver, self.check(obj_info.fid))
                else:
                    driver_wait(driver, self.check)

                log.info("Finished menu action")
            else:
                log.warn(f"No entries to {self.name}")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="menu_action_{self.name}",
                current_page=driver.current_url,
            )


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

download = MenuAction(
    name="download",
    action="Download",
    required_permissions=OwncloudPermissions.READ,
    check_function=(lambda x: True),
)

download_file = MenuAction(
    name="download",
    action="Download",
    data_type="dir",
    exclude_type=True,
    required_permissions=OwncloudPermissions.READ,
    check_function=(lambda x: True),
)

download_dir = MenuAction(
    name="download",
    action="Download",
    data_type="dir",
    exclude_type=False,
    required_permissions=OwncloudPermissions.READ,
    check_function=(lambda x: True),
)
