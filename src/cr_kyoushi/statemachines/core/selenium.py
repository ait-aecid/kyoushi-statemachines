"""
This module contains configuration and utility functions for using Selenium webdrivers
as part of simulations.
"""
import os
import sys
import time

from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from faker import Faker
from pydantic import (
    AnyUrl,
    BaseModel,
    Field,
    PositiveInt,
    SecretStr,
    root_validator,
    validator,
)
from pydantic.errors import (
    EnumMemberError,
    PathNotADirectoryError,
)
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import (
    Proxy,
    ProxyType,
)
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.opera.options import Options as OperaOptions
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.support.wait import (
    POLL_FREQUENCY,
    WebDriverWait,
)
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.manager import DriverManager
from webdriver_manager.microsoft import (
    EdgeChromiumDriverManager,
    IEDriverManager,
)
from webdriver_manager.opera import OperaDriverManager
from webdriver_manager.utils import ChromeType

from cr_kyoushi.simulation.model import (
    ApproximateFloat,
    LogLevel,
    WorkSchedule,
)
from cr_kyoushi.simulation.states import State

from .config import (
    BasicStatemachineConfig,
    FakerContext,
    FakerContextModel,
)
from .sm import FakerStatemachine
from .util import filter_none_keys


if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol

TIMEOUT = 120

__all__ = [
    "WebdriverType",
    "WebdriverManagerConfig",
    "SeleniumConfig",
    "get_webdriver_manager",
    "install_webdriver",
    "get_webdriver",
]


class WebdriverType(str, Enum):
    """Enum for the different Selenium webdriver types"""

    CHROME = "CHROME"
    CHROMIUM = "CHROMIUM"
    FIREFOX = "FIREFOX"
    IE = "IE"
    EDGE = "EDGE"
    OPERA = "OPERA"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, val: str) -> "WebdriverType":
        """Custom case insensitive value enum validator"""
        if isinstance(val, WebdriverType):
            return val

        if isinstance(val, str):
            try:
                enum_v = WebdriverType(val.upper())
            except ValueError:
                raise EnumMemberError(enum_values=list(WebdriverType))
            return enum_v
        raise EnumMemberError(enum_values=list(WebdriverType))


class WebdriverManagerConfig(BaseModel):
    """Configuration class for the selenium webdriver manager"""

    path: Optional[Path] = Field(
        None,
        description="The webdriver cache path",
    )

    url: Optional[AnyUrl] = Field(
        None,
        description="The base URL to download the webdriver from. (e.g., https://chromedriver.storage.googleapis.com)",
    )

    latest_release_url: Optional[AnyUrl] = Field(
        None,
        description="The URL for the latest version of the webdriver",
    )

    log_level: LogLevel = Field(
        LogLevel.INFO,
        description="Log level for the webdriver manager.",
    )

    cache_valid_range: PositiveInt = Field(
        1,
        description="The validity of the driver cache in days.",
    )


class SeleniumProxyConfig(BaseModel):
    """Selenium webdriver proxy configuration"""

    enabled: bool = Field(
        False,
        description="If a proxy should be used or not",
    )

    host: str = Field(
        "localhost",
        description="The proxy host",
    )

    port: PositiveInt = Field(
        8080,
        description="The proxy port",
    )

    socks: bool = Field(
        False,
        description="If a socks proxy should be used instead of a HTTP proxy",
    )

    socks_version: PositiveInt = Field(
        5,
        description="The SOCKS protocol version to use",
    )

    username: Optional[str] = Field(
        None,
        description="The socks username to use for authentication",
    )

    password: Optional[SecretStr] = Field(
        None,
        description="The socks password to use for authentication",
    )


class SeleniumDownloadConfig(BaseModel):
    """Configuration class for the selenium drivers download settings"""

    prompt: bool = Field(
        True,
        description="If the download dialog should be shown or not",
    )

    path: Optional[Path] = Field(
        None,
        description="The download directory to use",
    )

    autosave: List[str] = Field(
        [],
        description="List of mime type to autosave (required for firefox prompt=False)",
    )

    @validator("path")
    def validate_dir(cls, value: Path) -> Path:
        if value.exists() and not value.is_dir():
            raise PathNotADirectoryError(path=value)

        return value

    @root_validator()
    def validate_download_path(cls, values):
        assert (
            values.get("prompt", True) or values.get("path", None) is not None
        ), "Download path must be set if prompt is `False`"
        return values


