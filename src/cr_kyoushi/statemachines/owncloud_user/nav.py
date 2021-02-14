"""Owncloud user selenium navigation operations i.e., actions that move between pages or views"""


from typing import Optional

from pydantic import HttpUrl
from selenium import webdriver
from structlog.stdlib import BoundLogger

from ..core.selenium import (
    driver_wait,
    scroll_to,
)
from .context import Context
from .wait import (
    CheckFileView,
    check_all_files_content,
    check_file_view,
    check_loaded,
    check_owncloud_main,
)


class GoToOwncloud:
    """Go to owncloud action opens the owncloud main page

    The url can be configured"""

    def __init__(self, url: HttpUrl):
        self.url: HttpUrl = url

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        log = log.bind(owncloud_url=self.url)
        if not check_owncloud_main(context.driver):
            log.info("Opening owncloud")
            context.driver.get(self.url)
            driver_wait(context.driver, check_owncloud_main)
            log.info("Opened owncloud")
        else:
            log.info(
                "Already on owncloud",
                current_page=context.driver.current_url,
            )


class NavFilesMenu:
    def __init__(self, data_id: str):
        self.data_id: str = data_id
        self.check = CheckFileView(data_id)

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver

        if check_owncloud_main(driver):
            if not self.check(driver):
                log.info(f"Navigating to {self.data_id}")

                driver.find_element_by_xpath(
                    f"//div[@id='app-navigation']//li[@data-id='{self.data_id}']/a"
                ).click()
                driver_wait(driver, self.check)
                driver_wait(driver, check_loaded)

                log.info(f"Navigated to {self.data_id}")
            else:
                log.info(
                    f"Already on {self.data_id}",
                    current_page=context.driver.current_url,
                )
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action=f"nav_{self.data_id}",
                current_page=driver.current_url,
            )


nav_all_files = NavFilesMenu("files")
nav_favorites = NavFilesMenu("favorites")
nav_sharing_in = NavFilesMenu("sharingin")
nav_sharing_out = NavFilesMenu("sharingout")


class NavBreadCrumbs:
    def __init__(self, level: int):
        self.level: int = level

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver
        if check_all_files_content(driver):
            crumb_link = driver.find_element_by_xpath(
                "//div[@id='app-content-files']//div[@id='controls']//div[contains(@class, 'breadcrumb')]"
                f"/div[contains(@class,'crumb') and position()={self.level}]"
            )

            directory = crumb_link.get_attribute("data-dir")

            # bind dir info to log context
            log = log.bind(directory_path=directory)

            scroll_to(driver, crumb_link)

            log.info("Navigating to directory")
            crumb_link.click()
            driver_wait(driver, check_loaded)
            driver_wait(driver, check_file_view)
            log.info("Navigated to directory")
        else:
            log.error(
                "Invalid action for current page",
                owncloud_action="nav_breadcrumbs",
                current_page=driver.current_url,
            )


nav_root_dir = NavBreadCrumbs(1)
