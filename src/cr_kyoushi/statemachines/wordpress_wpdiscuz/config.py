from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
    validator,
)

from ..core.config import (
    ActivityExtraConfig,
    ProbabilisticStateConfig,
)
from ..core.selenium import SeleniumStatemachineConfig


class ActivitySelectionConfig(ProbabilisticStateConfig):
    """Wordpess wpDiscuz user state machines selecting activity states configuration."""

    wpdiscuz: float = Field(
        0.6,
        description="The base propability that wpdiscuz will be selected.",
    )

    idle: float = Field(
        0.4,
        description="The base propability that idle will be selected.",
    )


class PostsPageExtraConfig(ActivityExtraConfig):
    max_page: int = Field(
        3,
        description="The maximum posts page to navigate to",
    )


class PostsPageConfig(ProbabilisticStateConfig):
    """The posts page states configuration"""

    nav_older: float = Field(
        0.15,
        description="The base propability that nav_older will be selected.",
    )

    nav_newer: float = Field(
        0.25,
        description="The base propability that nav_newer will be selected.",
    )

    nav_post: float = Field(
        0.35,
        description="The base propability that nav_post will be selected.",
    )

    return_: float = Field(
        0.25,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: PostsPageExtraConfig = Field(
        PostsPageExtraConfig(ret_increase=1.5),
        description="Extra configuration for the state",
    )


class CloseChoiceConfig(ProbabilisticStateConfig):
    """The close choices states configuration"""

    leave_open: float = Field(
        0.6,
        description="The base propability that leave_open will be selected.",
    )

    close: float = Field(
        0.4,
        description="The base propability that close will be selected.",
    )


class PostPageExtraConfig(ActivityExtraConfig):
    max_level: int = Field(
        3,
        description="The maximum comment depth level to reply to.",
    )

    max_rating: int = Field(
        5,
        description="The maximum star rating the user will give to a post.",
    )

    min_rating: int = Field(
        1,
        description="The minimum star rating the user will give to a post.",
    )

    @validator("min_rating", "max_rating")
    def check_valid_rating(cls, v: int):
        assert v > 0 and v <= 5, "Rating must be between 1 and 5"
        return v

    @validator("min_rating")
    def check_min_le_max(cls, v, values, **kwargs):
        if "max_rating" in values:
            assert v <= values["max_rating"], "Min rating must be <= max rating"
        return v


class PostPageConfig(ProbabilisticStateConfig):
    """The post page states configuration"""

    rate_post: float = Field(
        0.1,
        description="The base propability that rate_post will be selected.",
    )

    down_vote: float = Field(
        0.1,
        description="The base propability that down_vote will be selected.",
    )

    up_vote: float = Field(
        0.15,
        description="The base propability that up_vote will be selected.",
    )

    comment: float = Field(
        0.25,
        description="The base propability that comment will be selected.",
    )

    reply: float = Field(
        0.2,
        description="The base propability that reply will be selected.",
    )

    return_: float = Field(
        0.2,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: PostPageExtraConfig = Field(
        PostPageExtraConfig(ret_increase=1.5),
        description="Extra configuration for the state",
    )


class WpDiscuzStates(BaseModel):
    """Configuration class for all wpdiscuz activity states."""

    posts_page: PostsPageConfig = Field(
        PostsPageConfig(),
        description="The posts page states config",
    )

    close_choice: CloseChoiceConfig = Field(
        CloseChoiceConfig(),
        description="The close choice states config",
    )

    post_page: PostPageConfig = Field(
        PostPageConfig(),
        description="The post page states config",
    )


class WpDiscuzUserStates(WpDiscuzStates):
    """Configuration class for the wordpress wpdiscuz state machine states"""

    selecting_activity: ActivitySelectionConfig = Field(
        ActivitySelectionConfig(),
        description="The selecting activity states config",
    )


class WpDiscuzConfig(BaseModel):
    """Configuration class for the wpdiscuz user"""

    url: HttpUrl = Field(
        "http://localhost",
        description="The wordpress servers base URL",
    )

    page_title: str = Field(
        "Wordpress",
        description="The wordpress pages title",
    )

    author: str = Field(
        "Max Mustermann",
        description="The comment authors name",
    )

    email: EmailStr = Field(
        "max.mustermann@localhost.local",
        description="The comment authors email",
    )

    max_daily: int = Field(
        10,
        description="The maximum amount of times the wpdiscuz activity will be entered per day",
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
        ```
    """

    states: WpDiscuzUserStates = Field(
        WpDiscuzUserStates(),
        description="The states configuration for the state machine",
    )

    wpdiscuz: WpDiscuzConfig = Field(
        WpDiscuzConfig(),
        description="The wpdiscuz user config",
    )
