"""Statemachine that only idles or executes the owncloud user activity."""
from datetime import datetime
from typing import (
    List,
    Optional,
    Tuple,
)

from cr_kyoushi.simulation import sm
from cr_kyoushi.simulation.model import WorkSchedule
from cr_kyoushi.simulation.states import (
    SequentialState,
    State,
)
from cr_kyoushi.simulation.transitions import Transition

from ..core.config import IdleConfig
from ..core.selenium import (
    SeleniumConfig,
    SeleniumStatemachine,
)
from ..core.transitions import IdleTransition
from ..horde_user import activities as horde_activities
from ..horde_user.config import (
    HordeConfig,
    HordeStates,
)
from ..owncloud_user import activities as owncloud_activities
from ..owncloud_user.config import (
    OwncloudStates,
    OwncloudUserConfig,
)
from ..ssh_user import activities as ssh_activities
from ..ssh_user.actions import disconnect as ssh_disconnect
from ..ssh_user.config import (
    SSHStates,
    SSHUserConfig,
)
from ..web_browser import activities as browser_activities
from ..web_browser.config import UserConfig as WebBrowserConfig
from ..web_browser.config import WebBrowserStates
from ..wordpress_editor import activities as editor_activities
from ..wordpress_editor.config import (
    WordpressEditorConfig,
    WordpressEditorStates,
)
from ..wordpress_editor.context import WordpressEditorContext
from ..wordpress_wpdiscuz import activities as wpdiscuz_activites
from ..wordpress_wpdiscuz.config import (
    WpDiscuzConfig,
    WpDiscuzStates,
)
from ..wordpress_wpdiscuz.context import WpDiscuzContext
from .actions import (
    VPNConnect,
    vpn_disconnect,
)
from .config import (
    StatemachineConfig,
    VPNConfig,
)
from .context import (
    Context,
    ContextModel,
)
from .states import ActivitySelectionState


__all__ = ["Statemachine", "StatemachineFactory"]


class Statemachine(SeleniumStatemachine[Context]):
    """Beta user state machine"""

    def __init__(
        self,
        wpdiscuz_config: Optional[WpDiscuzConfig],
        wp_editor_config: Optional[WordpressEditorConfig],
        initial_state: str,
        states: List[State],
        selenium_config: SeleniumConfig,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        work_schedule: Optional[WorkSchedule] = None,
        max_errors: int = 0,
    ):
        super().__init__(
            initial_state,
            states,
            selenium_config,
            start_time=start_time,
            end_time=end_time,
            work_schedule=work_schedule,
            max_errors=max_errors,
        )
        self._wp_editor: Optional[WordpressEditorConfig] = wp_editor_config
        self._wpdiscuz: Optional[WpDiscuzConfig] = wpdiscuz_config

    def setup_context(self):
        driver = self.get_driver()

        if self._wp_editor is not None:
            editor_context = WordpressEditorContext(
                username=self._wp_editor.username,
                password=self._wp_editor.password,
            )
        else:
            # if we have no wp_editor config (i.e., wp_editor activity is disabled)
            # then we just set a dummy context as it won't be used anyways
            editor_context = WordpressEditorContext(
                username="dummy",
                password="dummy",
            )

        if self._wpdiscuz is not None:
            reader_context = WpDiscuzContext(
                author=self._wpdiscuz.author,
                email=self._wpdiscuz.email,
            )
        else:
            # if we have no wpdiscuz config (i.e., wpdiscuz activity is disabled)
            # then we just set a dummy context as it won't be used anyways
            reader_context = WpDiscuzContext(
                author="dummy",
                email="dummy",
            )

        self.context = ContextModel(
            driver=driver,
            main_window=driver.current_window_handle,
            fake=self.fake,
            wp_editor=editor_context,
            wpdiscuz=reader_context,
        )

    def destroy_context(self):
        # when we have a context
        if self.context is not None:

            # and a shell
            if self.context.ssh_user.shell is not None:
                ssh_disconnect(self.log, self.current_state, self.context, None)

            # and a vpn process
            if self.context.vpn_process is not None:
                # disconnect from the VPN
                vpn_disconnect(self.log, self.current_state, self.context, None)

        # need to destroy after our code as we still need the context
        super().destroy_context()


