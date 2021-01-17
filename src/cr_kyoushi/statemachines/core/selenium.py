"""
This module contains configuration and utility functions for using Selenium webdrivers
as part of simulations.
"""

from enum import Enum
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import Field
from pydantic import PositiveInt
from pydantic import validator
from pydantic.errors import EnumMemberError
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.opera.options import Options as OperaOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.manager import DriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.microsoft import IEDriverManager
from webdriver_manager.opera import OperaDriverManager
from webdriver_manager.utils import ChromeType

from cr_kyoushi.simulation.model import LogLevel

from .util import filter_none_keys


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


def get_webdriver(
    config: SeleniumConfig,
) -> Union[
    webdriver.Chrome,
    webdriver.Firefox,
    webdriver.Ie,
    webdriver.Edge,
    webdriver.Opera,
]:
    """Gets and configures a Selenium webdriver instance based on the given configuration.

    Args:
        config: The selenium configuration

    Returns:
        The initialized and configured Selenium webdriver instance
    """
    driver_info = _MANAGER_MAP[config.type]
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

    # create driver
    driver = driver_info["driver"](
        executable_path=driver_path,
        options=options,
    )

    # configure browser display size and position
    driver.set_window_size(width=config.window_width, height=config.window_height)
    driver.set_window_position(x=config.window_x_position, y=config.window_y_position)

    return driver
