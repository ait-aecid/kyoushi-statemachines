import pytest

from pydantic import (
    BaseModel,
    ValidationError,
)
from pytest_mock import MockFixture
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import (
    EdgeChromiumDriverManager,
    IEDriverManager,
)
from webdriver_manager.opera import OperaDriverManager

from cr_kyoushi.statemachines.core.selenium import (
    SeleniumConfig,
    WebdriverType,
    get_webdriver_manager,
    install_webdriver,
)


class WebdriverTestModel(BaseModel):
    driver_type: WebdriverType


def test_parse_from_int_values():
    chrome = WebdriverTestModel(driver_type=WebdriverType.CHROME.value)
    chromium = WebdriverTestModel(driver_type=WebdriverType.CHROMIUM.value)
    firefox = WebdriverTestModel(driver_type=WebdriverType.FIREFOX.value)
    ie = WebdriverTestModel(driver_type=WebdriverType.IE.value)
    edge = WebdriverTestModel(driver_type=WebdriverType.EDGE.value)
    opera = WebdriverTestModel(driver_type=WebdriverType.OPERA.value)

    assert chrome.driver_type == WebdriverType.CHROME
    assert chromium.driver_type == WebdriverType.CHROMIUM
    assert firefox.driver_type == WebdriverType.FIREFOX
    assert ie.driver_type == WebdriverType.IE
    assert edge.driver_type == WebdriverType.EDGE
    assert opera.driver_type == WebdriverType.OPERA


def test_parse_from_invalid_int_value():
    with pytest.raises(ValidationError):
        WebdriverTestModel(driver_type=10)


def test_parse_from_case_insensitive_string_value():
    chrome = WebdriverTestModel(driver_type="chrome")
    chromium = WebdriverTestModel(driver_type="cHRomIUm")
    firefox = WebdriverTestModel(driver_type="FIREFOX")
    ie = WebdriverTestModel(driver_type="iE")
    edge = WebdriverTestModel(driver_type="eDGe")
    opera = WebdriverTestModel(driver_type="OperA")

    assert chrome.driver_type == WebdriverType.CHROME
    assert chromium.driver_type == WebdriverType.CHROMIUM
    assert firefox.driver_type == WebdriverType.FIREFOX
    assert ie.driver_type == WebdriverType.IE
    assert edge.driver_type == WebdriverType.EDGE
    assert opera.driver_type == WebdriverType.OPERA


def test_parse_from_invalid_string_value():
    with pytest.raises(ValidationError):
        WebdriverTestModel(driver_type="not_a_driver")


def test_parse_from_enum():
    chrome = WebdriverTestModel(driver_type=WebdriverType.CHROME)
    assert chrome.driver_type == WebdriverType.CHROME


@pytest.mark.parametrize(
    "config",
    [
        pytest.param(
            {
                "type": "IE",
                "headless": True,
                "arguments": ["some-arg"],
            },
            id="ie-headless",
        ),
        pytest.param(
            {
                "type": "EDGE",
                "headless": True,
                "arguments": [],
            },
            id="edge-headless",
        ),
        pytest.param(
            {
                "type": "EDGE",
                "headless": False,
                "arguments": ["some-arg"],
            },
            id="edge-arguments",
        ),
    ],
)
def test_selenium_config_validation_raises_on_invalid(config):
    with pytest.raises(ValidationError):
        SeleniumConfig(**config)


@pytest.mark.parametrize(
    "config, expected",
    [
        pytest.param(
            {
                "type": "firefox",
                "headless": True,
                "arguments": ["some-arg"],
            },
            {
                "type": WebdriverType.FIREFOX,
                "headless": True,
                "arguments": ["some-arg"],
            },
            id="firefox-headless",
        ),
        pytest.param(
            {
                "type": "IE",
                "headless": False,
                "arguments": ["some-arg"],
            },
            {
                "type": WebdriverType.IE,
                "headless": False,
                "arguments": ["some-arg"],
            },
            id="ie",
        ),
    ],
)
def test_selenium_config_validation(config, expected):
    expected_config = SeleniumConfig()
    expected_config.type = expected["type"]
    expected_config.headless = expected["headless"]
    expected_config.arguments = expected["arguments"]

    assert SeleniumConfig(**config) == expected_config


@pytest.mark.parametrize(
    "config, expected_manager",
    [
        pytest.param(SeleniumConfig(type="chrome"), ChromeDriverManager, id="chrome"),
        pytest.param(
            SeleniumConfig(type="chromium"), ChromeDriverManager, id="chromium"
        ),
        pytest.param(SeleniumConfig(type="firefox"), GeckoDriverManager, id="firefox"),
        pytest.param(SeleniumConfig(type="ie"), IEDriverManager, id="ie"),
        pytest.param(SeleniumConfig(type="edge"), EdgeChromiumDriverManager, id="edge"),
        pytest.param(SeleniumConfig(type="opera"), OperaDriverManager, id="opera"),
    ],
)
def test_get_webdriver_manager_returns_correct_manager(
    mocker: MockFixture,
    config,
    expected_manager,
):
    # need to mock the chrome version call in case chrome or chromium is not installed
    chrome_version_mock = mocker.Mock()
    chrome_version_mock.return_value = "87.0.4280.141"
    mocker.patch(
        "webdriver_manager.driver.chrome_version",
    )

    assert isinstance(get_webdriver_manager(config), expected_manager)


def test_install_webdriver_calls_manager_install(mocker: MockFixture):
    expected_driver_path = "installed"

    # mock the manager
    manager_mock = mocker.MagicMock(GeckoDriverManager)
    manager_mock.install.return_value = expected_driver_path

    get_manager_mock = mocker.MagicMock()
    get_manager_mock.return_value = manager_mock

    mocker.patch(
        "cr_kyoushi.statemachines.core.selenium.get_webdriver_manager",
        get_manager_mock,
    )

    config = SeleniumConfig()

    # assert expected webdriver path is returned
    assert install_webdriver(config) == expected_driver_path

    # assert correct manager is installed
    get_manager_mock.assert_called_once_with(config)
    manager_mock.install.assert_called_once_with()
