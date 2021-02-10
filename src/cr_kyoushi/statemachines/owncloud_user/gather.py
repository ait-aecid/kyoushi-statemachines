from enum import IntFlag
from typing import (
    List,
    Optional,
)

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from .context import FileInfo


class OwncloudPermissions(IntFlag):
    READ = 1
    UPDATE = 2
    CREATE = 4
    DELETE = 8
    SHARE = 16
    ALL = 31


def get_file_info(tr: WebElement) -> FileInfo:
    info = FileInfo()
    info.fid = tr.get_attribute("data-id")
    info.file_type = tr.get_attribute("data-type")
    info.size = (
        int(tr.get_attribute("data-size"))
        if tr.get_attribute("data-size") is not None
        else None
    )
    info.name = tr.get_attribute("data-file")
    info.path = tr.get_attribute("data-path")
    info.mime = tr.get_attribute("data-mime")
    info.mtime = int(tr.get_attribute("data-mtime"))
    info.etag = tr.get_attribute("data-etag")
    info.permissions = int(tr.get_attribute("data-permissions"))
    info.share_permissions = int(tr.get_attribute("data-share-permissions"))

    return info


def get_current_content_id(driver: webdriver.Remote) -> str:
    # get id of currently active file menu
    active_menu = driver.find_element_by_xpath(
        "//div[@id='app-navigation']//li[contains(@class,'active')]"
    ).get_attribute("data-id")
    # get content body for active menu
    return f"app-content-{active_menu}"


def get_current_content(driver: webdriver.Remote) -> WebElement:
    # get content body for active menu id
    return driver.find_element_by_id(get_current_content_id(driver))


def get_favored_files(driver: webdriver.Remote) -> List[WebElement]:
    return get_current_content(driver).find_elements_by_xpath(
        ".//tbody[@id='fileList']/tr[not(@data-favorite='true')]"
    )


def get_unfavored_files(driver: webdriver.Remote) -> List[WebElement]:
    return get_current_content(driver).find_elements_by_xpath(
        ".//tbody[@id='fileList']/tr[@data-favorite='true']"
    )


def has_permissions(tr: WebElement, permissions: OwncloudPermissions) -> bool:
    data_permissions: OwncloudPermissions = OwncloudPermissions(
        int(tr.get_attribute("data-permissions"))
    )
    return (
        # either we have all permissions for the object
        data_permissions is OwncloudPermissions.ALL
        # or we have the desired permissions
        or permissions in data_permissions  # type: ignore
    )


def get_data(
    driver: webdriver.Remote,
    data_type: Optional[str] = None,
    exclude_type: bool = False,
    permissions: Optional[OwncloudPermissions] = None,
) -> List[WebElement]:
    condition = ""
    if data_type:
        condition = f"@data-type='{data_type}'"
        if exclude_type:
            condition = f"[not({condition})]"
        else:
            condition = f"[{condition}]"

    data = get_current_content(driver).find_elements_by_xpath(
        f".//tbody[@id='fileList']/tr{condition}"
    )
    if permissions is not None:
        return [d for d in data if has_permissions(d, permissions)]
    return data


def get_dirs(
    driver: webdriver.Remote,
    permissions: Optional[OwncloudPermissions] = None,
) -> List[WebElement]:
    return get_data(
        driver,
        data_type="dir",
        exclude_type=False,
        permissions=permissions,
    )


def get_files(
    driver: webdriver.Remote,
    permissions: Optional[OwncloudPermissions] = None,
) -> List[WebElement]:
    return get_data(
        driver,
        data_type="dir",
        exclude_type=True,
        permissions=permissions,
    )
