from datetime import (
    date,
    datetime,
)
from typing import (
    List,
    Optional,
)

from pydantic import (
    AnyUrl,
    BaseModel,
    Field,
)
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from cr_kyoushi.simulation.model import (
    ApproximateFloat,
    WorkSchedule,
)
from cr_kyoushi.simulation.util import now

from ..core.config import (
    ProbabilisticStateConfig,
    ProbVal,
)
from ..core.selenium import SeleniumConfig


__all__ = [
    "UserConfig",
    "StatemachineConfig",
    "Context",
    "ActivitySelectionStateConfig",
    "WebsiteStateConfig",
    "LeaveWebsiteStateConfig",
    "StatesConfig",
]


class UserConfig(BaseModel):
    """Web browser state machine user behavior configuration"""

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

    idle_time: ApproximateFloat = Field(
        ApproximateFloat(min=60, max=60 * 60 * 2),
        description="The time to wait in between website visits",
    )


class ActivitySelectionStateConfig(ProbabilisticStateConfig):
    """Transition probabilities configuration for the `selecting_activity` state"""

    visit_website: ProbVal = Field(
        0.7,
        description="The probability that the user will visit a website next",
    )

    idle: ProbVal = Field(
        0.3,
        description="The probability that the user will idle next",
    )


class WebsiteStateConfig(ProbabilisticStateConfig):
    """Transition probabilities configuration for the `on_website` state"""

    visit_link: ProbVal = Field(
        0.7,
        description="The probability that the user will click a link",
    )

    leave_website: ProbVal = Field(
        0.3,
        description="The probability that the user will leave the website",
    )


class LeaveWebsiteStateConfig(ProbabilisticStateConfig):
    """Transition probabilities configuration for the `leaving_website` state"""

    background: ProbVal = Field(
        0.5,
        description="The probability that the user will just leave the website open in the background",
    )

    close: ProbVal = Field(
        0.5,
        description="The probability that the user will close the website",
    )


class StatesConfig(BaseModel):
    """State transition configuration for the web browser state machine"""

    selecting_activity: ActivitySelectionStateConfig = Field(
        ActivitySelectionStateConfig(),
        description="The transition probabilities configuration for the `selecting_activity` state",
    )

    on_website: WebsiteStateConfig = Field(
        WebsiteStateConfig(),
        description="The transition probabilities configuration for the `on_website` state",
    )

    leaving_website: LeaveWebsiteStateConfig = Field(
        LeaveWebsiteStateConfig(),
        description="The transition probabilities configuration for the `leaving_website` state",
    )


class StatemachineConfig(BaseModel):
    """Web browser state machine configuration model

    Example:
        ```yaml
        max_error: 0
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
        user:
            max_websites_day: 5
            max_depth: 2
            wait_time:
                min: 3.5 # seconds
                max: 10  # seconds
            idle_time:
                min: 300 # 60*5 = 5m
                max: 10800 # 60*60*3 = 3h
            websites:
                - http://ait.ac.at
                - https://orf.at
                - http://google.at
        states:
            selecting_activity:
                visit_website: 0.7
                idle: 0.3
            on_website:
                visit_link: 0.7
                leave_website: 0.3
            leaving_website:
                background: 0.5
                close: 0.5
        ```
    """

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

    states: StatesConfig = Field(
        StatesConfig(),
        description="The state transitions probability configuration",
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