class SeleniumConfig(BaseModel):
    """Configuration class for selenium drivers"""

    driver_manager: WebdriverManagerConfig = Field(
        WebdriverManagerConfig(),
        description="Configuration for the webdriver manager used to download and install webdrivers.",
    )

    type: WebdriverType = Field(
        WebdriverType.FIREFOX,
        description="The webdriver type to use.",
    )

    accept_insecure_ssl: bool = Field(
        True,
        description="If the browser should accept insecure SSL connections or not.",
    )

    headless: bool = Field(
        False,
        description="If the browser should be run in headless mode or not.",
    )

    proxy: SeleniumProxyConfig = Field(
        SeleniumProxyConfig(),
        description="The proxy configuration to use for the webdriver",
    )

    download: SeleniumDownloadConfig = Field(
        SeleniumDownloadConfig(),
        description="The file download configuration for the webdriver",
    )

    implicit_wait: float = Field(
        0,
        description="The implicit time the selenium driver waits when looking up an element",
    )

    window_x_position = int = Field(
        0,
        description="The windows x-axis position in pixels",
    )

    window_y_position = int = Field(
        0,
        description="The windows y-axis position in pixels",
    )

    window_width = int = Field(
        800,
        description="The windows width in pixels",
    )

    window_height = int = Field(
        600,
        description="The windows height in pixels",
    )

    arguments: List[str] = Field(
        [],
        description="Additional commandline arguments for the webdriver",
    )

    capabilities: Dict[str, Any] = Field(
        {},
        description="List of desired capabilities",
    )

    @validator("arguments")
    def edge_no_arguments(cls, arguments, values, **kwargs):
        # only validate if we have a valid type
        if (
            "type" in values
            and values["type"] == WebdriverType.EDGE
            and len(arguments) > 0
        ):
            raise ValueError("Edge does not support webdriver arguments")
        return arguments

    @validator("headless")
    def ie_edge_no_headless(cls, headless, values, **kwargs):
        # only validate if we have a valid type
        if (
            "type" in values
            and (
                values["type"] == WebdriverType.IE
                or values["type"] == WebdriverType.EDGE
            )
            and headless
        ):
            raise ValueError("Edge and IE do not support headless mode")
        return headless


"""Mapping of driver types to their selenium classes"""
_MANAGER_MAP = {
    WebdriverType.CHROME: {
        "manager": ChromeDriverManager,
        "manager_options": {},
        "driver": webdriver.Chrome,
        "driver_options": webdriver.ChromeOptions(),
    },
    WebdriverType.CHROMIUM: {
        "manager": ChromeDriverManager,
        "manager_options": {"chrome_type": ChromeType.CHROMIUM},
        "driver": webdriver.Chrome,
        "driver_options": webdriver.ChromeOptions(),
    },
    WebdriverType.FIREFOX: {
        "manager": GeckoDriverManager,
        "manager_options": {},
        "driver": webdriver.Firefox,
        "driver_options": webdriver.FirefoxOptions(),
    },
    WebdriverType.IE: {
        "manager": IEDriverManager,
        "manager_options": {},
        "driver": webdriver.Ie,
        "driver_options": webdriver.IeOptions(),
    },
    WebdriverType.EDGE: {
        "manager": EdgeChromiumDriverManager,
        "manager_options": {},
        "driver": webdriver.Edge,
        "driver_options": EdgeOptions(),
    },
    WebdriverType.OPERA: {
        "manager": OperaDriverManager,
        "manager_options": {},
        "driver": webdriver.Opera,
        "driver_options": OperaOptions(),
    },
}


def get_webdriver_manager(config: SeleniumConfig) -> DriverManager:
    """Gets and configures a webdriver manager instance for the given selenium config.

    Args:
        config: The selenium config

    Returns:
        Configured `DriverManager` instance
    """
    manager_info = _MANAGER_MAP[config.type]

    manager_options = dict(manager_info["manager_options"])
    manager_options.update(filter_none_keys(config.driver_manager.dict()))
    # convert log level to int
    manager_options["log_level"] = int(manager_options["log_level"])

    return manager_info["manager"](**manager_options)


