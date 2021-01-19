from pytest_mock import MockFixture
from selenium.webdriver import Remote
from selenium.webdriver.remote.webelement import WebElement

from cr_kyoushi.simulation.logging import get_logger
from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.simulation.util import now
from cr_kyoushi.statemachines.web_browser.config import Context
from cr_kyoushi.statemachines.web_browser.transitions import Idle
from cr_kyoushi.statemachines.web_browser.transitions import _get_available_links


def test_idle_given_no_end_time(mocker: MockFixture):
    idle_amount = ApproximateFloat(min=0.5, max=1.5)
    context = mocker.MagicMock(Context)
    idle = Idle(idle_amount=idle_amount)

    # mock sleep functions
    sleep_mock = mocker.patch(
        "cr_kyoushi.statemachines.web_browser.transitions.sleep", return_value=None
    )
    sleep_until_mock = mocker.patch(
        "cr_kyoushi.statemachines.web_browser.transitions.sleep_until",
        return_value=None,
    )

    idle(
        log=get_logger(),
        current_state="STATE",
        context=context,
        target="TARGET",
    )

    assert sleep_mock.mock_calls == [mocker.call(idle_amount)]
    assert sleep_until_mock.mock_calls == []


def test_idle_given_end_time(mocker: MockFixture):
    idle_amount = ApproximateFloat(min=1.5, max=1.5)
    context = mocker.MagicMock(Context)
    current_time = now()
    idle = Idle(idle_amount=idle_amount, end_time=current_time)

    # mock sleep functions
    sleep_mock = mocker.patch(
        "cr_kyoushi.statemachines.web_browser.transitions.sleep", return_value=None
    )
    sleep_until_mock = mocker.patch(
        "cr_kyoushi.statemachines.web_browser.transitions.sleep_until",
        return_value=None,
    )
    # mock now to ensure that current_time is always the same
    mocker.patch(
        "cr_kyoushi.statemachines.web_browser.transitions.now",
        return_value=current_time,
    )

    idle(
        log=get_logger(),
        current_state="STATE",
        context=context,
        target="TARGET",
    )

    assert sleep_mock.mock_calls == []
    assert sleep_until_mock.mock_calls == [mocker.call(current_time)]


def test_available_links(mocker: MockFixture):

    http_link = mocker.MagicMock(WebElement)
    http_link.get_attribute.return_value = "http://some.lnk"
    https_link = mocker.MagicMock(WebElement)
    https_link.get_attribute.return_value = "https://some.lnk"
    empty_link = mocker.MagicMock(WebElement)
    empty_link.get_attribute.return_value = ""
    invalid_scheme_link = mocker.MagicMock(WebElement)
    invalid_scheme_link.get_attribute.return_value = "file://some.txt"
    relative_link = mocker.MagicMock(WebElement)
    relative_link.get_attribute.return_value = "/index.html"

    web_elements = [
        http_link,
        https_link,
        empty_link,
        invalid_scheme_link,
        relative_link,
    ]

    expected_links = [http_link, https_link]

    driver_mock = mocker.MagicMock(Remote)
    driver_mock.find_elements.return_value = web_elements

    context = Context(driver=driver_mock)

    _get_available_links(log=get_logger(), context=context)

    assert expected_links == context.available_links