class StatemachineFactory(sm.StatemachineFactory):
    """Owncloud user activity state machine factory"""

    @property
    def name(self) -> str:
        return "OwncloudUserStatemachineFactory"

    @property
    def config_class(self):
        return StatemachineConfig

    def __init__(self):
        self.states: List[State] = []

    def build_horde(self, idle: IdleConfig, horde: HordeConfig, states: HordeStates):
        """Builds and configures the horde activity

        Args:
            idle: The idle config
            horde: The horde user config
            states: The horde states config

        Returns:
            The horde enter activity transition
        """

        # get base states and transitions

        name_prefix = "horde"

        (
            # transitions
            horde_transition,
            pause_horde,
            return_select,
            # states
            login_check,
            login_page,
            logout_choice,
        ) = horde_activities.get_base_activity(
            idle=idle,
            horde=horde,
            login_config=states.login_page,
            logout_config=states.logout_choice,
            name_prefix=name_prefix,
        )
        # add states to factory state list
        self.states.extend([login_check, login_page, logout_choice])

        # mail states and nav
        (
            nav_mail,
            mails_page,
            mail_view,
            mail_info,
            mail_compose,
        ) = horde_activities.get_mail_activity(
            idle=idle,
            horde=horde,
            page_config=states.mails_page,
            view_config=states.mail_view,
            info_config=states.mail_info,
            return_select=return_select,
            name_prefix=name_prefix,
        )
        # add states to factory state list
        self.states.extend([mails_page, mail_view, mail_info, mail_compose])

        # preferences states and nav
        (
            nav_preferences,
            preferences_page,
            preferences_personal_page,
        ) = horde_activities.get_preferences_activity(
            idle=idle,
            horde=horde,
            name_prefix=name_prefix,
        )
        # add states to factory state list
        self.states.extend([preferences_page, preferences_personal_page])

        # admin states and nav

        (
            nav_admin,
            # states
            admin_page,
            admin_config_page,
            admin_groups_page,
            admin_group_added,
            admin_group_deleting,
            admin_php_shell_page,
            admin_sql_shell_page,
            admin_cli_shell_page,
        ) = horde_activities.get_admin_activity(
            idle=idle,
            admin_config=states.admin_page,
            groups_config=states.admin_groups_page,
            return_select=return_select,
            name_prefix=name_prefix,
        )
        # add states to factory state list
        self.states.extend(
            [
                admin_page,
                admin_config_page,
                admin_groups_page,
                admin_group_added,
                admin_group_deleting,
                admin_php_shell_page,
                admin_sql_shell_page,
                admin_cli_shell_page,
            ]
        )

        # notes states and nav

        (
            nav_notes,
            # states
            notes_page,
            note_creator,
            note_editor,
        ) = horde_activities.get_notes_activity(
            idle=idle,
            page_config=states.notes_page,
            editor_config=states.note_editor,
            return_select=return_select,
            name_prefix=name_prefix,
        )
        # add states to factory state list
        self.states.extend([notes_page, note_creator, note_editor])

        # tasks states and nav

        (
            nav_tasks,
            # states
            tasks_page,
            task_creator,
            task_editor,
        ) = horde_activities.get_tasks_activity(
            idle=idle,
            page_config=states.tasks_page,
            return_select=return_select,
            name_prefix=name_prefix,
        )
        # add states to factory state list
        self.states.extend([tasks_page, task_creator, task_editor])

        # address book states and nav

        (
            nav_address_book,
            # states
            address_book_page,
            contact_compose,
            contacts_browser,
            contact_info,
            contact_delete_confirming,
        ) = horde_activities.get_address_book_activity(
            idle=idle,
            page_config=states.address_book_page,
            browser_config=states.contacts_browser,
            info_config=states.contact_info,
            return_select=return_select,
            name_prefix=name_prefix,
        )
        # add states to factory state list
        self.states.extend(
            [
                address_book_page,
                contact_compose,
                contacts_browser,
                contact_info,
                contact_delete_confirming,
            ]
        )

        # calendar states and nav

        (
            nav_calendar,
            # states
            calendar_page,
            event_compose,
            event_edit,
        ) = horde_activities.get_calendar_activity(
            idle=idle,
            page_config=states.calendar_page,
            edit_config=states.event_edit,
            return_select=return_select,
            name_prefix=name_prefix,
        )
        # add states to factory state list
        self.states.extend([calendar_page, event_compose, event_edit])

        # create and add horde main menu state

        self.states.append(
            horde_activities.get_menu_activity(
                states.selecting_menu,
                nav_mail,
                nav_preferences,
                nav_admin,
                nav_notes,
                nav_tasks,
                nav_address_book,
                nav_calendar,
                pause_horde,
                name_prefix=name_prefix,
            )
        )

        return horde_transition

    def build_owncloud(
        self,
        idle: IdleConfig,
        user_config: OwncloudUserConfig,
        states_config: OwncloudStates,
        selenium_config: SeleniumConfig,
    ) -> Transition:
        """Builds and configures the owncloud activity

        Args:
            idle: The idle config
            user_config: The owncloud user config
            states_config: The owncloud states config
            selenium_config: The selenium config

        Returns:
            The owncloud enter activity transition
        """

        name_prefix = "owncloud"

        # create and add owncloud base activity
        (
            goto_owncloud,
            pause,
            logged_in_check,
            login_page,
            logout_choice,
        ) = owncloud_activities.get_base_activity(
            idle=idle,
            owncloud=user_config,
            login_config=states_config.login_page,
            logout_config=states_config.logout_choice,
            name_prefix=name_prefix,
        )

        self.states.extend([logged_in_check, login_page, logout_choice])

        # create and add owncloud file view activity
        self.states.extend(
            owncloud_activities.get_file_view_activity(
                idle=idle,
                download_config=selenium_config.download,
                owncloud=user_config,
                menu_config=states_config.selecting_menu,
                all_files_config=states_config.all_files,
                favorites_config=states_config.favorites,
                sharing_in_config=states_config.sharing_in,
                sharing_out_config=states_config.sharing_out,
                upload_menu_config=states_config.upload_menu,
                pause_owncloud=pause,
                name_prefix=name_prefix,
            )
        )

        # create and add owncloud file details activity
        self.states.extend(
            owncloud_activities.get_file_details_activity(
                idle=idle,
                details_config=states_config.file_details,
                sharing_config=states_config.sharing_details,
                name_prefix=name_prefix,
            )
        )

        return goto_owncloud

    def build_ssh(
        self, idle: IdleConfig, user: SSHUserConfig, states: SSHStates
    ) -> Transition:
        """Builds and configures the ssh user activity

        Args:
            idle: The idle config
            user: The ssh user config
            states: The ssh states config

        Returns:
            The ssh user enter activity transition
        """

        name_prefix = "ssh"

        # build ssh activity
        (
            select_ssh_server,
            selected_server,
            connected,
            executing_chain,
            sudo_check,
            sudo_dialog,
        ) = ssh_activities.get_ssh_activity(
            idle=idle,
            user=user,
            connected_config=states.connected,
            sudo_config=states.sudo_dialog,
            name_prefix=name_prefix,
        )
        # add ssh states to factory list
        self.states.extend(
            [
                selected_server,
                connected,
                executing_chain,
                sudo_check,
                sudo_dialog,
            ]
        )

        return select_ssh_server

    def build_browser(
        self,
        idle: IdleConfig,
        user_config: WebBrowserConfig,
        states_config: WebBrowserStates,
    ) -> Transition:
        """Builds and configures the web browser user activity

        Args:
            idle: The idle config
            user: The web browser user config
            states: The web browser states config

        Returns:
            The web browser user enter activity transition
        """
        name_prefix = "browser"

        # build web browser activity
        (
            website_transition,
            on_website,
            leaving_website,
        ) = browser_activities.get_browser_activity(
            idle,
            user_config,
            states_config,
            name_prefix=name_prefix,
        )

        # add web browser states to factory states
        self.states.extend([on_website, leaving_website])

        return website_transition

    def build_wp_editor(
        self,
        idle: IdleConfig,
        user_config: WordpressEditorConfig,
        states_config: WordpressEditorStates,
    ) -> Transition:
        """Builds and configures the wordpress editor activity

        Args:
            idle: The idle config
            user: The wordpress editor config
            states: The wordpress editor states config

        Returns:
            The wordpress editor enter activity transition
        """

        name_prefix = "wp_editor"

        # create wp editor base activity
        (
            goto_wp_admin,
            pause,
            logged_in_check,
            login_page,
            logout_choice,
        ) = editor_activities.get_base_activity(
            idle=idle,
            user_config=user_config,
            login_config=states_config.login_page,
            logout_config=states_config.logout_choice,
            name_prefix=name_prefix,
        )
        # add base activity states to factory
        self.states.extend([logged_in_check, login_page, logout_choice])

        # create and add wp editor core activity states
        self.states.extend(
            editor_activities.get_editor_activity(
                idle=idle,
                user_config=user_config,
                menu_config=states_config.selecting_menu,
                comments_config=states_config.comments_page,
                posts_config=states_config.posts_page,
                pause_wordpress=pause,
                name_prefix=name_prefix,
            )
        )

        return goto_wp_admin

    def build_wpdiscuz(
        self,
        idle: IdleConfig,
        user_config: WpDiscuzConfig,
        states_config: WpDiscuzStates,
    ) -> Transition:
        """Builds and configures the wordpress wpdiscuz user activity

        Args:
            idle: The idle config
            user: The wordpress wpdiscuz user config
            states: The wordpress wpdiscuz states config

        Returns:
            The web browser user enter activity transition
        """

        name_prefix = "wpdiscuz"

        # create base activity
        (
            goto_wordpress,
            posts_page,
            close_choice,
        ) = wpdiscuz_activites.get_posts_activity(
            idle=idle,
            user_config=user_config,
            posts_config=states_config.posts_page,
            close_config=states_config.close_choice,
            name_prefix=name_prefix,
        )
        # add posts anc close states
        self.states.extend([posts_page, close_choice])

        # create and add post and comment states
        self.states.extend(
            wpdiscuz_activites.get_post_activity(
                idle=idle,
                post_config=states_config.post_page,
                return_home=goto_wordpress,
                name_prefix=name_prefix,
            )
        )

        return goto_wordpress

    def __pre_vpn(self, name: str, original: Transition, vpn_connect: Transition):
        connected = SequentialState("vpn_connected", original, name_prefix=name)
        self.states.append(connected)
        return Transition(
            vpn_connect,
            name="vpn_connect",
            target=connected.name,
            name_prefix=name,
        )

    def configure_vpn(
        self,
        vpn: VPNConfig,
        goto_horde: Optional[Transition],
        goto_owncloud: Optional[Transition],
        start_ssh: Optional[Transition],
        goto_website: Optional[Transition],
        goto_wp_admin: Optional[Transition],
        goto_wordpress: Optional[Transition],
    ) -> Tuple[
        Optional[Transition],
        Optional[Transition],
        Optional[Transition],
        Optional[Transition],
        Optional[Transition],
        Optional[Transition],
    ]:
        # can't be None if enabled
        assert vpn.config is not None
        vpn_connect = VPNConnect(vpn.config)

        horde_transition = (
            self.__pre_vpn("horde", goto_horde, vpn_connect)
            if (vpn.eager or vpn.horde) and goto_horde is not None
            else goto_horde
        )

        owncloud_transition = (
            self.__pre_vpn("owncloud", goto_owncloud, vpn_connect)
            if (vpn.eager or vpn.owncloud) and goto_owncloud is not None
            else goto_owncloud
        )

        ssh_user_transition = (
            self.__pre_vpn("ssh_user", start_ssh, vpn_connect)
            if (vpn.eager or vpn.ssh_user) and start_ssh is not None
            else start_ssh
        )

        web_browser_transition = (
            self.__pre_vpn("web_browser", goto_website, vpn_connect)
            if (vpn.eager or vpn.web_browser) and goto_website is not None
            else goto_website
        )

        wp_editor_transition = (
            self.__pre_vpn("wp_editor", goto_wp_admin, vpn_connect)
            if (vpn.eager or vpn.wp_editor) and goto_wp_admin is not None
            else goto_wp_admin
        )

        wpdiscuz_transition = (
            self.__pre_vpn("wpdiscuz", goto_wordpress, vpn_connect)
            if (vpn.eager or vpn.wpdiscuz) and goto_wordpress is not None
            else goto_wordpress
        )

        return (
            horde_transition,
            owncloud_transition,
            ssh_user_transition,
            web_browser_transition,
            wp_editor_transition,
            wpdiscuz_transition,
        )

    def build(self, config: StatemachineConfig):
        idle = config.idle
        states_config = config.states
        activities = states_config.activities
        activities_loaded: List[str] = []

        # initialize activity entry transitions with None
        # as they are all optional
        goto_horde: Optional[Transition] = None
        goto_owncloud: Optional[Transition] = None
        start_ssh: Optional[Transition] = None
        goto_website: Optional[Transition] = None
        goto_wp_admin: Optional[Transition] = None
        goto_wordpress: Optional[Transition] = None

        if (
            activities.horde > 0
            and config.horde is not None
            and states_config.horde is not None
        ):
            goto_horde = self.build_horde(idle, config.horde, states_config.horde)
            activities_loaded.append("horde")

        if (
            activities.owncloud > 0
            and config.owncloud is not None
            and states_config.owncloud is not None
        ):
            goto_owncloud = self.build_owncloud(
                idle, config.owncloud, states_config.owncloud, config.selenium
            )
            activities_loaded.append("owncloud")

        if (
            activities.ssh_user > 0
            and config.ssh_user is not None
            and states_config.ssh_user is not None
        ):
            start_ssh = self.build_ssh(idle, config.ssh_user, states_config.ssh_user)
            activities_loaded.append("ssh_user")

        if (
            activities.web_browser > 0
            and config.web_browser is not None
            and states_config.web_browser is not None
        ):
            goto_website = self.build_browser(
                idle, config.web_browser, states_config.web_browser
            )
            activities_loaded.append("web_browser")

        if (
            activities.wp_editor > 0
            and config.wp_editor is not None
            and states_config.wp_editor is not None
        ):
            goto_wp_admin = self.build_wp_editor(
                idle, config.wp_editor, states_config.wp_editor
            )
            activities_loaded.append("wp_editor")

        if (
            activities.wpdiscuz > 0
            and config.wpdiscuz is not None
            and states_config.wpdiscuz is not None
        ):
            goto_wordpress = self.build_wpdiscuz(
                idle, config.wpdiscuz, states_config.wpdiscuz
            )
            activities_loaded.append("wpdiscuz")

        idle_transition = IdleTransition(
            idle_amount=idle.big,
            end_time=config.end_time,
            name="idle",
            target="selecting_activity",
        )

        if config.vpn.enabled:
            # configure activity entry transitions with VPN pre transitions
            (
                horde_transition,
                owncloud_transition,
                ssh_user_transition,
                web_browser_transition,
                wp_editor_transition,
                wpdiscuz_transition,
            ) = self.configure_vpn(
                config.vpn,
                goto_horde,
                goto_owncloud,
                start_ssh,
                goto_website,
                goto_wp_admin,
                goto_wordpress,
            )

        else:
            horde_transition = goto_horde
            owncloud_transition = goto_owncloud
            ssh_user_transition = start_ssh
            web_browser_transition = goto_website
            wp_editor_transition = goto_wp_admin
            wpdiscuz_transition = goto_wordpress

        initial = ActivitySelectionState(
            name="selecting_activity",
            horde=horde_transition,
            owncloud=owncloud_transition,
            ssh_user=ssh_user_transition,
            web_browser=web_browser_transition,
            wp_editor=wp_editor_transition,
            wpdiscuz=wpdiscuz_transition,
            idle=idle_transition,
            horde_weight=activities.horde,
            owncloud_weight=activities.owncloud,
            ssh_user_weight=activities.ssh_user,
            web_browser_weight=activities.web_browser,
            wp_editor_weight=activities.wp_editor,
            wpdiscuz_weight=activities.wpdiscuz,
            idle_weight=activities.idle,
            horde_max_daily=config.horde.max_daily
            if config.horde is not None
            else None,
            owncloud_max_daily=config.owncloud.max_daily
            if config.owncloud is not None
            else None,
            ssh_user_max_daily=config.ssh_user.max_daily
            if config.ssh_user is not None
            else None,
            web_browser_max_daily=config.web_browser.max_daily
            if config.web_browser is not None
            else None,
            wp_editor_max_daily=config.wp_editor.max_daily
            if config.wp_editor is not None
            else None,
            wpdiscuz_max_daily=config.wpdiscuz.max_daily
            if config.wpdiscuz is not None
            else None,
        )

        self.states.append(initial)

        sm = Statemachine(
            wpdiscuz_config=config.wpdiscuz,
            wp_editor_config=config.wp_editor,
            initial_state="selecting_activity",
            states=self.states,
            selenium_config=config.selenium,
            start_time=config.start_time,
            end_time=config.end_time,
            work_schedule=config.schedule,
            max_errors=config.max_errors,
        )

        sm.log.info("Loaded activities", activities=activities_loaded)

        return sm
