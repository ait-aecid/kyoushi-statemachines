import re

from typing import (
    Dict,
    List,
    Optional,
    Pattern,
)

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
from ..core.selenium import (
    SeleniumConfig,
    SeleniumStatemachineConfig,
)
from ..core.util import positive_smaller_one


class ActivitySelectionConfig(ProbabilisticStateConfig):
    """Owncloud user state machines selecting activity states configuration."""

    owncloud: float = Field(
        0.6,
        description="The base propability that owncloud will be selected.",
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

    nav_all: float = Field(
        0.25,
        description="The base propability that nav_all will be selected.",
    )

    nav_favorites: float = Field(
        0.2,
        description="The base propability that nav_favorites will be selected.",
    )

    nav_sharing_in: float = Field(
        0.25,
        description="The base propability that nav_sharing_in will be selected.",
    )

    nav_sharing_out: float = Field(
        0.2,
        description="The base propability that nav_sharing_out will be selected.",
    )

    return_: float = Field(
        0.1,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(),
        description="Extra configuration for the state",
    )


class FilesViewConfig(ProbabilisticStateConfig):
    """The files view states configuration (e.g., favorites)"""

    scroll_down: float = Field(
        0.15,
        description="The base propability that scroll_down will be selected.",
    )

    favorite: float = Field(
        0.05,
        description="The base propability that favorite will be selected.",
    )

    remove_favorite: float = Field(
        0.05,
        description="The base propability that remove_favorite will be selected.",
    )

    open_directory: float = Field(
        0.2,
        description="The base propability that open_directory will be selected.",
    )

    download_file: float = Field(
        0.1,
        description="The base propability that download_file will be selected.",
    )

    delete_file: float = Field(
        0.1,
        description="The base propability that delete_file will be selected.",
    )

    download_directory: float = Field(
        0.05,
        description="The base propability that download_directory will be selected.",
    )

    delete_directory: float = Field(
        0.05,
        description="The base propability that delete_directory will be selected.",
    )

    view_details: float = Field(
        0.15,
        description="The base propability that view_details will be selected.",
    )

    return_: float = Field(
        0.1,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(),
        description="Extra configuration for the state",
    )


FavoritesViewConfig = FilesViewConfig

SharingOutViewConfig = FilesViewConfig


class AllFilesViewConfig(ProbabilisticStateConfig):
    """The selecting menu states configuration"""

    scroll_down: float = Field(
        0.1,
        description="The base propability that scroll_down will be selected.",
    )

    favorite: float = Field(
        0.05,
        description="The base propability that favorite will be selected.",
    )

    remove_favorite: float = Field(
        0.05,
        description="The base propability that remove_favorite will be selected.",
    )

    open_directory: float = Field(
        0.1,
        description="The base propability that open_directory will be selected.",
    )

    nav_root: float = Field(
        0.075,
        description="The base propability that nav_root will be selected.",
    )

    download_file: float = Field(
        0.1,
        description="The base propability that download_file will be selected.",
    )

    delete_file: float = Field(
        0.075,
        description="The base propability that delete_file will be selected.",
    )

    upload_file: float = Field(
        0.075,
        description="The base propability that upload_file will be selected.",
    )

    download_directory: float = Field(
        0.05,
        description="The base propability that download_directory will be selected.",
    )

    delete_directory: float = Field(
        0.05,
        description="The base propability that delete_directory will be selected.",
    )

    create_directory: float = Field(
        0.075,
        description="The base propability that create_directory will be selected.",
    )

    view_details: float = Field(
        0.125,
        description="The base propability that view_details will be selected.",
    )

    return_: float = Field(
        0.075,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(),
        description="Extra configuration for the state",
    )


class SharingInViewConfig(ProbabilisticStateConfig):
    """The sharing in view state configuration"""

    scroll_down: float = Field(
        0.15,
        description="The base propability that scroll_down will be selected.",
    )

    accept: float = Field(
        0.4,
        description="The base propability that accept will be selected.",
    )

    decline: float = Field(
        0.35,
        description="The base propability that decline will be selected.",
    )

    return_: float = Field(
        0.1,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(),
        description="Extra configuration for the state",
    )


class FileDetailsViewConfig(ProbabilisticStateConfig):
    """The file details view state configuration"""

    view_comments: float = Field(
        0.25,
        description="The base propability that view_comments will be selected.",
    )

    view_sharing: float = Field(
        0.4,
        description="The base propability that view_sharing will be selected.",
    )

    view_versions: float = Field(
        0.25,
        description="The base propability that view_versions will be selected.",
    )

    return_: float = Field(
        0.1,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(),
        description="Extra configuration for the state",
    )


class SharingDetailsExtraConfig(ActivityExtraConfig):
    share_users: Dict[str, float] = Field(
        {},
        description="Dictionary of users to share to",
    )

    max_shares: Optional[int] = Field(
        None,
        description="The maximum number of users to share a single file/dir to",
    )


class SharingDetailsConfig(ProbabilisticStateConfig):
    """The sharing details view state configuration"""

    share: float = Field(
        0.4,
        description="The base propability that share will be selected.",
    )

    unshare: float = Field(
        0.35,
        description="The base propability that unshare will be selected.",
    )

    return_: float = Field(
        0.25,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: SharingDetailsExtraConfig = Field(
        SharingDetailsExtraConfig(),
        description="Extra configuration for the state",
    )


class UploadMenuConfig(ProbabilisticStateConfig):
    """The upload menu state configuration"""

    keep_new: float = Field(
        0.6,
        description="The base propability that keep_new will be selected.",
    )

    keep_both: float = Field(
        0.3,
        description="The base propability that keep_both will be selected.",
    )

    keep_old: float = Field(
        0.1,
        description="The base propability that keep_old will be selected.",
    )


class OwncloudStates(BaseModel):
    """Configuration class for all owncloud user activity states."""

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

    all_files: AllFilesViewConfig = Field(
        AllFilesViewConfig(),
        description="The all files view state config",
    )

    favorites: FavoritesViewConfig = Field(
        FavoritesViewConfig(),
        description="The favorites view state config",
    )

    sharing_in: SharingInViewConfig = Field(
        SharingInViewConfig(),
        description="The sharing_in view state config",
    )

    sharing_out: SharingOutViewConfig = Field(
        SharingOutViewConfig(),
        description="The sharing_out view state config",
    )

    file_details: FileDetailsViewConfig = Field(
        FileDetailsViewConfig(),
        description="The file details state config",
    )

    sharing_details: SharingDetailsConfig = Field(
        SharingDetailsConfig(),
        description="The sharing details tab state config",
    )

    upload_menu: UploadMenuConfig = Field(
        UploadMenuConfig(),
        description="The upload menu state config",
    )


class OwncloudUserStates(OwncloudStates):
    """Configuration class for the owncloud user state machine states"""

    selecting_activity: ActivitySelectionConfig = Field(
        ActivitySelectionConfig(),
        description="The selecting activity states config",
    )


class OwncloudUserConfig(BaseModel):
    """Configuration class for the owncloud user"""

    url: HttpUrl = Field(
        "http://localhost",
        description="The owncloud servers url",
    )

    username: str = Field(
        "mmustermann",
        description="The users username",
    )

    password: str = Field(
        "passwd123",
        description="The users password",
    )

    max_daily: int = Field(
        10,
        description=(
            "The maximum amount of times the owncloud user "
            "activity will be entered per day"
        ),
    )

    upload_files: Dict[str, float] = Field(
        [],
        description="Files the user might upload mapped to their propabilities",
    )

    modify_directories: List[Pattern] = Field(
        [re.compile(r"\/.+")],
        description=(
            "List of regular expresions used to control which "
            "directories can be modified. i.e., dir create, file upload, delete"
        ),
    )

    max_directory_create_depth: Optional[int] = Field(
        None,
        description="The maximum directory level to create sub directories in.",
    )

    max_directory_count: Optional[int] = Field(
        None,
        description="The maximum sub directories to create.",
    )

    favor_factor: float = Field(
        1.0,
        description="Factor used to decrease favorite and remove_favorite chance.",
    )

    min_scroll_space: float = Field(
        200.0,
        description=(
            "The minimum amount of scroll space that has to be "
            "available for the user to consider scrolling down."
        ),
    )

    _validate_favor_factor = validator("favor_factor", allow_reuse=True)(
        positive_smaller_one
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

    owncloud_user: OwncloudUserConfig = Field(
        OwncloudUserConfig(),
        description="The owncloud user config",
    )

    states: OwncloudUserStates = Field(
        OwncloudUserStates(),
        description="The states configuration for the state machine",
    )

    @validator("selenium")
    def validate_download_no_prompt(cls, value: SeleniumConfig) -> SeleniumConfig:
        assert (
            value.download.prompt is False
        ), "The selenium browser download prompt must be turned of for this sm!"
        return value
