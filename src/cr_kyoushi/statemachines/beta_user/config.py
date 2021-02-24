"""Configuration classes for the horde user activity and state machine"""

from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    FilePath,
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

    horde: Optional[HordeStates] = Field(
        HordeStates(),
        description="The horde user states config",
    )

    owncloud: Optional[OwncloudStates] = Field(
        OwncloudStates(),
        description="The owncloud user states config",
    )

    ssh_user: Optional[SSHStates] = Field(
        SSHStates(),
        description="The SSH user states config",
    )

    web_browser: Optional[WebBrowserStates] = Field(
        WebBrowserStates(),
        description="The web browser user states config",
    )

    wp_editor: Optional[WordpressEditorStates] = Field(
        WordpressEditorStates(),
        description="The wordpress editor user states config",
    )

    wpdiscuz: Optional[WpDiscuzStates] = Field(
        WpDiscuzStates(),
        description="The wpdiscuz user states config",
    )

    @validator("wpdiscuz", always=True)
    def validate_wpdiscuz_states_config_presence(
        cls, value: Optional[WpDiscuzConfig], values
    ) -> Optional[WpDiscuzConfig]:
        if "activities" in values and values["activities"].wpdiscuz > 0:
            assert (
                value is not None
            ), "There must be a wpdiscuz states config if the activity is enabled!"
        return value

    @validator("wp_editor", always=True)
    def validate_wp_editor_states_config_presence(
        cls, value: Optional[WordpressEditorConfig], values
    ) -> Optional[WordpressEditorConfig]:
        if "activities" in values and values["activities"].wp_editor > 0:
            assert (
                value is not None
            ), "There must be a wp_editor states config if the activity is enabled!"
        return value

    @validator("web_browser", always=True)
    def validate_web_browser_states_config_presence(
        cls, value: Optional[WebBrowserConfig], values
    ) -> Optional[WebBrowserConfig]:
        if "activities" in values and values["activities"].web_browser > 0:
            assert (
                value is not None
            ), "There must be a web_browser states config if the activity is enabled!"
        return value

    @validator("ssh_user", always=True)
    def validate_ssh_user_states_config_presence(
        cls, value: Optional[SSHUserConfig], values
    ) -> Optional[SSHUserConfig]:
        if "activities" in values and values["activities"].ssh_user > 0:
            assert (
                value is not None
            ), "There must be a ssh_user states config if the activity is enabled!"
        return value

    @validator("owncloud", always=True)
    def validate_owncloud_states_config_presence(
        cls, value: Optional[OwncloudUserConfig], values
    ) -> Optional[OwncloudUserConfig]:
        if "activities" in values and values["activities"].owncloud > 0:
            assert (
                value is not None
            ), "There must be a owncloud states config if the activity is enabled!"
        return value

    @validator("horde", always=True)
    def validate_horde_states_config_presence(
        cls, value: Optional[HordeConfig], values
    ) -> Optional[HordeConfig]:
        if "activities" in values and values["activities"].horde > 0:
            assert (
                value is not None
            ), "There must be a horde states config if the activity is enabled!"
        return value


class VPNConfig(BaseModel):
    enabled: bool = Field(
        False,
        description="If the users uses the VPN or not",
    )

    config: Optional[FilePath] = Field(
        None,
        description="The OpenVPN configuration to use.",
    )

    eager: bool = Field(
        True,
        description="If the user should connect to the VPN as soon as they execute any activity.",
    )

    horde: bool = Field(
        False,
        description="If the horde activity requires the VPN",
    )

    owncloud: bool = Field(
        False,
        description="If the owncloud activity requires the VPN",
    )

    ssh_user: bool = Field(
        False,
        description="If the ssh_user activity requires the VPN",
    )

    web_browser: bool = Field(
        False,
        description="If the web_browser activity requires the VPN",
    )

    wp_editor: bool = Field(
        False,
        description="If the wp_editor activity requires the VPN",
    )

    wpdiscuz: bool = Field(
        False,
        description="If the wpdiscuz activity requires the VPN",
    )

    @validator("config", always=True)
    def validate_config(cls, value: Optional[FilePath], values) -> Optional[FilePath]:
        if "enabled" in values and values["enabled"] is True:
            assert value is not None, "A VPN config is required if the VPN is enabled!"
        return value


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

    vpn: VPNConfig = Field(
        VPNConfig(),
        description="The VPN configuration for the simulation user",
    )

    states: StatesConfig = Field(
        StatesConfig(),
        description="The horde state machines states configuration",
    )

    horde: Optional[HordeConfig] = Field(
        None,
        description="The horde user specific configuration",
    )

    owncloud: Optional[OwncloudUserConfig] = Field(
        None,
        description="The owncloud user config",
    )

    ssh_user: Optional[SSHUserConfig] = Field(
        None,
        description="The SSH user config",
    )

    web_browser: Optional[WebBrowserConfig] = Field(
        None,
        description="The web browser user config",
    )

    wp_editor: Optional[WordpressEditorConfig] = Field(
        None,
        description="The wordpress editor user config",
    )

    wpdiscuz: Optional[WpDiscuzConfig] = Field(
        None,
        description="The wpdiscuz user config",
    )

    @validator("selenium")
    def validate_download_no_prompt(cls, value: SeleniumConfig) -> SeleniumConfig:
        assert (
            value.download.prompt is False
        ), "The selenium browser download prompt must be turned of for this sm!"
        return value

    @validator("wpdiscuz", always=True)
    def validate_wpdiscuz_config_presence(
        cls, value: Optional[WpDiscuzConfig], values
    ) -> Optional[WpDiscuzConfig]:
        if "states" in values and values["states"].activities.wpdiscuz > 0:
            assert (
                value is not None
            ), "There must be a wpdiscuz config if the activity is enabled!"
        return value

    @validator("wp_editor", always=True)
    def validate_wp_editor_config_presence(
        cls, value: Optional[WordpressEditorConfig], values
    ) -> Optional[WordpressEditorConfig]:
        if "states" in values and values["states"].activities.wp_editor > 0:
            assert (
                value is not None
            ), "There must be a wp_editor config if the activity is enabled!"
        return value

    @validator("web_browser", always=True)
    def validate_web_browser_config_presence(
        cls, value: Optional[WebBrowserConfig], values
    ) -> Optional[WebBrowserConfig]:
        if "states" in values and values["states"].activities.web_browser > 0:
            assert (
                value is not None
            ), "There must be a web_browser config if the activity is enabled!"
        return value

    @validator("ssh_user", always=True)
    def validate_ssh_user_config_presence(
        cls, value: Optional[SSHUserConfig], values
    ) -> Optional[SSHUserConfig]:
        if "states" in values and values["states"].activities.ssh_user > 0:
            assert (
                value is not None
            ), "There must be a ssh_user config if the activity is enabled!"
        return value

    @validator("owncloud", always=True)
    def validate_owncloud_config_presence(
        cls, value: Optional[OwncloudUserConfig], values
    ) -> Optional[OwncloudUserConfig]:
        if "states" in values and values["states"].activities.owncloud > 0:
            assert (
                value is not None
            ), "There must be a owncloud config if the activity is enabled!"
        return value

    @validator("horde", always=True)
    def validate_horde_config_presence(
        cls, value: Optional[HordeConfig], values
    ) -> Optional[HordeConfig]:
        if "states" in values and values["states"].activities.horde > 0:
            assert (
                value is not None
            ), "There must be a horde config if the activity is enabled!"
        return value