def install_webdriver(config: SeleniumConfig) -> str:
    """Installs the configured Selenium driver and returns the install path.

    Args:
        config: The Selenium configuration determining which driver gets installed and how.

    Returns:
        Path to the installed driver binary.
    """
    manager = get_webdriver_manager(config)
    return manager.install()


def chrome_enable_download_headless(driver: webdriver.Remote, download_dir: str):
    driver.command_executor._commands["send_command"] = (
        "POST",
        "/session/$sessionId/chromium/send_command",
    )
    params = {
        "cmd": "Page.setDownloadBehavior",
        "params": {"behavior": "allow", "downloadPath": download_dir},
    }
    driver.execute("send_command", params)


def get_webdriver(
    config: SeleniumConfig,
    driver_path: Optional[str] = None,
) -> webdriver.Remote:
    """Gets and configures a Selenium webdriver instance based on the given configuration.

    Args:
        config: The selenium configuration

    Returns:
        The initialized and configured Selenium webdriver instance
    """
    driver_info = _MANAGER_MAP[config.type]
    fox_profile = None

    # install webdriver and get path if not already given
    if driver_path is None:
        driver_path = install_webdriver(config)

    options = driver_info["driver_options"]

    # configure webdriver capabilities
    for cap, cap_val in config.capabilities.items():
        options.set_capability(cap, cap_val)

    # configure webdriver arguments
    for arg in config.arguments:
        options.add_argument(arg)

    if config.type != WebdriverType.EDGE and config.type != WebdriverType.IE:
        # configure headless mode via driver options
        options.set_headless(config.headless)

    # configure SSL cert insecure option
    options.set_capability("acceptInsecureCerts", config.accept_insecure_ssl)

    # configure proxy
    if config.proxy.enabled:
        proxy_url = f"{config.proxy.host}:{str(config.proxy.port)}"
        proxy = Proxy()

        proxy.proxy_type = ProxyType.MANUAL
        proxy.autodetect = False
        proxy.ftp_proxy = proxy_url
        if config.proxy.socks:
            proxy.socks_proxy = proxy_url
            # auth settings
            if config.proxy.username is not None and config.proxy.password is not None:
                proxy.socks_username = config.proxy.username
                proxy.socks_password = config.proxy.password
        else:
            proxy.http_proxy = proxy_url
            proxy.ssl_proxy = proxy_url

        # options: webdriver.ChromeOptions
        # apply proxy settings
        proxy.add_to_capabilities(options.capabilities)
        if config.proxy.socks:
            # need to manually set the socksVersion since
            # the proxy config object does not expose the setting
            options.capabilities["proxy"]["socksVersion"] = config.proxy.socks_version

    download_path = (
        # set download path if we have one
        str(config.download.path.absolute())
        # otherwise set empty string
        if config.download.path is not None
        else ""
    )
    if not config.download.prompt:

        # create download directory
        os.makedirs(download_path, exist_ok=True)

        if config.type == WebdriverType.CHROME or config.type == WebdriverType.CHROMIUM:
            download_options = webdriver.ChromeOptions()
            download_options
            options.experimental_options.setdefault("prefs", {}).update(
                {
                    "download.default_directory": download_path,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "download.download_restrictions": 0,
                    "safebrowsing_for_trusted_sources_enabled": False,
                    "safebrowsing.enabled": False,
                }
            )
        elif config.type == WebdriverType.FIREFOX:
            fox_profile = webdriver.FirefoxProfile()
            fox_profile.set_preference(
                "browser.download.folderList", 2
            )  # custom location
            fox_profile.set_preference(
                "browser.download.manager.showWhenStarting", False
            )
            fox_profile.set_preference("browser.download.dir", download_path)
            fox_profile.set_preference("browser.download.manager.alertOnEXEOpen", False)
            fox_profile.set_preference("browser.download.manager.closeWhenDone", False)
            fox_profile.set_preference(
                "browser.download.manager.focusWhenStarting", False
            )
            # application/octet-stream,application/vnd.ms-excel
            fox_profile.set_preference(
                "browser.helperApps.neverAsk.saveToDisk",
                ",".join(config.download.autosave),
            )
            # need to disable pdf viewer as well
            fox_profile.set_preference("pdfjs.disabled", True)

    # common arguments
    args = {
        "executable_path": driver_path,
        "options": options,
    }

    if fox_profile is not None:
        args["firefox_profile"] = fox_profile

    # create driver
    driver = driver_info["driver"](**args)

    # for chrome we need to enable auto download
    # after start
    if not config.download.prompt and (
        config.type == WebdriverType.CHROME or config.type == WebdriverType.CHROMIUM
    ):
        chrome_enable_download_headless(driver, download_path)

    # configure driver implicit wait time
    driver.implicitly_wait(config.implicit_wait)

    # configure browser display size and position
    driver.set_window_size(width=config.window_width, height=config.window_height)
    driver.set_window_position(x=config.window_x_position, y=config.window_y_position)

    return driver


