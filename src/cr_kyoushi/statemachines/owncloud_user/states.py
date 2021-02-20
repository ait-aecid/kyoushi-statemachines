import re

from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
    Pattern,
)

from selenium.common.exceptions import NoSuchElementException
from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation import states
from cr_kyoushi.simulation.transitions import (
    NoopTransition,
    Transition,
)
from cr_kyoushi.simulation.util import now

from ..core.states import ActivityState
from .context import Context
from .gather import (
    OwncloudPermissions,
    get_app_content_scroll_space,
    get_current_content_id,
    get_current_directory,
    get_data,
    get_dirs,
    get_favored_files,
    get_file_info,
    get_files,
    get_sharable_users,
    get_share_pending,
    get_shared_users,
    get_unfavored_files,
    is_permissions,
)
from .wait import (
    check_file_details_comments_available,
    check_file_details_share_available,
    check_file_details_versions_available,
    check_file_exists_dialog,
    check_file_sharable,
    check_login_page,
    check_new_button,
)


class ActivitySelectionState(states.AdaptiveProbabilisticState):
    """The main activity selection state for the owncloud user.

    This will decide between either entering the owncloud activity or idling.
    """

    def __init__(
        self,
        name: str,
        owncloud_transition: Transition,
        idle_transition: Transition,
        owncloud_max_daily: int = 10,
        owncloud_weight: float = 0.6,
        idle_weight: float = 0.4,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            owncloud_transition: The transition to enter the owncloud activity
            idle_transition: The idle transition
            owncloud_max_daily: The maximum amount of times to enter the owncloud activity per day.
            owncloud_weight: The propability of entering the owncloud activity.
            idle_weight: The propability of entering the idle activity.
        """
        super().__init__(
            name=name,
            transitions=[owncloud_transition, idle_transition],
            weights=[owncloud_weight, idle_weight],
            name_prefix=name_prefix,
        )
        self.__owncloud = owncloud_transition
        self.__owncloud_count = 0
        self.__owncloud_max = owncloud_max_daily
        self.__day = now().date()

    def adapt_before(self, log, context):
        """Sets the propability of entering the owncloud activity to 0 if the daylie maximum is reached"""
        super().adapt_before(log, context)

        # reset owncloud count and modifiers if we have a new day
        current_day = now().date()
        if self.__day != current_day:
            self.__day = current_day
            self.__owncloud_count = 0
            self.reset()

        # if we reached the owncloud limit set the transition probability to 0
        if self.__owncloud_count >= self.__owncloud_max:
            self._modifiers[self.__owncloud] = 0

    def adapt_after(self, log, context, selected):
        """Increases the owncloud activity enter count"""
        super().adapt_after(log, context, selected)

        # increase owncloud count if we selected the transition
        if selected == self.__owncloud:
            self.__owncloud_count += 1


class LoggedInCheck(states.ChoiceState):
    """Dummy state used to detect if the user is already logged in or not."""

    def __init__(
        self,
        name: str,
        login_state: str,
        selecting_menu_state: str,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name,
            self.check_logged_in,
            yes=NoopTransition(
                name="logged_in_yes",
                target=selecting_menu_state,
                name_prefix=name_prefix,
            ),
            no=NoopTransition(
                name="logged_in_no",
                target=login_state,
                name_prefix=name_prefix,
            ),
            name_prefix=name_prefix,
        )

    def check_logged_in(self, log: BoundLogger, context: Context) -> bool:
        if check_login_page(context.driver):
            return False
        return True


class LoginPage(states.AdaptiveProbabilisticState):
    """The owncloud login page state"""

    def __init__(
        self,
        name: str,
        login: Transition,
        fail_login: Transition,
        fail_weight: float = 0.05,
        fail_decrease_factor: float = 0.9,
        name_prefix: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            transitions=[login, fail_login],
            weights=[1 - fail_weight, fail_weight],
            name_prefix=name_prefix,
        )
        self.__fail = fail_login
        self.__fail_decrease = fail_decrease_factor

    def adapt_after(self, log, context, selected):
        """Reduces the chance of a failing login after each fail"""
        super().adapt_after(log, context, selected)

        if selected == self.__fail:
            self._modifiers[self.__fail] *= self.__fail_decrease
        else:
            self.reset()


class SelectingMenu(ActivityState):
    """The owncloud selecting menu state.

    This is the main state used to switch between the various owncloud
    sub activities.
    """

    def __init__(
        self,
        name: str,
        nav_all: Transition,
        nav_favorites: Transition,
        nav_sharing_in: Transition,
        nav_sharing_out: Transition,
        ret_transition: Transition,
        nav_all_weight: float = 0.25,
        nav_favorites_weight: float = 0.2,
        nav_sharing_in_weight: float = 0.25,
        nav_sharing_out_weight: float = 0.2,
        ret_weight: float = 0.1,
        ret_increase=1.25,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            nav_all: The nav_all transition
            nav_favorites: The nav_favorites transition
            nav_sharing_in: The nav_sharing_in transition
            nav_sharing_out: The nav_sharing_out transition
            ret_transition: The return to parent activity transition
            nav_all_weight: The base weight for the   nav_all transition
            nav_favorites_weight: The base weight for the  nav_favorites transition
            nav_sharing_in_weight: The base weight for the  nav_sharing_in transition
            nav_sharing_out_weight: The base weight for the nav_sharing_out transition
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
        """
        super().__init__(
            name,
            [
                nav_all,
                nav_favorites,
                nav_sharing_in,
                nav_sharing_out,
                ret_transition,
            ],
            ret_transition,
            [
                nav_all_weight,
                nav_favorites_weight,
                nav_sharing_in_weight,
                nav_sharing_out_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )


class LogoutChoice(states.ProbabilisticState):
    """The owncloud logout choice state

    Used as a decision state to decide wether the user should logout
    of owncloud or simply leave it open in background when pausing the activity.
    """

    def __init__(
        self,
        name: str,
        logout: Transition,
        logout_prob: float = 0.05,
        background: str = "background_owncloud",
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name assigned to the state
            logout: The logout transition
            logout_prob: The chance the user will logout
            background: The name to assign to the background owncloud transition
        """
        super().__init__(
            name,
            [
                logout,
                # if we do not log out we do nothing
                NoopTransition(
                    name=background,
                    target=logout.target,
                    name_prefix=name_prefix,
                ),
            ],
            [logout_prob, 1 - logout_prob],
            name_prefix=name_prefix,
        )


def _update_scroll_down(
    context: Context,
    modifiers: Dict[Transition, float],
    scroll_down: Transition,
    min_scroll_space: float,
):
    """Enables/disables the scroll down action depending on the remaining scrollability of a page.

    Args:
        context: The sm context
    """
    space = get_app_content_scroll_space(context.driver)
    # disable scrolling if remaining scroll space < min space
    modifiers[scroll_down] = 0 if space < min_scroll_space else 1


def _update_favorite_actions(
    context: Context,
    modifiers: Dict[Transition, float],
    favorite: Transition,
    remove_favorite: Transition,
    favor_factor: float,
):
    """Modifies the favorite and remove_favorite modifiers.

    If all data elements are either favored or unfavored then
    the respective transition is disabled.

    Otherwise the modifier is a based on the number of
    favored/unfavored elements. i.e., with each favored/unfavored
    element the chance of favorite/remove_favorite is decreased.

    Args:
        context: The sm context.
    """
    favored_count = len(get_favored_files(context.driver))
    unfavored_count = len(get_unfavored_files(context.driver))

    modifiers[favorite] = 0 if unfavored_count == 0 else favor_factor ** favored_count

    modifiers[remove_favorite] = (
        0 if favored_count == 0 else favor_factor ** unfavored_count
    )


def _update_read_actions(
    context: Context,
    modifiers: Dict[Transition, float],
    view_details: Transition,
    download_file: Transition,
    download_directory: Transition,
    open_directory: Transition,
):
    """Disables/enables file/dir operations.

    Checks for the presence of files and directories and their permissions and
    disables/enables view, download and delete actions accordingly.

    Args:
        context: The sm context
    """
    data = get_data(context.driver)
    data_infos = [get_file_info(d) for d in data]

    if len(data) > 0:
        # need at least 1 data object to view details
        modifiers[view_details] = 1
    else:
        modifiers[view_details] = 0

    # check if we have any directories we can read
    if any(
        d
        for d in data_infos
        if d.file_type == "dir"
        and is_permissions(OwncloudPermissions.READ, d.permissions)
    ):
        modifiers[download_directory] = 1
        modifiers[open_directory] = 1
    else:
        modifiers[download_directory] = 0
        modifiers[open_directory] = 0

    # check if we have any files we can read
    if any(
        d
        for d in data_infos
        if d.file_type != "dir"
        and is_permissions(OwncloudPermissions.READ, d.permissions)
    ):
        modifiers[download_file] = 1
    else:
        modifiers[download_file] = 0


def _update_delete_actions(
    context: Context,
    modifiers: Dict[Transition, float],
    delete_file: Transition,
    delete_directory: Transition,
    modify_dirs: List[re.Pattern],
):
    """Disables/enables file/dir operations.

    Checks for the presence of files and directories and their permissions and
    disables/enables view, download and delete actions accordingly.

    Args:
        context: The sm context
    """

    if any(
        tr
        # check if we have any dirs we can delete
        for tr in get_dirs(context.driver, OwncloudPermissions.DELETE)
        # that are also in a modifiable directory
        # (views other than All Files might show files from various directories)
        if any(regex.match(tr.get_attribute("data-path")) for regex in modify_dirs)
    ):
        modifiers[delete_directory] = 1
    else:
        modifiers[delete_directory] = 0

    if any(
        tr
        # check if we have any files we can delete
        for tr in get_files(context.driver, OwncloudPermissions.DELETE)
        # that are also in a modifiable directory
        # (views other than All Files might show files from various directories)
        if any(regex.match(tr.get_attribute("data-path")) for regex in modify_dirs)
    ):
        modifiers[delete_file] = 1
    else:
        modifiers[delete_file] = 0


class AllFilesView(ActivityState):
    """The state controling the transitions when the user is on the all files view"""

    def __init__(
        self,
        name: str,
        scroll_down: Transition,
        favorite: Transition,
        remove_favorite: Transition,
        open_directory: Transition,
        nav_root: Transition,
        download_file: Transition,
        delete_file: Transition,
        upload_file: Transition,
        download_directory: Transition,
        delete_directory: Transition,
        create_directory: Transition,
        view_details: Transition,
        ret_transition: Transition,
        scroll_down_weight: float = 0.1,
        favorite_weight: float = 0.05,
        remove_favorite_weight: float = 0.05,
        open_directory_weight: float = 0.1,
        nav_root_weight: float = 0.075,
        download_file_weight: float = 0.1,
        delete_file_weight: float = 0.075,
        upload_file_weight: float = 0.075,
        download_directory_weight: float = 0.05,
        delete_directory_weight: float = 0.05,
        create_directory_weight: float = 0.075,
        view_details_weight: float = 0.125,
        ret_weight: float = 0.075,
        ret_increase=1.2,
        upload_files: Dict[str, float] = {},
        modify_directories: List[Pattern] = [re.compile(r"\/.+")],
        max_directory_create_depth: Optional[int] = None,
        max_directory_count: Optional[int] = None,
        favor_weight_factor: float = 1.0,
        min_scroll_space: float = 200.0,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            scroll_down: The transition used to scroll on the file view, causing more data to be loaded.
            favorite: Transition that marks a file or directory as favorite
            remove_favorite: Transition that un marks a file or directory as favorite
            nav_root: Transition that navigates to the root directory
            download_file: Transition that downloads a file
            delete_file: Transition that deletes a file
            upload_file: Transition that uploads a new file to the current directory
            download_directory: Transition that downloads a currently visible sub directory
            delete_directory: Transition that deletes a directory.
            create_directory: Transition that creates a new sub directory.
            open_directory: Transition that opens a directory
            view_details: Transition that views an existing files details
            ret_transition: The return to parent activity transition
            scroll_down_weight: The base weight of the scroll_down transition
            favorite_weight: The base weight of the favorite transition
            remove_favorite_weight: The base weight of the remove_favorite transition
            nav_root_weight: The base weight of the nav_root transition
            download_file_weight: The base weight of the download_file transition
            delete_file_weight: The base weight of the delete_file transition
            upload_file_weight: The base weight of the upload_file transition
            download_directory_weight: The base weight of the download_directory transition
            delete_directory_weight: The base weight of the delete_directory transition
            create_directory_weight: The base weight of the create_directory transition
            open_directory_weight: The base weight of the open_directory transition
            view_details_weight: The base weight of the view_details transition
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
            upload_files: Dictionary of files the user can upload
            modify_directories: List of path regular expressions for directories that the user can modify.
                                Note that the user still needs the actual permissions to do so.
            max_directory_create_depth: The maximum directory level to create sub directories in.
            max_directory_count: The maximum sub directories to create.
            favor_weight_factor: Used to decrease chance of favorite/remove_favorite depending
                                 on the amount of files/dirs already favored/not favored.
                                 Must be <= 1, >= 0
            min_scroll_space: The minium scroll space in pixels needed for the user to consider scrolling down.
        """
        super().__init__(
            name,
            [
                scroll_down,
                favorite,
                remove_favorite,
                open_directory,
                nav_root,
                download_file,
                delete_file,
                upload_file,
                download_directory,
                delete_directory,
                create_directory,
                view_details,
                ret_transition,
            ],
            ret_transition,
            [
                scroll_down_weight,
                favorite_weight,
                remove_favorite_weight,
                open_directory_weight,
                nav_root_weight,
                download_file_weight,
                delete_file_weight,
                upload_file_weight,
                download_directory_weight,
                delete_directory_weight,
                create_directory_weight,
                view_details_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self.upload_files: Dict[str, float] = upload_files
        self.modify_dir: List[Pattern] = modify_directories
        self.max_create_dir: Optional[int] = max_directory_create_depth
        self.max_dir: Optional[int] = max_directory_count
        self.favor_factor: float = favor_weight_factor
        self.min_scroll_space: float = min_scroll_space

        self._scroll_down: Transition = scroll_down
        self._favorite: Transition = favorite
        self._remove_favorite: Transition = remove_favorite
        self._open_directory: Transition = open_directory
        self._nav_root: Transition = nav_root
        self._download_file: Transition = download_file
        self._delete_file: Transition = delete_file
        self._upload_file: Transition = upload_file
        self._download_directory: Transition = download_directory
        self._delete_directory: Transition = delete_directory
        self._create_directory: Transition = create_directory
        self._view_details: Transition = view_details

    def _update_nav_root(self, context: Context):
        """Disables the root dir nav if we are already on the root dir.

        Args:
            context: The sm context
        """
        current_dir = get_current_directory(context.driver)
        # if we are already on the root dir disable the nav option
        self._modifiers[self._nav_root] = 0 if current_dir == "/" else 1

    def _update_create_actions(self, context: Context):
        """Disables/enables file upload and directory create.

        Checks wether create actions are possible and
        also checks wether the current directory limits (max depth and count)
        are reached.

        Args:
            context: The sm context
        """
        current_dir = get_current_directory(context.driver)

        if (
            # check that the new button is available
            # i.e., we have owncloud permissions to create
            check_new_button(context.driver)
            # and that the user is configured to modify the current dir
            and any(regex.match(current_dir) for regex in self.modify_dir)
        ):
            # activate upload file if we have files to upload
            self._modifiers[self._upload_file] = 1 if len(self.upload_files) > 0 else 0

            current_depth = len(Path(get_current_directory(context.driver)).parts)
            dir_count = len(get_dirs(context.driver))
            if (
                # check that current dir has less sub dirs than max
                (self.max_dir is None or dir_count < self.max_dir)
                # and current dir is at most max depth
                and (
                    self.max_create_dir is None or current_depth <= self.max_create_dir
                )
            ):
                self._modifiers[self._create_directory] = 1
            else:
                self._modifiers[self._create_directory] = 0
        else:
            self._modifiers[self._upload_file] = 0
            self._modifiers[self._create_directory] = 0

    def adapt_before(self, log: BoundLogger, context: Context):
        super().adapt_before(log, context)

        _update_scroll_down(
            context,
            self._modifiers,
            self._scroll_down,
            self.min_scroll_space,
        )

        _update_favorite_actions(
            context,
            self._modifiers,
            self._favorite,
            self._remove_favorite,
            self.favor_factor,
        )

        _update_read_actions(
            context,
            self._modifiers,
            self._view_details,
            self._download_file,
            self._download_directory,
            self._open_directory,
        )

        _update_delete_actions(
            context,
            self._modifiers,
            self._delete_file,
            self._delete_directory,
            self.modify_dir,
        )

        self._update_nav_root(context)
        self._update_create_actions(context)

        log.debug(
            "Modifiers before",
            modifiers={t.name: m for t, m in self._modifiers.items()},
        )


class FilesView(ActivityState):
    """The state controling the transitions when the user is on a normal files view

    e.g., favorites,  sharing_out
    """

    def __init__(
        self,
        name: str,
        scroll_down: Transition,
        favorite: Transition,
        remove_favorite: Transition,
        open_directory: Transition,
        download_file: Transition,
        delete_file: Transition,
        download_directory: Transition,
        delete_directory: Transition,
        view_details: Transition,
        ret_transition: Transition,
        scroll_down_weight: float = 0.15,
        favorite_weight: float = 0.05,
        remove_favorite_weight: float = 0.05,
        open_directory_weight: float = 0.2,
        download_file_weight: float = 0.1,
        delete_file_weight: float = 0.1,
        download_directory_weight: float = 0.05,
        delete_directory_weight: float = 0.05,
        view_details_weight: float = 0.15,
        ret_weight: float = 0.1,
        ret_increase=1.2,
        modify_directories: List[Pattern] = [re.compile(r"\/.+")],
        favor_weight_factor: float = 1.0,
        min_scroll_space: float = 200.0,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            scroll_down: The transition used to scroll on the file view, causing more data to be loaded.
            favorite: Transition that marks a file or directory as favorite
            remove_favorite: Transition that un marks a file or directory as favorite
            nav_root: Transition that navigates to the root directory
            download_file: Transition that downloads a file
            delete_file: Transition that deletes a file
            upload_file: Transition that uploads a new file to the current directory
            download_directory: Transition that downloads a currently visible sub directory
            delete_directory: Transition that deletes a directory.
            create_directory: Transition that creates a new sub directory.
            open_directory: Transition that opens a directory
            view_details: Transition that views an existing files details
            ret_transition: The return to parent activity transition
            scroll_down_weight: The base weight of the scroll_down transition
            favorite_weight: The base weight of the favorite transition
            remove_favorite_weight: The base weight of the remove_favorite transition
            nav_root_weight: The base weight of the nav_root transition
            download_file_weight: The base weight of the download_file transition
            delete_file_weight: The base weight of the delete_file transition
            upload_file_weight: The base weight of the upload_file transition
            download_directory_weight: The base weight of the download_directory transition
            delete_directory_weight: The base weight of the delete_directory transition
            create_directory_weight: The base weight of the create_directory transition
            open_directory_weight: The base weight of the open_directory transition
            view_details_weight: The base weight of the view_details transition
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
            modify_directories: List of path regular expressions for directories that the user can modify.
                                Note that the user still needs the actual permissions to do so.
            favor_weight_factor: Used to decrease chance of favorite/remove_favorite depending
                                 on the amount of files/dirs already favored/not favored.
                                 Must be <= 1, >= 0
            min_scroll_space: The minium scroll space in pixels needed for the user to consider scrolling down.
        """
        super().__init__(
            name,
            [
                scroll_down,
                favorite,
                remove_favorite,
                open_directory,
                download_file,
                delete_file,
                download_directory,
                delete_directory,
                view_details,
                ret_transition,
            ],
            ret_transition,
            [
                scroll_down_weight,
                favorite_weight,
                remove_favorite_weight,
                open_directory_weight,
                download_file_weight,
                delete_file_weight,
                download_directory_weight,
                delete_directory_weight,
                view_details_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self.modify_dir: List[Pattern] = modify_directories
        self.favor_factor: float = favor_weight_factor
        self.min_scroll_space: float = min_scroll_space

        self._scroll_down: Transition = scroll_down
        self._favorite: Transition = favorite
        self._remove_favorite: Transition = remove_favorite
        self._open_directory: Transition = open_directory
        self._download_file: Transition = download_file
        self._delete_file: Transition = delete_file
        self._download_directory: Transition = download_directory
        self._delete_directory: Transition = delete_directory
        self._view_details: Transition = view_details

    def adapt_before(self, log: BoundLogger, context: Context):
        super().adapt_before(log, context)

        _update_scroll_down(
            context,
            self._modifiers,
            self._scroll_down,
            self.min_scroll_space,
        )

        _update_favorite_actions(
            context,
            self._modifiers,
            self._favorite,
            self._remove_favorite,
            self.favor_factor,
        )

        _update_read_actions(
            context,
            self._modifiers,
            self._view_details,
            self._download_file,
            self._download_directory,
            self._open_directory,
        )

        _update_delete_actions(
            context,
            self._modifiers,
            self._delete_file,
            self._delete_directory,
            self.modify_dir,
        )

        log.debug(
            "Modifiers before",
            modifiers={t.name: m for t, m in self._modifiers.items()},
        )


FavoritesView = FilesView

SharingOutView = FilesView


class SharingInView(ActivityState):
    """The state controling the transitions when the user  is on the sharing in view"""

    def __init__(
        self,
        name: str,
        scroll_down: Transition,
        accept: Transition,
        decline: Transition,
        ret_transition: Transition,
        scroll_down_weight: float = 0.15,
        accept_weight: float = 0.4,
        decline_weight: float = 0.35,
        ret_weight: float = 0.1,
        ret_increase=1.2,
        min_scroll_space: float = 200.0,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            scroll_down: The transition used to scroll on the file view, causing more data to be loaded.
            accept: Transition that accepts an incoming share
            decline: Transition that decline an incoming share
            ret_transition: The return to parent activity transition
            scroll_down_weight: The base weight of the scroll_down transition
            accept_weight: The base weight of the accept transition
            decline_weight: The base weight of the decline transition
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
            min_scroll_space: The minium scroll space in pixels needed for the user to consider scrolling down.
        """
        super().__init__(
            name,
            [
                scroll_down,
                accept,
                decline,
                ret_transition,
            ],
            ret_transition,
            [
                scroll_down_weight,
                accept_weight,
                decline_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self.min_scroll_space: float = min_scroll_space

        self._scroll_down: Transition = scroll_down
        self._accept: Transition = accept
        self._decline: Transition = decline

    def adapt_before(self, log: BoundLogger, context: Context):
        super().adapt_before(log, context)

        _update_scroll_down(
            context,
            self._modifiers,
            self._scroll_down,
            self.min_scroll_space,
        )

        # disables accept/decline if there are no pending shares
        if len(get_share_pending(context.driver)) > 0:
            self._modifiers[self._accept] = 1
            self._modifiers[self._decline] = 1
        else:
            self._modifiers[self._accept] = 0
            self._modifiers[self._decline] = 0
            # x4 scroll modifier incase pending shares are not loaded
            # if we are the bottom it will be 0*4 = 0
            self._modifiers[self._scroll_down] *= 4

        log.debug(
            "Modifiers before",
            modifiers={t.name: m for t, m in self._modifiers.items()},
        )


class FileDetailsView(ActivityState):
    """The state controling the transitions when the user is viewing the details of a file/dir"""

    def __init__(
        self,
        name: str,
        view_comments: Transition,
        view_sharing: Transition,
        view_versions: Transition,
        close: Transition,
        view_comments_weight: float = 0.25,
        view_sharing_weight: float = 0.4,
        view_versions_weight: float = 0.25,
        close_weight: float = 0.1,
        close_increase=1.2,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            view_comments: The transition used to open the comments tab
            view_sharing: The transition used to open the sharing tab
            view_versions: The transition used to open the versions tab
            close: The return to parent activity transition
            view_comments_weight: The base weight of the view_comments transition
            view_sharing_weight: The base weight of the view_sharing transition
            view_versions_weight: The base weight of the view_versions transition
            close_weight: The base weight of the return transition
            close_increase: The factor to increase the return transitions weight by
                          until it is selected.
        """
        super().__init__(
            name,
            [
                view_comments,
                view_sharing,
                view_versions,
                close,
            ],
            close,
            [
                view_comments_weight,
                view_sharing_weight,
                view_versions_weight,
                close_weight,
            ],
            modifiers=None,
            ret_increase=close_increase,
            name_prefix=name_prefix,
        )
        self._comments: Transition = view_comments
        self._sharing: Transition = view_sharing
        self._versions: Transition = view_versions

    def adapt_before(self, log: BoundLogger, context: Context):
        super().adapt_before(log, context)

        # disable/enable tabs depending on if they are available
        self._modifiers[self._comments] = (
            1 if check_file_details_comments_available(context.driver) else 0
        )
        self._modifiers[self._sharing] = (
            1 if check_file_details_share_available(context.driver) else 0
        )
        self._modifiers[self._versions] = (
            1 if check_file_details_versions_available(context.driver) else 0
        )


class SharingDetails(ActivityState):
    """The state controling the transitions when the user is on the sharing details tab"""

    def __init__(
        self,
        name: str,
        share: Transition,
        unshare: Transition,
        ret_transition: Transition,
        share_weight: float = 0.4,
        unshare_weight: float = 0.35,
        ret_weight: float = 0.25,
        ret_increase=1.2,
        share_users: Dict[str, float] = {},
        max_shares: Optional[int] = None,
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            share: The transition used to share the open file/dir with another user.
            unshare: The transition used to unshare the open file/dir for a user.
            ret_transition: The return to parent activity transition
            share_weight: The base weight of the share transition
            unshare_weight: The base weight of the unshare transition
            decline_weight: The base weight of the decline transition
            ret_weight: The base weight of the return transition
            ret_increase: The factor to increase the return transitions weight by
                          until it is selected.
            share_users: The dictionary of users the owncloud user can share files to.
            max_shares: The maximum number of users one file/dir can be shared to.
        """
        super().__init__(
            name,
            [
                share,
                unshare,
                ret_transition,
            ],
            ret_transition,
            [
                share_weight,
                unshare_weight,
                ret_weight,
            ],
            modifiers=None,
            ret_increase=ret_increase,
            name_prefix=name_prefix,
        )
        self._share: Transition = share
        self._unshare: Transition = unshare
        self.users: Dict[str, float] = share_users
        self.max_shares: Optional[int] = max_shares

    def adapt_before(self, log: BoundLogger, context: Context):
        super().adapt_before(log, context)

        # disable unsharing if the file/dir has not been shared yet
        self._modifiers[self._unshare] = (
            1 if len(get_shared_users(context.driver)) > 0 else 0
        )

        if (
            # enable sharing only if the file/dir is sharable
            check_file_sharable(context.driver)
            # and we have no users to share to
            and len(get_sharable_users(context.driver, self.users)) > 0
            # and we shared this file/dir to less than the maximum amount of users
            and (
                # if no max is defined then we can share
                # as long as there are users to share to
                self.max_shares is None
                or len(get_shared_users(context.driver)) < self.max_shares
            )
        ):
            self._modifiers[self._share] = 1
        else:
            self._modifiers[self._share] = 0


class CloseCheckState(states.State):
    """Pseudostate to set the correct view state after closing the details view."""

    def __init__(
        self,
        name,
        all_files: str,
        favorites: str,
        sharing_out: str,
        fallback: str = "selecting_menu",
        transition_prefix="on",
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The name that is assigned to the state
            all_files: Name of the all files view state
            favorites: Name of the favorites view state
            sharing_out: Name of the sharing out view state
            fallback: Name of the state to fallback into if none of the views is correct
            transition_prefix: String to prefix the dummy transitions with
        """

        # create noop transitions
        self.views: Dict[str, Transition] = {
            "app-content-files": NoopTransition(
                f"{transition_prefix}_{all_files}",
                all_files,
                name_prefix=name_prefix,
            ),
            "app-content-favorites": NoopTransition(
                f"{transition_prefix}_{favorites}",
                favorites,
                name_prefix=name_prefix,
            ),
            "app-content-sharingout": NoopTransition(
                f"{transition_prefix}_{sharing_out}",
                sharing_out,
                name_prefix=name_prefix,
            ),
        }
        self.fallback = NoopTransition(
            f"{transition_prefix}_unknown_view",
            fallback,
            name_prefix=name_prefix,
        )
        super().__init__(
            name,
            list(self.views.values()) + [self.fallback],
            name_prefix=name_prefix,
        )

    def next(self, log: BoundLogger, context: Context):
        """Returns the noop transition matching to the currently active view.

        If none of the views match a noop transition to the fallback state
        is returned.

        Args:
            log: The logger instance
            context: The sm context

        Returns:
            The selected transition
        """
        try:
            current_view = get_current_content_id(context.driver)
            return self.views.get(current_view, self.fallback)
        except NoSuchElementException:
            # we also return the fallback if we cannot
            # find the view id at all
            return self.fallback


class UploadMenu(states.ProbabilisticState):
    """The state controling the transitions when the user is on the sharing details tab"""

    def __init__(
        self,
        name: str,
        keep_new: Transition,
        keep_both: Transition,
        keep_old: Transition,
        keep_new_weight: float = 0.6,
        keep_both_weight: float = 0.3,
        keep_old_weight: float = 0.1,
        new_file: str = "new_file",
        name_prefix: Optional[str] = None,
    ):
        """
        Args:
            name: The states name
            keep_new: The transition used to keep the new file
            keep_both: The transition used to keep both the old and the new file
            keep_old: The transition use to keep the old file (cancles the upload)
            keep_new_weight: The base weight of the keep_new transition
            keep_both_weight: The base weight of the keep_both transition
            keep_old_weight: The base weight of the keep_old transition
            new_file: The name to use for the noop transition for a complitely new file.
                      The target will automatically read form the `keep_new` transition.
        """
        self.new_file: Transition = NoopTransition(
            new_file, keep_new.target, name_prefix=name_prefix
        )
        super().__init__(
            name,
            [
                self.new_file,
                keep_new,
                keep_both,
                keep_old,
            ],
            [
                0.0,
                keep_new_weight,
                keep_both_weight,
                keep_old_weight,
            ],
            name_prefix=name_prefix,
        )

    def next(self, log: BoundLogger, context: Context):
        """Only use propabilities if we are on upload menu"""
        if check_file_exists_dialog(context.driver):
            return super().next(log, context)
        return self.new_file
