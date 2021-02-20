"""
A collection of helper functions used to create the various sub activities of the OwnCloud user activity.
"""

from typing import (
    Optional,
    Tuple,
)

from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    Transition,
    noop,
)

from ..core.config import IdleConfig
from ..core.selenium import SeleniumDownloadConfig
from . import (
    actions,
    config,
    nav,
    states,
)


def get_base_activity(
    idle: IdleConfig,
    owncloud: config.OwncloudUserConfig,
    login_config: config.LoginPageConfig,
    logout_config: config.LogoutChoiceConfig,
    root: str = "selecting_activity",
    selecting_menu: str = "selecting_menu",
    login_check: str = "login_check",
    login_page: str = "login_page",
    logout_choice: str = "logout?",
    # transitions
    owncloud_transition: str = "go_to_owncloud",
    login: str = "login",
    fail_login: str = "fail_login",
    pause_owncloud: str = "pause_owncloud",
    owncloud_logout: str = "owncloud_logout",
    return_select: str = "return_select",
    name_prefix: Optional[str] = None,
) -> Tuple[
    # transitions
    Transition,
    Transition,
    # states
    states.LoggedInCheck,
    states.LoginPage,
    states.LogoutChoice,
]:
    """Creates the owncloud base activity (i.e., login and logout) and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The owncloud open, pause and return to selection menu transition as well as the
        login and logout states.
    """

    if name_prefix:
        target_selecting_menu = f"{name_prefix}_{selecting_menu}"
        target_login_check = f"{name_prefix}_{login_check}"
        target_login_page = f"{name_prefix}_{login_page}"
        target_logout_choice = f"{name_prefix}_{logout_choice}"
    else:
        target_selecting_menu = selecting_menu
        target_login_check = login_check
        target_login_page = login_page
        target_logout_choice = logout_choice

    t_owncloud_transition = Transition(
        transition_function=nav.GoToOwncloud(owncloud.url),
        name=owncloud_transition,
        target=target_login_check,
        name_prefix=name_prefix,
    )

    t_login = DelayedTransition(
        transition_function=actions.LoginToOwncloud(
            username=owncloud.username,
            password=owncloud.password,
        ),
        name=login,
        target=target_selecting_menu,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_fail_login = DelayedTransition(
        transition_function=actions.FailLoginToOwncloud(
            username=owncloud.username,
            password=owncloud.password,
        ),
        name=fail_login,
        target=target_login_page,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_pause_owncloud = DelayedTransition(
        transition_function=noop,
        name=pause_owncloud,
        target=target_logout_choice,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_owncloud_logout = DelayedTransition(
        transition_function=actions.logout_of_owncloud,
        name=owncloud_logout,
        target=root,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    s_login_check = states.LoggedInCheck(
        name=login_check,
        login_state=target_login_page,
        selecting_menu_state=target_selecting_menu,
        name_prefix=name_prefix,
    )

    s_login_page = states.LoginPage(
        name=login_page,
        login=t_login,
        fail_login=t_fail_login,
        fail_weight=login_config.fail_chance,
        fail_decrease_factor=login_config.fail_decrease,
        name_prefix=name_prefix,
    )

    s_logout_choice = states.LogoutChoice(
        name=logout_choice,
        logout=t_owncloud_logout,
        logout_prob=logout_config.logout_chance,
        name_prefix=name_prefix,
    )

    return (
        # transitions
        t_owncloud_transition,
        t_pause_owncloud,
        # states
        s_login_check,
        s_login_page,
        s_logout_choice,
    )


def get_file_view_activity(
    idle: IdleConfig,
    download_config: SeleniumDownloadConfig,
    owncloud: config.OwncloudUserConfig,
    menu_config: config.SelectingMenuConfig,
    all_files_config: config.AllFilesViewConfig,
    favorites_config: config.FavoritesViewConfig,
    sharing_in_config: config.SharingInViewConfig,
    sharing_out_config: config.SharingOutViewConfig,
    upload_menu_config: config.UploadMenuConfig,
    pause_owncloud: Transition,
    # states
    selecting_menu: str = "selecting_menu",
    all_files: str = "all_files",
    favorites: str = "favorites",
    sharing_in: str = "sharing_in",
    sharing_out: str = "sharing_out",
    file_details: str = "file_details",
    upload_menu: str = "upload_menu",
    # nav transitions
    do_nothing: str = "do_nothing",
    nav_all_files: str = "nav_all_files",
    nav_favorites: str = "nav_favorites",
    nav_sharing_in: str = "nav_sharing_in",
    nav_sharing_out: str = "nav_sharing_out",
    # file transitions
    scroll_down: str = "scroll_down",
    favorite: str = "favorite",
    remove_favorite: str = "remove_favorite",
    open_directory: str = "open_directory",
    nav_root: str = "nav_root",
    download_file: str = "download_file",
    delete_file: str = "delete_file",
    upload_file: str = "upload_file",
    download_directory: str = "download_directory",
    delete_directory: str = "delete_directory",
    create_directory: str = "create_directory",
    view_details: str = "view_details",
    # transitions sharing in
    accept_share: str = "accept_share",
    decline_share: str = "decline_share",
    # transitions upload menu
    keep_new: str = "keep_new",
    keep_both: str = "keep_both",
    keep_old: str = "keep_old",
    new_file: str = "new_file",
    name_prefix: Optional[str] = None,
) -> Tuple[
    states.SelectingMenu,
    states.AllFilesView,
    states.FavoritesView,
    states.SharingInView,
    states.SharingOutView,
    states.UploadMenu,
]:
    """Creates the owncloud user file activity

    i.e., navigating the main menu and performing actions on
    the various file views.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The activities states as tuple of the form:
        (
            selecting_menu,
            all_files,
            favorites,
            sharing_in,
            sharing_out,
            upload_menu,
        )
    """
    if name_prefix:
        target_selecting_menu = f"{name_prefix}_{selecting_menu}"
        target_all_files = f"{name_prefix}_{all_files}"
        target_favorites = f"{name_prefix}_{favorites}"
        target_sharing_in = f"{name_prefix}_{sharing_in}"
        target_sharing_out = f"{name_prefix}_{sharing_out}"
        target_file_details = f"{name_prefix}_{file_details}"
        target_upload_menu = f"{name_prefix}_{upload_menu}"
    else:
        target_selecting_menu = selecting_menu
        target_all_files = all_files
        target_favorites = favorites
        target_sharing_in = sharing_in
        target_sharing_out = sharing_out
        target_file_details = file_details
        target_upload_menu = upload_menu

    # nav transitions

    t_do_nothing = DelayedTransition(
        noop,
        name=do_nothing,
        target=target_selecting_menu,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_nav_all_files = DelayedTransition(
        nav.nav_all_files,
        name=nav_all_files,
        target=target_all_files,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_nav_favorites = DelayedTransition(
        nav.nav_favorites,
        name=nav_favorites,
        target=target_favorites,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_nav_sharing_in = DelayedTransition(
        nav.nav_sharing_in,
        name=nav_sharing_in,
        target=target_sharing_in,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_nav_sharing_out = DelayedTransition(
        nav.nav_sharing_out,
        name=nav_sharing_out,
        target=target_sharing_out,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    # all files transitions

    t_files_scroll_down = DelayedTransition(
        actions.Scroll(),
        name=scroll_down,
        target=target_all_files,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_files_favorite = DelayedTransition(
        actions.favorite,
        name=favorite,
        target=target_all_files,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_files_remove_favorite = DelayedTransition(
        actions.unfavorite,
        name=remove_favorite,
        target=target_all_files,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_files_nav_root = DelayedTransition(
        nav.nav_root_dir,
        name=nav_root,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_files_download_file = DelayedTransition(
        actions.DownloadFile(download_config.path),
        name=download_file,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_files_delete_file = DelayedTransition(
        actions.delete_file,
        name=delete_file,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_files_upload_file = DelayedTransition(
        actions.UploadFile(owncloud.upload_files),
        name=upload_file,
        target=target_upload_menu,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_files_download_directory = DelayedTransition(
        actions.DownloadDir(download_config.path),
        name=download_directory,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_files_delete_directory = DelayedTransition(
        actions.delete_directory,
        name=delete_directory,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_files_create_directory = DelayedTransition(
        actions.create_directory,
        name=create_directory,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # favorites transitions

    t_fav_scroll_down = DelayedTransition(
        actions.Scroll(),
        name=scroll_down,
        target=target_favorites,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_fav_favorite = DelayedTransition(
        actions.favorite,
        name=favorite,
        target=target_favorites,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_fav_remove_favorite = DelayedTransition(
        actions.unfavorite,
        name=remove_favorite,
        target=target_favorites,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_fav_download_file = DelayedTransition(
        actions.DownloadFile(download_config.path),
        name=download_file,
        target=target_favorites,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_fav_delete_file = DelayedTransition(
        actions.delete_file,
        name=delete_file,
        target=target_favorites,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_fav_download_directory = DelayedTransition(
        actions.DownloadDir(download_config.path),
        name=download_directory,
        target=target_favorites,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_fav_delete_directory = DelayedTransition(
        actions.delete_directory,
        name=delete_directory,
        target=target_favorites,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # sharing in transitions

    t_in_scroll_down = DelayedTransition(
        actions.Scroll(),
        name=scroll_down,
        target=target_sharing_in,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_in_accept_share = DelayedTransition(
        actions.accept_share,
        name=accept_share,
        target=target_sharing_in,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_in_decline_share = DelayedTransition(
        actions.decline_share,
        name=decline_share,
        target=target_sharing_in,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # sharing out transitions

    t_out_scroll_down = DelayedTransition(
        actions.Scroll(),
        name=scroll_down,
        target=target_sharing_out,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_out_favorite = DelayedTransition(
        actions.favorite,
        name=favorite,
        target=target_sharing_out,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_out_remove_favorite = DelayedTransition(
        actions.unfavorite,
        name=remove_favorite,
        target=target_sharing_out,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_out_download_file = DelayedTransition(
        actions.DownloadFile(download_config.path),
        name=download_file,
        target=target_sharing_out,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_out_delete_file = DelayedTransition(
        actions.delete_file,
        name=delete_file,
        target=target_sharing_out,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_out_download_directory = DelayedTransition(
        actions.DownloadDir(download_config.path),
        name=download_directory,
        target=target_sharing_out,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_out_delete_directory = DelayedTransition(
        actions.delete_directory,
        name=delete_directory,
        target=target_sharing_out,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # shared file view transitions

    t_open_directory = DelayedTransition(
        actions.open_directory,
        name=open_directory,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_view_details = DelayedTransition(
        actions.show_details,
        name=view_details,
        target=target_file_details,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # upload menu transitions

    t_keep_old = DelayedTransition(
        actions.upload_keep_old,
        name=keep_old,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_keep_both = DelayedTransition(
        actions.upload_keep_both,
        name=keep_both,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_keep_new = DelayedTransition(
        actions.upload_keep_new,
        name=keep_new,
        target=target_all_files,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # states

    s_selecting_menu = states.SelectingMenu(
        selecting_menu,
        nav_all=t_nav_all_files,
        nav_favorites=t_nav_favorites,
        nav_sharing_in=t_nav_sharing_in,
        nav_sharing_out=t_nav_sharing_out,
        ret_transition=pause_owncloud,
        nav_all_weight=menu_config.nav_all,
        nav_favorites_weight=menu_config.nav_favorites,
        nav_sharing_in_weight=menu_config.nav_sharing_in,
        nav_sharing_out_weight=menu_config.nav_sharing_out,
        ret_weight=menu_config.return_,
        ret_increase=menu_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_all_files = states.AllFilesView(
        all_files,
        scroll_down=t_files_scroll_down,
        favorite=t_files_favorite,
        remove_favorite=t_files_remove_favorite,
        open_directory=t_open_directory,
        nav_root=t_files_nav_root,
        download_file=t_files_download_file,
        delete_file=t_files_delete_file,
        upload_file=t_files_upload_file,
        download_directory=t_files_download_directory,
        delete_directory=t_files_delete_directory,
        create_directory=t_files_create_directory,
        view_details=t_view_details,
        ret_transition=t_do_nothing,
        scroll_down_weight=all_files_config.scroll_down,
        favorite_weight=all_files_config.favorite,
        remove_favorite_weight=all_files_config.remove_favorite,
        open_directory_weight=all_files_config.open_directory,
        nav_root_weight=all_files_config.nav_root,
        download_file_weight=all_files_config.download_file,
        delete_file_weight=all_files_config.delete_file,
        upload_file_weight=all_files_config.upload_file,
        download_directory_weight=all_files_config.download_directory,
        delete_directory_weight=all_files_config.delete_directory,
        create_directory_weight=all_files_config.create_directory,
        view_details_weight=all_files_config.view_details,
        ret_weight=all_files_config.return_,
        ret_increase=all_files_config.extra.return_increase,
        upload_files=owncloud.upload_files,
        modify_directories=owncloud.modify_directories,
        max_directory_create_depth=owncloud.max_directory_create_depth,
        max_directory_count=owncloud.max_directory_count,
        favor_weight_factor=owncloud.favor_factor,
        min_scroll_space=owncloud.min_scroll_space,
        name_prefix=name_prefix,
    )

    s_favorites = states.FavoritesView(
        favorites,
        scroll_down=t_fav_scroll_down,
        favorite=t_fav_favorite,
        remove_favorite=t_fav_remove_favorite,
        open_directory=t_open_directory,
        download_file=t_fav_download_file,
        delete_file=t_fav_delete_file,
        download_directory=t_fav_download_directory,
        delete_directory=t_fav_delete_directory,
        view_details=t_view_details,
        ret_transition=t_do_nothing,
        scroll_down_weight=favorites_config.scroll_down,
        favorite_weight=favorites_config.favorite,
        remove_favorite_weight=favorites_config.remove_favorite,
        open_directory_weight=favorites_config.open_directory,
        download_file_weight=favorites_config.download_file,
        delete_file_weight=favorites_config.delete_file,
        download_directory_weight=favorites_config.download_directory,
        delete_directory_weight=favorites_config.delete_directory,
        view_details_weight=favorites_config.view_details,
        ret_weight=favorites_config.return_,
        ret_increase=favorites_config.extra.return_increase,
        modify_directories=owncloud.modify_directories,
        favor_weight_factor=owncloud.favor_factor,
        min_scroll_space=owncloud.min_scroll_space,
        name_prefix=name_prefix,
    )

    s_sharing_in = states.SharingInView(
        sharing_in,
        scroll_down=t_in_scroll_down,
        accept=t_in_accept_share,
        decline=t_in_decline_share,
        ret_transition=t_do_nothing,
        scroll_down_weight=sharing_in_config.scroll_down,
        accept_weight=sharing_in_config.accept,
        decline_weight=sharing_in_config.decline,
        ret_weight=sharing_in_config.return_,
        ret_increase=sharing_in_config.extra.return_increase,
        min_scroll_space=owncloud.min_scroll_space,
        name_prefix=name_prefix,
    )

    s_sharing_out = states.SharingOutView(
        sharing_out,
        scroll_down=t_out_scroll_down,
        favorite=t_out_favorite,
        remove_favorite=t_out_remove_favorite,
        open_directory=t_open_directory,
        download_file=t_out_download_file,
        delete_file=t_out_delete_file,
        download_directory=t_out_download_directory,
        delete_directory=t_out_delete_directory,
        view_details=t_view_details,
        ret_transition=t_do_nothing,
        scroll_down_weight=sharing_out_config.scroll_down,
        favorite_weight=sharing_out_config.favorite,
        remove_favorite_weight=sharing_out_config.remove_favorite,
        open_directory_weight=sharing_out_config.open_directory,
        download_file_weight=sharing_out_config.download_file,
        delete_file_weight=sharing_out_config.delete_file,
        download_directory_weight=sharing_out_config.download_directory,
        delete_directory_weight=sharing_out_config.delete_directory,
        view_details_weight=sharing_out_config.view_details,
        ret_weight=sharing_out_config.return_,
        ret_increase=sharing_out_config.extra.return_increase,
        modify_directories=owncloud.modify_directories,
        favor_weight_factor=owncloud.favor_factor,
        min_scroll_space=owncloud.min_scroll_space,
        name_prefix=name_prefix,
    )

    s_upload_menu = states.UploadMenu(
        upload_menu,
        keep_new=t_keep_new,
        keep_both=t_keep_both,
        keep_old=t_keep_old,
        keep_new_weight=upload_menu_config.keep_new,
        keep_both_weight=upload_menu_config.keep_both,
        keep_old_weight=upload_menu_config.keep_old,
        new_file=new_file,
        name_prefix=name_prefix,
    )

    return (
        s_selecting_menu,
        s_all_files,
        s_favorites,
        s_sharing_in,
        s_sharing_out,
        s_upload_menu,
    )


def get_file_details_activity(
    idle: IdleConfig,
    details_config: config.FileDetailsViewConfig,
    sharing_config: config.SharingDetailsConfig,
    # states
    selecting_menu: str = "selecting_menu",
    all_files: str = "all_files",
    favorites: str = "favorites",
    sharing_out: str = "sharing_out",
    file_details: str = "file_details",
    sharing_details: str = "sharing_details",
    close_check: str = "details_close_check",
    # transitions
    do_nothing: str = "do_nothing",
    view_comments: str = "view_comments",
    view_sharing: str = "view_sharing",
    view_versions: str = "view_versions",
    share_file: str = "share_file",
    unshare_file: str = "unshare_file",
    close: str = "close_details",
    close_check_prefix: str = "on",
    name_prefix: Optional[str] = None,
) -> Tuple[states.FileDetailsView, states.SharingDetails, states.CloseCheckState]:
    """Creates the owncloud user file details activity

    i.e., navigating the details tabs and sharing/unsharing files

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The activities states as tuple of the form:
        (
            file_details,
            sharing_details,
            close_check,
        )
    """

    if name_prefix:
        target_selecting_menu = f"{name_prefix}_{selecting_menu}"
        target_all_files = f"{name_prefix}_{all_files}"
        target_favorites = f"{name_prefix}_{favorites}"
        target_sharing_out = f"{name_prefix}_{sharing_out}"
        target_file_details = f"{name_prefix}_{file_details}"
        target_sharing_details = f"{name_prefix}_{sharing_details}"
        target_close_check = f"{name_prefix}_{close_check}"
    else:
        target_selecting_menu = selecting_menu
        target_all_files = all_files
        target_favorites = favorites
        target_sharing_out = sharing_out
        target_file_details = file_details
        target_sharing_details = sharing_details
        target_close_check = close_check

    # file details transitions

    t_view_comments = DelayedTransition(
        actions.open_details_comments,
        name=view_comments,
        target=target_file_details,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_view_sharing = DelayedTransition(
        actions.open_details_share,
        name=view_sharing,
        target=target_sharing_details,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_view_versions = DelayedTransition(
        actions.open_details_versions,
        name=view_versions,
        target=target_file_details,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_close = DelayedTransition(
        actions.close_details,
        name=close,
        target=target_close_check,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # sharing details transitions

    t_share_file = DelayedTransition(
        actions.ShareFile(sharing_config.extra.share_users),
        name=share_file,
        target=target_sharing_details,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_unshare_file = DelayedTransition(
        actions.unshare_file,
        name=unshare_file,
        target=target_sharing_details,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_do_nothing = DelayedTransition(
        noop,
        name=do_nothing,
        target=target_file_details,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # states

    s_file_details = states.FileDetailsView(
        file_details,
        view_comments=t_view_comments,
        view_sharing=t_view_sharing,
        view_versions=t_view_versions,
        close=t_close,
        view_comments_weight=details_config.view_comments,
        view_sharing_weight=details_config.view_sharing,
        view_versions_weight=details_config.view_versions,
        close_weight=details_config.return_,
        close_increase=details_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_sharing_details = states.SharingDetails(
        sharing_details,
        share=t_share_file,
        unshare=t_unshare_file,
        ret_transition=t_do_nothing,
        share_weight=sharing_config.share,
        unshare_weight=sharing_config.unshare,
        ret_weight=sharing_config.return_,
        ret_increase=sharing_config.extra.return_increase,
        share_users=sharing_config.extra.share_users,
        max_shares=sharing_config.extra.max_shares,
        name_prefix=name_prefix,
    )

    s_close_check = states.CloseCheckState(
        close_check,
        all_files=target_all_files,
        favorites=target_favorites,
        sharing_out=target_sharing_out,
        fallback=target_selecting_menu,
        transition_prefix=close_check_prefix,
        name_prefix=name_prefix,
    )

    return (s_file_details, s_sharing_details, s_close_check)