def slow_type(
    element: WebElement,
    text: str,
    delay: Union[float, ApproximateFloat] = ApproximateFloat(
        min=0.05,
        max=0.35,
    ),
):
    """Send a text to an element one character at a time with a delay.

    Args:
        element: The element to send the text to
        text: The text to send
        delay: The delay to use in between key strokes.
               Average typing speed is 180-200 characters per minute or
               3~ per second. The default was set with this in mind.
    """
    # convert to approximate float if we got a float
    if not isinstance(delay, ApproximateFloat):
        delay = ApproximateFloat.convert(delay)

    # type the text
    for character in text:
        element.send_keys(character)
        time.sleep(delay.value)


def type_linebreak(driver: webdriver.Remote, count=1):
    """Sends a linebreak to the currently focused input element (e.g., textarea).

    This is done using ++shift+enter++ so no submit is triggered.

    Args:
        driver: The webdriver
        count: The amount of line breaks to write
    """
    for i in range(0, count):
        ActionChains(driver).key_down(Keys.SHIFT).key_down(Keys.ENTER).key_up(
            Keys.SHIFT
        ).key_up(Keys.ENTER).perform()


def js_set_text(driver: webdriver.Remote, element: WebElement, text: str):
    """Set the text value of an input element directly with Javascript.

    This can be useful for avoiding onChange event listeners
    evaluating partial texts.

    Args:
        driver: The webdriver
        element: The input element to set the text for
        text: The text to set
    """
    driver.execute_script(
        f"arguments[0].value = '{text}'",
        element,
    )


def wait_for_window_change(
    driver: webdriver.Remote,
    handles_before: List[str],
    timeout: Union[float, int] = 10,
    poll_frequency: float = POLL_FREQUENCY,
):
    """Wait for a new window to open and returns its window handle.

    Args:
        driver: The webdriver
        handles_before: The handles list before the new window opens
        timeout: The maximum time to wait for
        poll_frequency: The frequency the condition should be checked
    """
    # wait for the window to appear
    WebDriverWait(
        driver=driver,
        timeout=timeout,
        poll_frequency=poll_frequency,
    ).until(lambda driver: len(handles_before) != len(driver.window_handles))


def get_new_window(
    driver: webdriver.Remote,
    handles_before: List[str],
) -> Optional[str]:
    """Get the new window based on the current and previous window list.

    Args:
        driver: The webdriver
        handles_before: The window list before the new window opened

    Returns:
        The window handle for the new window
    """
    # get new window and return
    handle_after = driver.window_handles
    if len(handle_after) > len(handles_before):
        return set(handle_after).difference(set(handles_before)).pop()
    return None


def wait_and_get_new_window(
    driver: webdriver.Remote,
    action: Callable[[], None],
    timeout: Union[float, int] = 10,
    poll_frequency: float = POLL_FREQUENCY,
) -> Optional[str]:
    """Executes the given function and waits for a new window to open and returns it handle.

    Args:
        driver: The webdriver
        action: The function to execute before waiting for the window
        timeout: The maximum time to wait
        poll_frequency: The frequency to check for the presence of the new window

    Returns:
        Optional[str]: [description]
    """
    handles_before = driver.window_handles

    action()

    wait_for_window_change(driver, handles_before, timeout, poll_frequency)
    return get_new_window(driver, handles_before)


