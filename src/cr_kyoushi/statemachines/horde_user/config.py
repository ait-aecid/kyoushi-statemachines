from datetime import datetime
from typing import Optional

from faker import Faker
from pydantic import BaseModel
from pydantic import Field
from selenium import webdriver

from cr_kyoushi.simulation.model import WorkSchedule

from ..core.selenium import SeleniumConfig


__all__ = [
    "StatemachineConfig",
    "Context",
]


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


class Context(BaseModel):
    driver: webdriver.Remote
    """The selenium web driver"""

    fake: Faker
    """Faker instance to use for generating various random content"""

    class Config:
        arbitrary_types_allowed = True
