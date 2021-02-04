from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
)

from cr_kyoushi.simulation.model import WorkSchedule

from ..core.config import (
    IdleConfig,
    ProbabilisticStateConfig,
)
from ..core.selenium import SeleniumConfig


class ActivitySelectionConfig(ProbabilisticStateConfig):
    """Wordpess wordpress user state machines selecting activity states configuration."""

    wp_editor: float = Field(
        0.6,
        description="The base propability that wp_editor will be selected.",
    )

    idle: float = Field(
        0.4,
        description="The base propability that idle will be selected.",
    )


class WordpressEditorStates(BaseModel):
    """Configuration class for all wordpress editor activity states."""


class WordpressEditorUserStates(WordpressEditorStates):
    """Configuration class for the wordpress wordpress editor state machine states"""

    selecting_activity: ActivitySelectionConfig = Field(
        ActivitySelectionConfig(),
        description="The selecting activity states config",
    )


class WordpressEditorConfig(BaseModel):
    """Configuration class for the wordpress editor user"""

    url: HttpUrl = Field(
        "http://localhost",
        description="The wordpress servers wp-admin URL",
    )

    author: str = Field(
        "Max Mustermann",
        description="The editors name",
    )

    username: str = Field(
        "mmustermann",
        description="The editors username",
    )

    password: str = Field(
        "passwd123",
        description="The editors password",
    )

    max_daily: int = Field(
        10,
        description="The maximum amount of times the wpdiscuz activity will be entered per day",
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

    idle: IdleConfig = Field(
        IdleConfig(),
        description="The idle configuration for the state machine",
    )

    schedule: Optional[WorkSchedule] = Field(
        None,
        description="The work schedule for the web browser user",
    )

    selenium: SeleniumConfig = Field(
        SeleniumConfig(),
        description="Selenium configuration for the web browser user",
    )

    wp_editor: WordpressEditorConfig = Field(
        WordpressEditorConfig(),
        description="The wordpress editor user config",
    )
