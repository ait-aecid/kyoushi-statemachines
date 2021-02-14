from enum import IntFlag
from typing import (
    Dict,
    List,
    Optional,
)

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from cr_kyoushi.simulation.util import normalize_propabilities

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


def get_current_directory(driver: webdriver.Remote) -> str:
    try:
        return (
            get_current_content(driver)
            .find_element_by_xpath(".//input[@id='dir']")
            .get_attribute("value")
        )
    except NoSuchElementException:
        # if file view is empty
        # then there is no dir
        return ""


def get_unfavored_files(driver: webdriver.Remote) -> List[WebElement]:
    return get_current_content(driver).find_elements_by_xpath(
        ".//tbody[@id='fileList']/tr[not(@data-favorite='true')]"
    )


def get_favored_files(driver: webdriver.Remote) -> List[WebElement]:
    return get_current_content(driver).find_elements_by_xpath(
        ".//tbody[@id='fileList']/tr[@data-favorite='true']"
    )


def is_permissions(
    permissions: OwncloudPermissions,
    check: Optional[int] = None,
) -> bool:
    if check is not None:
        data_permissions: OwncloudPermissions = OwncloudPermissions(check)
        return (
            # either we have all permissions for the object
            data_permissions is OwncloudPermissions.ALL
            # or we have the desired permissions
            or permissions in data_permissions  # type: ignore
        )
    else:
        return False


def has_permissions(tr: WebElement, permissions: OwncloudPermissions) -> bool:
    data_permissions: int = int(tr.get_attribute("data-permissions"))
    return is_permissions(permissions, data_permissions)


def get_data(
    driver: webdriver.Remote,
    data_type: Optional[str] = None,
    exclude_type: bool = False,
    permissions: Optional[OwncloudPermissions] = None,
) -> List[WebElement]:
    """Gets all the data rows matching the given filter attributes.

    !!! Warning
        ownCloud dynamically loads elements as the user scrolls.
        As this will only return already loaded data elements.

    Args:
        driver: The webdriver instance
        data_type: The data type to filter for
        exclude_type: If `True` then the data type filter will be a negative match
        permissions: The permissions the user must have on the data elements

    Returns:
        List of `tr` web elements for the data elements
    """
    condition = ""
    if data_type:
        condition = f"@data-type='{data_type}'"
        if exclude_type:
            condition = f"not({condition})"
        condition = f" and {condition}"

    data = get_current_content(driver).find_elements_by_xpath(
        f".//tbody[@id='fileList']/tr[(@data-share-state='0' or not(@data-share-state)) {condition}]"
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


def get_share_pending(driver: webdriver.Remote) -> List[WebElement]:
    return get_current_content(driver).find_elements_by_xpath(
        ".//tbody[@id='fileList']/tr[contains(@class, 'share-state-pending')]"
    )


def get_shared_users(driver: webdriver.Remote) -> List[WebElement]:
    return driver.find_elements_by_xpath(
        "//div[@id='app-sidebar' and not(contains(@class,'disappear'))]"
        "//ul[@id='shareWithList']/li"
    )


def get_sharable_users(
    driver: webdriver.Remote,
    users: Dict[str, float],
) -> Dict[str, float]:
    shared_users = [
        li.get_attribute("data-share-with") for li in get_shared_users(driver)
    ]

    # remove all users that have the file shared
    current_users = users.copy()
    for key in shared_users:
        if key in current_users:
            del current_users[key]

    # fix the propabilities
    if len(current_users) > 0:
        keys = list(current_users.keys())
        adjusted_p = normalize_propabilities(current_users.values())
        current_users = dict(zip(keys, adjusted_p))
    return current_users


def get_app_content_max_scroll(driver: webdriver.Remote) -> float:
    return float(
        driver.execute_script(
            """
            return (
                document.getElementById("app-content").scrollHeight
                -
                document.getElementById("app-content").clientHeight
            )
            """
        )
    )


def get_app_content_scroll(driver: webdriver.Remote) -> float:
    return float(
        driver.execute_script('return document.getElementById("app-content").scrollTop')
    )


def get_app_content_scroll_space(driver: webdriver.Remote) -> float:
    return get_app_content_max_scroll(driver) - get_app_content_scroll(driver)