@contextmanager
def wait_for_page_load(
    driver: webdriver.Remote,
    locator: Tuple[By, str] = (By.TAG_NAME, "html"),
    timeout=TIMEOUT,
):
    """Context manager for waiting on page reloads or requests caused by interaction.

    From https://www.cloudbees.com/blog/get-selenium-to-wait-for-page-load/

    Args:
        timeout: The maximum time to wait for the page to load
    """
    (by, value) = locator
    old_page = driver.find_element(by, value)
    yield
    WebDriverWait(driver, timeout).until(staleness_of(old_page))


def driver_wait(
    driver: webdriver.Remote,
    check_func: Callable[[webdriver.Remote], Optional[Any]],
    timeout: Union[float, int] = TIMEOUT,
    poll_frequency: float = POLL_FREQUENCY,
    ignored_exceptions: Tuple[Exception, ...] = None,
):
    """Wrapper function for WebDriverWait until with a custom timeout value

    Args:
        driver: The webdriver instance
        check_func: The poll check function
        timeout: The maximum time to wait.
        poll_frequency: The poll frequency.
        ignored_exceptions: The exceptions to ignore and not count as errors.
    """
    WebDriverWait(driver, timeout, poll_frequency, ignored_exceptions).until(check_func)


def scroll_to(
    driver: webdriver.Remote,
    elem: WebElement,
    wait: bool = True,
    options_behavior: Optional[str] = None,
    options_block: Optional[str] = "center",
    options_inline: Optional[str] = None,
):
    # only scroll if the element is not already in the view port
    if not element_in_viewport(driver, elem):
        options = {}
        if options_behavior:
            options["behavior"] = options_behavior
        if options_block:
            options["block"] = options_block
        if options_inline:
            options["inline"] = options_inline

        args = ""
        if len(options) > 0:
            args = ", ".join([f'{key}: "{val}"' for key, val in options.items()])
            args = "{" + args + "}"

        with WaitForScrollFinish(driver):
            driver.execute_script(f"arguments[0].scrollIntoView({args});", elem)
        driver_wait(driver, check_element_in_viewport(elem))


def element_in_viewport(driver: webdriver.Remote, elem: WebElement) -> bool:
    """Checks wether an element is not only visible but is also in the current viewport.

    See https://stackoverflow.com/a/46816183

    Args:
        driver: The webdriver
        elem: The element to check

    Returns:
        `True` if the element is in the viewport `False` otherwise.
    """
    elem_left_bound = elem.location.get("x")
    elem_top_bound = elem.location.get("y")
    elem_width = elem.size.get("width")
    elem_height = elem.size.get("height")
    elem_right_bound = elem_left_bound + elem_width
    elem_lower_bound = elem_top_bound + elem_height

    win_upper_bound = driver.execute_script("return window.pageYOffset")
    win_left_bound = driver.execute_script("return window.pageXOffset")
    win_width = driver.execute_script(
        "return window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;"
    )
    win_height = driver.execute_script(
        "return window.innerHeight || document.documentElement.clientHeight|| document.body.clientHeight;"
    )
    win_right_bound = win_left_bound + win_width
    win_lower_bound = win_upper_bound + win_height

    return all(
        (
            win_left_bound <= elem_left_bound,
            win_right_bound >= elem_right_bound,
            win_upper_bound <= elem_top_bound,
            win_lower_bound >= elem_lower_bound,
        )
    )


def check_element_in_viewport(elem: WebElement) -> Callable[[webdriver.Remote], bool]:
    return lambda driver: element_in_viewport(driver, elem)


