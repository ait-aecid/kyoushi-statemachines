from faker import Faker
from pytest_mock import MockFixture
from selenium.webdriver import Remote
from selenium.webdriver.remote.webelement import WebElement

from cr_kyoushi.simulation.logging import get_logger
from cr_kyoushi.statemachines.web_browser.config import ContextModel
from cr_kyoushi.statemachines.web_browser.transitions import _get_available_links


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

    context = ContextModel(driver=driver_mock, fake=Faker(), main_window="test")

    _get_available_links(log=get_logger(), context=context)

    assert expected_links == context.web_browser.available_links
