import pytest

from pydantic import BaseModel
from pydantic import ValidationError

from cr_kyoushi.statemachines.core.selenium import WebdriverType


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
