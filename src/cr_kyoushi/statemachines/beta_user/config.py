"""Configuration classes for the horde user activity and state machine"""


from pydantic import (
    BaseModel,
    Field,
    validator,
)

from ..core.config import ProbabilisticStateConfig
from ..core.selenium import (
    SeleniumConfig,
    SeleniumStatemachineConfig,
)
from ..horde_user.config import (
    HordeConfig,
    HordeStates,
)
from ..owncloud_user.config import (
    OwncloudStates,
    OwncloudUserConfig,
)
from ..ssh_user.config import (
    SSHStates,
    SSHUserConfig,
)
from ..web_browser.config import UserConfig as WebBrowserConfig
from ..web_browser.config import WebBrowserStates
from ..wordpress_editor.config import (
    WordpressEditorConfig,
    WordpressEditorStates,
)
from ..wordpress_wpdiscuz.config import (
    WpDiscuzConfig,
    WpDiscuzStates,
)


class ActivitySelectionConfig(ProbabilisticStateConfig):
    """Horde user state machines selecting activity states configuration."""

    horde: float = Field(
        0.3,
        description="The base propability that the horde activity will be selected.",
    )

    owncloud: float = Field(
        0.15,
        description="The base propability that the owncloud activity will be selected.",
    )

    ssh_user: float = Field(
        0,
        description="The base propability that the ssh_user activity will be selected.",
    )

    web_browser: float = Field(
        0.2,
        description="The base propability that the web_browser activity will be selected.",
    )

    wp_editor: float = Field(
        0,
        description="The base propability that the wp_editor activity will be selected.",
    )

    wpdiscuz: float = Field(
        0.15,
        description="The base propability that the wpdiscuz activity will be selected.",
    )

    idle: float = Field(
        0.2,
        description="The base propability that the user will idle.",
    )


class StatesConfig(BaseModel):
    activities: ActivitySelectionConfig = Field(
        ActivitySelectionConfig(),
        description="The activity selection states configuration",
    )

    horde: HordeStates = Field(
        HordeStates(),
        description="The horde user states config",
    )

    owncloud: OwncloudStates = Field(
        OwncloudStates(),
        description="The owncloud user states config",
    )

    ssh_user: SSHStates = Field(
        SSHStates(),
        description="The SSH user states config",
    )

    web_browser: WebBrowserStates = Field(
        WebBrowserStates(),
        description="The web browser user states config",
    )

    wp_editor: WordpressEditorStates = Field(
        WordpressEditorStates(),
        description="The wordpress editor user states config",
    )

    wpdiscuz: WpDiscuzStates = Field(
        WpDiscuzStates(),
        description="The wpdiscuz user states config",
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

    states: StatesConfig = Field(
        StatesConfig(),
        description="The horde state machines states configuration",
    )

    horde: HordeConfig = Field(
        HordeConfig(),
        description="The horde user specific configuration",
    )

    owncloud: OwncloudUserConfig = Field(
        OwncloudUserConfig(),
        description="The owncloud user config",
    )

    ssh_user: SSHUserConfig = Field(
        SSHUserConfig(),
        description="The SSH user config",
    )

    web_browser: WebBrowserConfig = Field(
        WebBrowserConfig(),
        description="The web browser user config",
    )

    wp_editor: WordpressEditorConfig = Field(
        WordpressEditorConfig(),
        description="The wordpress editor user config",
    )

    wpdiscuz: WpDiscuzConfig = Field(
        WpDiscuzConfig(),
        description="The wpdiscuz user config",
    )

    @validator("selenium")
    def validate_download_no_prompt(cls, value: SeleniumConfig) -> SeleniumConfig:
        assert (
            value.download.prompt is False
        ), "The selenium browser download prompt must be turned of for this sm!"
        return value
