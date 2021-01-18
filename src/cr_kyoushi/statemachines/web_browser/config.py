from datetime import date
from datetime import datetime
from typing import TYPE_CHECKING
from typing import List
from typing import Optional

from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import Field
from pydantic import confloat
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.simulation.model import WorkSchedule
from cr_kyoushi.simulation.util import now

from ..core.selenium import SeleniumConfig


__all__ = ["UserConfig", "StatemachineConfig", "Context"]


if TYPE_CHECKING:
    Probability = float
else:
    Probability = confloat(ge=0, le=1)


class UserConfig(BaseModel):
    websites: List[AnyUrl] = Field(
        [],
        description="The web site URLs the user can visit",
    )

    max_websites_day: int = Field(
        5,
        description="The maximum websites to visit per day",
    )

    max_depth: int = Field(
        2,
        description="The maximum link depth the user will browse to on a website",
    )

    wait_time: ApproximateFloat = Field(
        ApproximateFloat(min=0.5, max=3.0),
        description="The approximate time the user waits before clicking a link on a website",
    )

    visit_website: Probability = Field(
        0.7,
        description="The probability that the user will visit a website, otherwise the user will idle",
    )

    visit_link: Probability = Field(
        0.7,
        description="The probability that the user will click a link, otherwise the user will leave the website",
    )

    leave_open: Probability = Field(
        0.5,
        description="The probability that the user will just leave the website open in the background",
    )


class StatemachineConfig(BaseModel):
    max_errors: int = Field(
        0,
        description="The maximum amount of times to try to recover from an error",
    )

    start_time: Optional[datetime] = Field(
        None,
        description="The state machines start time",
    )

    end_time: Optional[datetime] = Field(
        None,
        description="The state machines end time",
    )

    schedule: Optional[WorkSchedule] = Field(
        None,
        description="The work schedule for the web browser user",
    )

    selenium: SeleniumConfig = Field(
        SeleniumConfig(),
        description="Selenium configuration for the web browser user",
    )

    user: UserConfig = Field(
        UserConfig(),
        description="The web browser user configuration",
    )

    idle_time: ApproximateFloat = Field(
        ApproximateFloat(min=60, max=60 * 60 * 2),
        description="The time to wait in between website visits",
    )


class Context(BaseModel):
    driver: webdriver.Remote
    """The selenium web driver"""

    current_website: Optional[AnyUrl] = Field(
        None,
        description="The website currently being visited",
    )

    current_day: date = Field(
        now().date(),
        description="The current day (used to check visit count)",
    )

    available_links: List[WebElement] = Field(
        [],
        description="List of links available on the current website",
    )

    website_count: int = Field(
        0,
        description="The current days visited website count",
    )

    website_depth: int = Field(
        0,
        description="The current websites link depth",
    )

    class Config:
        arbitrary_types_allowed = True