class WaitForScrollFinish:
    """Utility class that can be used to wait for a vertical scroll to finish.

    Can also be used as context manager to encapsulate a code block with the
    wait directive. Meaning the y_pos is saved at the start of the block
    and the check is started once the indented block has finished.

    Examples:
      ```python
      with WaitForScrollFinish(driver):
          # y post is magically saved here
          driver.find_element_by_id('some-input').send_keys('input')
          driver.find_element_by_id('some-button').click()
          # scroll checks and waits magically begin here
     ```
    """

    def __init__(
        self,
        driver: webdriver.Remote,
        y_pos: int = 0,
        timeout: int = TIMEOUT,
    ):
        """
        Args:
            driver: The webdriver instance
            y_pos: The initial y position to use. Used when you want to manually call the wait functions.
            timeout: The maximum amount of time to wait for the scroll to finish.
        """
        self.driver: webdriver.Remote = driver
        self.timeout: int = timeout
        self.y_pos_org: int = y_pos

    def __enter__(self):
        self.y_pos_org = self.driver.execute_script("return window.pageYOffset")
        return self

    def check_stable(self, driver: webdriver.Remote) -> bool:
        current = driver.execute_script("return window.pageYOffset")
        # compare current to old y post
        if current == self.y_pos_org:
            return True
        # if not the same updated saved y pos and return false
        self.y_pos_org = current
        return False

    def wait_changed(self):
        # wait for the scroll location to change
        WebDriverWait(self.driver, self.timeout).until(
            lambda driver: driver.execute_script("return window.pageYOffset")
            != self.y_pos_org
        )

    def wait_stable(self):
        # wait for the scroll bar to stop
        WebDriverWait(self.driver, self.timeout).until(self.check_stable)

    def wait(self):
        self.wait_changed()
        self.wait_stable()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.wait()


class SeleniumStatemachineConfig(BasicStatemachineConfig):
    """Web browser state machine configuration model

    Example:
        ```yaml
        max_errors: 0
        start_time: 2021-01-23T9:00
        end_time: 2021-01-29T00:01
        schedule:
        work_days:
            monday:
                start_time: 09:00
                end_time: 17:30
            friday:
                start_time: 11:21
                end_time: 19:43
        selenium:
            driver_manager:
                cache_valid_range: 5 # days
            type: firefox
            window_width: 800
            window_height: 600
            accept_insecure_ssl: yes
        ```
    """

    selenium: SeleniumConfig = Field(
        SeleniumConfig(),
        description="Selenium configuration for the web browser user",
    )


class SeleniumContext(FakerContext, Protocol):
    """Context model for selenium state machines"""

    driver: webdriver.Remote
    """The selenium web driver"""

    main_window: str
    """The main window of the webdriver"""

    fake: Faker
    """Faker instance to use for generating various random content"""


class SeleniumContextModel(FakerContextModel):
    """Context model for selenium state machines"""

    driver: webdriver.Remote
    """The selenium web driver"""

    main_window: str = Field(
        ...,
        description="The main window of the webdriver",
    )


C = TypeVar("C", bound=SeleniumContext)


class SeleniumStatemachine(FakerStatemachine[C]):
    """Generic selenium state machine class"""

    def __init__(
        self,
        initial_state: str,
        states: List[State],
        selenium_config: SeleniumConfig,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        work_schedule: Optional[WorkSchedule] = None,
        max_errors: int = 0,
    ):
        super().__init__(
            initial_state,
            states,
            start_time=start_time,
            end_time=end_time,
            work_schedule=work_schedule,
            max_errors=max_errors,
        )
        self._selenium_config: SeleniumConfig = selenium_config
        self._webdriver_path: Optional[str] = None

    def get_driver(self) -> webdriver.Remote:
        # we assume we only install once at the start of the sm
        if self._webdriver_path is None:
            self._webdriver_path = install_webdriver(self._selenium_config)

        return get_webdriver(
            self._selenium_config,
            self._webdriver_path,
        )

    def setup_context(self):
        raise NotImplementedError()

    def destroy_context(self):
        if self.context is not None:
            self.context.driver.quit()


class Statemachine(SeleniumStatemachine[SeleniumContext]):
    """Basic selenium state machine class with a selenium context"""

    def setup_context(self):
        driver = self.get_driver()
        self.context = SeleniumContextModel(
            driver=driver,
            main_window=driver.current_window_handle,
            fake=self.fake,
        )
