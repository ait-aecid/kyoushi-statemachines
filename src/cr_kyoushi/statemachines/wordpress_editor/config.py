from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    validator,
)

from ..core.config import (
    ActivityExtraConfig,
    ProbabilisticStateConfig,
)
from ..core.selenium import SeleniumStatemachineConfig
from ..core.util import positive_smaller_one


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


class LoginPageConfig(BaseModel):
    """The login page states configuration"""

    fail_chance: float = Field(
        0.05,
        description="The chance the user will use an incorrect password",
    )

    fail_decrease: float = Field(
        0.9,
        description=(
            "Multiplicative modifier used for decreasing the "
            "chance of failed logins with each consecutive fail"
        ),
    )

    # validators
    _validate_chance = validator("fail_chance", allow_reuse=True)(positive_smaller_one)

    _validate_decrease = validator("fail_decrease", allow_reuse=True)(
        positive_smaller_one
    )


class LogoutChoiceConfig(BaseModel):
    """The logout choice states configuration"""

    logout_chance: float = Field(
        0.05,
        description="The chance the user will logout when stopping the horde activity",
    )

    # validators
    _validate_chance = validator("logout_chance", allow_reuse=True)(
        positive_smaller_one
    )


class SelectingMenuConfig(ProbabilisticStateConfig):
    """The selecting menu states configuration"""

    nav_dashboard: float = Field(
        0.15,
        description="The base propability that nav_dashboard will be selected.",
    )

    nav_comments: float = Field(
        0.25,
        description="The base propability that nav_comments will be selected.",
    )

    nav_media: float = Field(
        0.15,
        description="The base propability that nav_media will be selected.",
    )

    nav_posts: float = Field(
        0.3,
        description="The base propability that nav_posts will be selected.",
    )

    return_: float = Field(
        0.15,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(),
        description="Extra configuration for the state",
    )


class CommentsPageExtraConfig(ActivityExtraConfig):
    reply_only_guests: bool = Field(
        True,
        description="If the user should only reply to guest comments",
    )


class CommentsPageConfig(ProbabilisticStateConfig):
    """The comments page states configuration"""

    new_reply: float = Field(
        0.45,
        description="The base propability that new_reply will be selected.",
    )

    return_: float = Field(
        0.55,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: CommentsPageExtraConfig = Field(
        CommentsPageExtraConfig(),
        description="Extra configuration for the state",
    )


class PostsPageExtraConfig(ActivityExtraConfig):
    max_posts_daily: int = Field(
        1,
        description="The maximum number of posts a user will post in a day",
    )


class PostsPageConfig(ProbabilisticStateConfig):
    """The posts page states configuration"""

    new_post: float = Field(
        0.5,
        description="The base propability that new_post will be selected.",
    )

    return_: float = Field(
        0.5,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: PostsPageExtraConfig = Field(
        PostsPageExtraConfig(),
        description="Extra configuration for the state",
    )


class WordpressEditorStates(BaseModel):
    """Configuration class for all wordpress editor activity states."""

    login_page: LoginPageConfig = Field(
        LoginPageConfig(),
        description="The login page states config",
    )

    logout_choice: LogoutChoiceConfig = Field(
        LogoutChoiceConfig(),
        description="The logout choice states config",
    )

    selecting_menu: SelectingMenuConfig = Field(
        SelectingMenuConfig(),
        description="The selecting menu states config",
    )

    comments_page: CommentsPageConfig = Field(
        CommentsPageConfig(),
        description="The comments page states config",
    )

    posts_page: PostsPageConfig = Field(
        PostsPageConfig(),
        description="The posts page states config",
    )


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

    wp_editor: WordpressEditorConfig = Field(
        WordpressEditorConfig(),
        description="The wordpress editor user config",
    )

    states: WordpressEditorUserStates = Field(
        WordpressEditorUserStates(),
        description="The states configuration for the state machine",
    )
