import sys

from datetime import date
from typing import (
    List,
    Optional,
)

from pydantic import (
    AnyUrl,
    BaseModel,
    Field,
)
from selenium.webdriver.remote.webelement import WebElement

from cr_kyoushi.simulation.util import now

from ..core.config import ProbabilisticStateConfig
from ..core.selenium import (
    SeleniumContext,
    SeleniumContextModel,
    SeleniumStatemachineConfig,
)


if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol

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

    max_daily: int = Field(
        5,
        description="The maximum websites to visit per day",
    )

    max_depth: int = Field(
        2,
        description="The maximum link depth the user will browse to on a website",
    )


class ActivitySelectionStateConfig(ProbabilisticStateConfig):
    """Transition probabilities configuration for the `selecting_activity` state"""

    visit_website: float = Field(
        0.7,
        description="The probability that the user will visit a website next",
    )

    idle: float = Field(
        0.3,
        description="The probability that the user will idle next",
    )


class WebsiteStateConfig(ProbabilisticStateConfig):
    """Transition probabilities configuration for the `on_website` state"""

    visit_link: float = Field(
        0.7,
        description="The probability that the user will click a link",
    )

    leave_website: float = Field(
        0.3,
        description="The probability that the user will leave the website",
    )


class LeaveWebsiteStateConfig(ProbabilisticStateConfig):
    """Transition probabilities configuration for the `leaving_website` state"""

    background: float = Field(
        0.5,
        description="The probability that the user will just leave the website open in the background",
    )

    close: float = Field(
        0.5,
        description="The probability that the user will close the website",
    )


class WebBrowserStates(BaseModel):
    """State transition configuration for the web browser states"""

    on_website: WebsiteStateConfig = Field(
        WebsiteStateConfig(),
        description="The transition probabilities configuration for the `on_website` state",
    )

    leaving_website: LeaveWebsiteStateConfig = Field(
        LeaveWebsiteStateConfig(),
        description="The transition probabilities configuration for the `leaving_website` state",
    )


class StatesConfig(WebBrowserStates):
    """State transition configuration for the web browser state machine"""

    selecting_activity: ActivitySelectionStateConfig = Field(
        ActivitySelectionStateConfig(),
        description="The transition probabilities configuration for the `selecting_activity` state",
    )


class StatemachineConfig(SeleniumStatemachineConfig):
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
        user:
            max_daily: 5
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

    user: UserConfig = Field(
        UserConfig(),
        description="The web browser user configuration",
    )

    states: StatesConfig = Field(
        StatesConfig(),
        description="The state transitions probability configuration",
    )


class WebBrowserContextModel(BaseModel):
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


class Context(SeleniumContext, Protocol):

    web_browser: WebBrowserContextModel
    """The web browser user context"""


class ContextModel(SeleniumContextModel):
    web_browser: WebBrowserContextModel = Field(
        WebBrowserContextModel(),
        description="The web browser user context",
    )
