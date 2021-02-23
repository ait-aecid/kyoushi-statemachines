"""
A collection of helper functions used to create the various sub activities of the Horde user activity.
"""

from typing import (
    Dict,
    Optional,
    Tuple,
    cast,
)

from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    NoopTransition,
    Transition,
    noop,
)

from ..core.config import IdleConfig
from . import (
    actions,
    config,
    nav,
    states,
)


__all__ = [
    "get_mail_activity",
    "get_preferences_activity",
    "get_admin_activity",
    "get_notes_activity",
    "get_tasks_activity",
    "get_address_book_activity",
    "get_calendar_activity",
    "get_base_activity",
    "get_menu_activity",
]


def get_mail_activity(
    idle: IdleConfig,
    horde: config.HordeConfig,
    page_config: config.MailsPageConfig,
    view_config: config.MailViewConfig,
    info_config: config.MailInfoConfig,
    return_select: Transition,
    # states
    mails_page: str = "mails_page",
    mail_view: str = "mail_view",
    mail_info: str = "mail_info",
    mail_compose: str = "mail_compose",
    # transition names
    nav_mail: str = "nav_mail",
    refresh_mail: str = "refresh_mail",
    new_mail: str = "new_mail",
    view_mail: str = "view_mail",
    do_nothing: str = "do_nothing",
    delete_mail: str = "delete_mail",
    open_mail: str = "open_mail",
    reply_mail: str = "reply_mail",
    send_mail: str = "send_mail",
    name_prefix: Optional[str] = None,
) -> Tuple[
    Transition,
    states.MailsPage,
    states.MailView,
    states.MailInfo,
    states.MailCompose,
]:
    """Creates the horde mail activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The mail activity states and the mail menu navigation transition.
    """
    # mail transitions

    target_mails_page = f"{name_prefix}_{mails_page}" if name_prefix else mails_page
    target_mail_view = f"{name_prefix}_{mail_view}" if name_prefix else mail_view
    target_mail_info = f"{name_prefix}_{mail_info}" if name_prefix else mail_info
    target_mail_compose = (
        f"{name_prefix}_{mail_compose}" if name_prefix else mail_compose
    )

    t_nav_mail = DelayedTransition(
        transition_function=nav.navigate_mail_menu,
        name=nav_mail,
        target=target_mails_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_refresh_mail = Transition(
        transition_function=actions.refresh_mail,
        name=refresh_mail,
        target=target_mails_page,
        name_prefix=name_prefix,
    )

    t_new_mail = DelayedTransition(
        transition_function=actions.new_mail,
        name=new_mail,
        target=target_mail_compose,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_view_mail = DelayedTransition(
        transition_function=actions.view_mail,
        name=view_mail,
        target=target_mail_view,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_delete_mail = DelayedTransition(
        transition_function=actions.delete_mail,
        name=delete_mail,
        target=target_mails_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_open_mail = DelayedTransition(
        transition_function=actions.open_mail,
        name=open_mail,
        target=target_mail_info,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_reply_mail = DelayedTransition(
        transition_function=actions.reply_mail,
        name=reply_mail,
        target=target_mail_compose,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_send_mail = Transition(
        transition_function=actions.SendMail(
            # we cast here since mypy does not recognize EmailStr as str
            contacts=cast(Dict[str, float], horde.mail.contacts),
            attachments={
                str(path.absolute()): p for path, p in horde.mail.attachments.items()
            },
            extra_recipient_prob=horde.mail.extra_recipient,
            max_recipients=horde.mail.max_recipients,
            attachment_prob=horde.mail.attachment,
            attachment_reply_prob=horde.mail.attachment_reply,
        ),
        name=send_mail,
        target=target_mails_page,
        name_prefix=name_prefix,
    )

    # mail states

    s_mails_page = states.MailsPage(
        name=mails_page,
        view_mail=t_view_mail,
        new_mail=t_new_mail,
        refresh_mail=t_refresh_mail,
        ret_transition=return_select,
        view_mail_weight=page_config.view_mail,
        new_mail_weight=page_config.new_mail,
        refresh_mail_weight=page_config.refresh_mail,
        ret_weight=page_config.return_,
        ret_increase=page_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_mail_view = states.MailView(
        name=mail_view,
        delete_mail=t_delete_mail,
        open_mail=t_open_mail,
        do_nothing=NoopTransition(
            name=do_nothing,
            target=target_mails_page,
            name_prefix=name_prefix,
        ),
        delete_mail_weight=view_config.delete_mail,
        open_mail_weight=view_config.open_mail,
        do_nothing_weight=view_config.do_nothing,
        name_prefix=name_prefix,
    )

    s_mail_info = states.MailInfo(
        name=mail_info,
        delete_mail=t_delete_mail,
        reply_mail=t_reply_mail,
        delete_mail_weight=info_config.delete_mail,
        reply_mail_weight=info_config.reply_mail,
        name_prefix=name_prefix,
    )

    s_mail_compose = states.MailCompose(
        name=mail_compose,
        transition=t_send_mail,
        name_prefix=name_prefix,
    )

    return (
        # mail nav
        t_nav_mail,
        # states
        s_mails_page,
        s_mail_view,
        s_mail_info,
        s_mail_compose,
    )


def get_preferences_activity(
    idle: IdleConfig,
    horde: config.HordeConfig,
    # states
    preferences_page: str = "preferences_page",
    preferences_personal_page: str = "preferences_personal_page",
    selecting_menu: str = "selecting_menu",
    # transitions
    nav_preferences: str = "nav_preferences",
    nav_preferences_personal: str = "nav_preferences_personal",
    set_preferences_personal: str = "set_preferences_personal",
    name_prefix: Optional[str] = None,
) -> Tuple[Transition, states.PreferencesPage, states.PreferencesPersonalPage]:
    """Creates the horde preference configuration activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The preference activity states and the its menu navigation transition.
    """

    if name_prefix:
        target_preferences_page = f"{name_prefix}_{preferences_page}"
        target_preferences_personal_page = f"{name_prefix}_{preferences_personal_page}"
        target_selecting_menu = f"{name_prefix}_{selecting_menu}"
    else:
        target_preferences_page = preferences_page
        target_preferences_personal_page = preferences_page
        target_selecting_menu = preferences_page

    # preferences transitions

    t_nav_preferences = DelayedTransition(
        transition_function=nav.navigate_preferences_global,
        name=nav_preferences,
        target=target_preferences_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_preferences_personal = DelayedTransition(
        transition_function=nav.navigate_preferences_personal,
        name=nav_preferences_personal,
        target=target_preferences_personal_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_set_preferences_personal = DelayedTransition(
        transition_function=actions.SetPersonalPreferences(
            full_name=f"{horde.first_name} {horde.last_name}"
        ),
        name=set_preferences_personal,
        target=target_selecting_menu,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # preferences states

    s_preferences_page = states.PreferencesPage(
        name=preferences_page,
        transition=t_nav_preferences_personal,
        name_prefix=name_prefix,
    )

    s_preferences_personal_page = states.PreferencesPersonalPage(
        name=preferences_personal_page,
        transition=t_set_preferences_personal,
        name_prefix=name_prefix,
    )

    return (
        # preferences nav
        t_nav_preferences,
        s_preferences_page,
        s_preferences_personal_page,
    )


def get_admin_activity(
    idle: IdleConfig,
    admin_config: config.AdminPageConfig,
    groups_config: config.AdminGroupsPageConfig,
    return_select: Transition,
    admin_page: str = "admin_page",
    admin_config_page: str = "admin_config_page",
    admin_groups_page: str = "admin_groups_page",
    admin_group_added: str = "admin_group_added",
    admin_group_deleting: str = "admin_group_deleting",
    admin_php_shell_page: str = "admin_php_shell_page",
    admin_sql_shell_page: str = "admin_sql_shell_page",
    admin_cli_shell_page: str = "admin_cli_shell_page",
    # transitions
    nav_admin: str = "nav_admin",
    nav_config: str = "nav_config",
    check_versions: str = "check_versions",
    nav_groups: str = "nav_groups",
    group_add: str = "group_add",
    group_delete: str = "group_delete",
    group_delete_confirm: str = "group_delete_confirm",
    nav_users: str = "nav_users",
    nav_sessions: str = "nav_sessions",
    nav_alarms: str = "nav_alarms",
    nav_locks: str = "nav_locks",
    nav_permissions: str = "nav_permissions",
    nav_php_shell: str = "nav_php_shell",
    exec_php: str = "exec_php",
    nav_sql_shell: str = "nav_sql_shell",
    exec_sql: str = "exec_sql",
    nav_cli_shell: str = "nav_cli_shell",
    exec_cli: str = "exec_cli",
    name_prefix: Optional[str] = None,
) -> Tuple[
    Transition,
    # states
    states.AdminPage,
    states.AdminConfigPage,
    states.AdminGroupsPage,
    states.AdminGroupAdded,
    states.AdminGroupDeleting,
    states.AdminPHPShellPage,
    states.AdminSQLShellPage,
    states.AdminCLIShellPage,
]:
    """Creates the horde admin configuration activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The admin activity states and the its menu navigation transition.
    """
    if name_prefix:
        target_admin_page = f"{name_prefix}_{admin_page}"
        target_admin_config_page = f"{name_prefix}_{admin_config_page}"
        target_admin_groups_page = f"{name_prefix}_{admin_groups_page}"
        target_admin_group_added = f"{name_prefix}_{admin_group_added}"
        target_admin_group_deleting = f"{name_prefix}_{admin_group_deleting}"
        target_admin_php_shell_page = f"{name_prefix}_{admin_php_shell_page}"
        target_admin_sql_shell_page = f"{name_prefix}_{admin_sql_shell_page}"
        target_admin_cli_shell_page = f"{name_prefix}_{admin_cli_shell_page}"
    else:
        target_admin_page = admin_page
        target_admin_config_page = admin_config_page
        target_admin_groups_page = admin_groups_page
        target_admin_group_added = admin_group_added
        target_admin_group_deleting = admin_group_deleting
        target_admin_php_shell_page = admin_php_shell_page
        target_admin_sql_shell_page = admin_sql_shell_page
        target_admin_cli_shell_page = admin_cli_shell_page

    # admin transitions
    t_nav_admin = DelayedTransition(
        transition_function=nav.navigate_admin_configuration,
        name=nav_admin,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_config = DelayedTransition(
        transition_function=nav.navigate_admin_configuration,
        name=nav_config,
        target=target_admin_config_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_check_versions = DelayedTransition(
        transition_function=actions.admin_check_versions,
        name=check_versions,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_groups = DelayedTransition(
        transition_function=nav.navigate_admin_groups,
        name=nav_groups,
        target=target_admin_groups_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_group_add = DelayedTransition(
        transition_function=actions.add_user_group,
        name=group_add,
        target=target_admin_group_added,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_group_delete = DelayedTransition(
        transition_function=actions.delete_user_group,
        name=group_delete,
        target=target_admin_group_deleting,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_group_delete_confirm = DelayedTransition(
        transition_function=actions.confirm_delete_user_group,
        name=group_delete_confirm,
        target=target_admin_groups_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_users = DelayedTransition(
        transition_function=nav.navigate_admin_users,
        name=nav_users,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_sessions = DelayedTransition(
        transition_function=nav.navigate_admin_sessions,
        name=nav_sessions,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_alarms = DelayedTransition(
        transition_function=nav.navigate_admin_alarms,
        name=nav_alarms,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_locks = DelayedTransition(
        transition_function=nav.navigate_admin_locks,
        name=nav_locks,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_permissions = DelayedTransition(
        transition_function=nav.navigate_admin_permissions,
        name=nav_permissions,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_php_shell = DelayedTransition(
        transition_function=nav.navigate_admin_php_shell,
        name=nav_php_shell,
        target=target_admin_php_shell_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_exec_php = DelayedTransition(
        transition_function=actions.admin_exec_php,
        name=exec_php,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_sql_shell = DelayedTransition(
        transition_function=nav.navigate_admin_sql_shell,
        name=nav_sql_shell,
        target=target_admin_sql_shell_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_exec_sql = DelayedTransition(
        transition_function=actions.admin_exec_sql,
        name=exec_sql,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_cli_shell = DelayedTransition(
        transition_function=nav.navigate_admin_cli,
        name=nav_cli_shell,
        target=target_admin_cli_shell_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_exec_cli = DelayedTransition(
        transition_function=actions.admin_exec_cli,
        name=exec_cli,
        target=target_admin_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # admin states

    s_admin_page = states.AdminPage(
        name=admin_page,
        nav_config=t_nav_config,
        nav_groups=t_nav_groups,
        nav_users=t_nav_users,
        nav_sessions=t_nav_sessions,
        nav_alarms=t_nav_alarms,
        nav_locks=t_nav_locks,
        nav_permissions=t_nav_permissions,
        nav_php_shell=t_nav_php_shell,
        nav_sql_shell=t_nav_sql_shell,
        nav_cli_shell=t_nav_cli_shell,
        ret_transition=return_select,
        nav_config_weight=admin_config.nav_config,
        nav_groups_weight=admin_config.nav_groups,
        nav_users_weight=admin_config.nav_users,
        nav_sessions_weight=admin_config.nav_sessions,
        nav_alarms_weight=admin_config.nav_alarms,
        nav_locks_weight=admin_config.nav_locks,
        nav_permissions_weight=admin_config.nav_permissions,
        nav_php_shell_weight=admin_config.nav_php_shell,
        nav_sql_shell_weight=admin_config.nav_sql_shell,
        nav_cli_shell_weight=admin_config.nav_cli_shell,
        ret_weight=admin_config.return_,
        ret_increase=admin_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_admin_config_page = states.AdminConfigPage(
        name=admin_config_page,
        transition=t_check_versions,
        name_prefix=name_prefix,
    )

    s_admin_groups_page = states.AdminGroupsPage(
        name=admin_groups_page,
        group_add=t_group_add,
        group_delete=t_group_delete,
        ret_transition=return_select,
        group_add_weight=groups_config.group_add,
        group_delete_weight=groups_config.group_delete,
        ret_weight=groups_config.return_,
        ret_increase=groups_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_admin_group_added = states.AdminGroupAdded(
        name=admin_group_added,
        transition=t_nav_groups,
        name_prefix=name_prefix,
    )

    s_admin_group_deleting = states.AdminGroupDeleting(
        name=admin_group_deleting,
        transition=t_group_delete_confirm,
        name_prefix=name_prefix,
    )

    s_admin_php_shell_page = states.AdminPHPShellPage(
        name=admin_php_shell_page,
        transition=t_exec_php,
        name_prefix=name_prefix,
    )

    s_admin_sql_shell_page = states.AdminSQLShellPage(
        name=admin_sql_shell_page,
        transition=t_exec_sql,
        name_prefix=name_prefix,
    )

    s_admin_cli_shell_page = states.AdminCLIShellPage(
        name=admin_cli_shell_page,
        transition=t_exec_cli,
        name_prefix=name_prefix,
    )

    return (
        t_nav_admin,
        # states
        s_admin_page,
        s_admin_config_page,
        s_admin_groups_page,
        s_admin_group_added,
        s_admin_group_deleting,
        s_admin_php_shell_page,
        s_admin_sql_shell_page,
        s_admin_cli_shell_page,
    )


def get_notes_activity(
    idle: IdleConfig,
    page_config: config.NotesPageConfig,
    editor_config: config.NoteEditorConfig,
    return_select: Transition,
    notes_page: str = "notes_page",
    note_creator: str = "note_creator",
    note_editor: str = "note_editor",
    # transitions
    nav_notes: str = "nav_notes",
    new_note: str = "new_note",
    write_note: str = "write_note",
    edit_note: str = "edit_note",
    delete_note: str = "delete_note",
    name_prefix: Optional[str] = None,
) -> Tuple[
    Transition,
    # states
    states.NotesPage,
    states.NoteCreator,
    states.NoteEditor,
]:
    """Creates the horde notes activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The notes activity states and the its menu navigation transition.
    """
    if name_prefix:
        target_notes_page = f"{name_prefix}_{notes_page}"
        target_note_creator = f"{name_prefix}_{note_creator}"
        target_note_editor = f"{name_prefix}_{note_editor}"
    else:
        target_notes_page = notes_page
        target_note_creator = note_creator
        target_note_editor = note_editor

    # notes transitions
    t_nav_notes = DelayedTransition(
        transition_function=nav.navigate_notes_menu,
        name=nav_notes,
        target=target_notes_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_new_note = DelayedTransition(
        transition_function=actions.new_note,
        name=new_note,
        target=target_note_creator,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_write_note = DelayedTransition(
        transition_function=actions.write_note,
        name=write_note,
        target=target_notes_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_edit_note = DelayedTransition(
        transition_function=actions.edit_note,
        name=edit_note,
        target=target_note_editor,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_delete_note = DelayedTransition(
        transition_function=actions.delete_note,
        name=delete_note,
        target=target_notes_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # note states

    s_notes_page = states.NotesPage(
        name=notes_page,
        new_note=t_new_note,
        edit_note=t_edit_note,
        ret_transition=return_select,
        new_note_weight=page_config.new_note,
        edit_note_weight=page_config.edit_note,
        ret_weight=page_config.return_,
        ret_increase=page_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_note_creator = states.NoteCreator(
        name=note_creator,
        transition=t_write_note,
        name_prefix=name_prefix,
    )

    s_note_editor = states.NoteEditor(
        name=note_editor,
        write_note=t_write_note,
        delete_note=t_delete_note,
        write_note_weight=editor_config.write_note,
        delete_note_weight=editor_config.delete_note,
        name_prefix=name_prefix,
    )

    return (
        t_nav_notes,
        # states
        s_notes_page,
        s_note_creator,
        s_note_editor,
    )


def get_tasks_activity(
    idle: IdleConfig,
    page_config: config.TasksPageConfig,
    return_select: Transition,
    # states
    tasks_page: str = "tasks_page",
    task_creator: str = "task_creator",
    task_editor: str = "task_editor",
    # transitions
    nav_tasks: str = "nav_tasks",
    new_task: str = "new_task",
    save_task: str = "save_task",
    edit_task: str = "edit_task",
    delete_task: str = "delete_task",
    name_prefix: Optional[str] = None,
) -> Tuple[
    Transition,
    # states
    states.TasksPage,
    states.TaskCreator,
    states.TaskEditor,
]:
    """Creates the horde tasks activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The tasks activity states and the its menu navigation transition.
    """

    if name_prefix:
        target_tasks_page = f"{name_prefix}_{tasks_page}"
        target_task_creator = f"{name_prefix}_{task_creator}"
        target_task_editor = f"{name_prefix}_{task_editor}"
    else:
        target_tasks_page = tasks_page
        target_task_creator = task_creator
        target_task_editor = task_editor

    # tasks transitions
    t_nav_tasks = DelayedTransition(
        transition_function=nav.navigate_tasks_menu,
        name=nav_tasks,
        target=target_tasks_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_new_task = DelayedTransition(
        transition_function=actions.new_task,
        name=new_task,
        target=target_task_creator,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_save_task = DelayedTransition(
        transition_function=actions.save_new_task,
        name=save_task,
        target=target_tasks_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_edit_task = DelayedTransition(
        transition_function=actions.edit_task,
        name=edit_task,
        target=target_task_editor,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_delete_task = DelayedTransition(
        transition_function=actions.delete_task,
        name=delete_task,
        target=target_tasks_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # task states

    s_tasks_page = states.TasksPage(
        name=tasks_page,
        new_task=t_new_task,
        edit_task=t_edit_task,
        ret_transition=return_select,
        new_task_weight=page_config.new_task,
        edit_task_weight=page_config.edit_task,
        ret_weight=page_config.return_,
        ret_increase=page_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_task_creator = states.TaskCreator(
        name=task_creator,
        transition=t_save_task,
        name_prefix=name_prefix,
    )

    s_task_editor = states.TaskEditor(
        name=task_editor,
        transition=t_delete_task,
        name_prefix=name_prefix,
    )

    return (
        t_nav_tasks,
        # states
        s_tasks_page,
        s_task_creator,
        s_task_editor,
    )


def get_address_book_activity(
    idle: IdleConfig,
    page_config: config.AddressBookPageConfig,
    browser_config: config.ContactsBrowserConfig,
    info_config: config.ContactInfoConfig,
    return_select: Transition,
    # states
    address_book_page: str = "address_book_page",
    contact_compose: str = "contact_compose",
    contacts_browser: str = "contacts_browser",
    contact_info: str = "contact_info",
    contact_delete_confirming: str = "contact_delete_confirming",
    # transitions
    nav_address_book: str = "nav_address_book",
    new_contact: str = "new_contact",
    submit_contact: str = "submit_contact",
    nav_contacts_browse: str = "nav_contacts_browse",
    do_nothing: str = "do_nothing",
    view_contact: str = "view_contact",
    delete_contact: str = "delete_contact",
    delete_contact_confirm: str = "delete_contact_confirm",
    name_prefix: Optional[str] = None,
) -> Tuple[
    Transition,
    # states
    states.AddressBookPage,
    states.ContactCompose,
    states.ContactsBrowser,
    states.ContactInfo,
    states.ContactDeleteConfirming,
]:
    """Creates the horde address book activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The address book activity states and the its menu navigation transition.
    """
    if name_prefix:
        target_address_book_page = f"{name_prefix}_{address_book_page}"
        target_contact_compose = f"{name_prefix}_{contact_compose}"
        target_contacts_browser = f"{name_prefix}_{contacts_browser}"
        target_contact_info = f"{name_prefix}_{contact_info}"
        target_contact_delete_confirming = f"{name_prefix}_{contact_delete_confirming}"
    else:
        target_address_book_page = address_book_page
        target_contact_compose = contact_compose
        target_contacts_browser = contacts_browser
        target_contact_info = contact_info
        target_contact_delete_confirming = contact_delete_confirming

    # address book transitions

    t_nav_address_book = DelayedTransition(
        transition_function=nav.navigate_address_book_menu,
        name=nav_address_book,
        target=target_address_book_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_new_contact = DelayedTransition(
        transition_function=actions.start_add_contact,
        name=new_contact,
        target=target_contact_compose,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_submit_contact = DelayedTransition(
        transition_function=actions.submit_new_contact,
        name=submit_contact,
        target=target_address_book_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_nav_contacts_browse = DelayedTransition(
        transition_function=nav.navigate_address_book_browse,
        name=nav_contacts_browse,
        target=target_contacts_browser,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_contacts_do_nothing = DelayedTransition(
        transition_function=nav.navigate_address_book_menu,
        name=do_nothing,
        target=target_address_book_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_view_contact = DelayedTransition(
        transition_function=nav.navigate_address_book_contact,
        name=view_contact,
        target=target_contact_info,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_delete_contact = DelayedTransition(
        transition_function=actions.delete_contact,
        name=delete_contact,
        target=target_contact_delete_confirming,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_delete_contact_confirm = DelayedTransition(
        transition_function=actions.confirm_delete_contact,
        name=delete_contact_confirm,
        target=target_address_book_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # address book states

    s_address_book_page = states.AddressBookPage(
        name=address_book_page,
        new_contact=t_new_contact,
        browse_contacts=t_nav_contacts_browse,
        ret_transition=return_select,
        new_contact_weight=page_config.new_contact,
        browse_contacts_weight=page_config.browse_contacts,
        ret_transition_weight=page_config.return_,
        ret_increase=page_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_contact_compose = states.ContactCompose(
        name=contact_compose,
        transition=t_submit_contact,
        name_prefix=name_prefix,
    )

    s_contacts_browser = states.ContactsBrowser(
        name=contacts_browser,
        new_contact=t_new_contact,
        view_contact=t_view_contact,
        new_contact_weight=browser_config.new_contact,
        view_contact_weight=browser_config.view_contact,
        name_prefix=name_prefix,
    )

    s_contact_info = states.ContactInfo(
        name=contact_info,
        delete_contact=t_delete_contact,
        do_nothing=t_contacts_do_nothing,
        delete_contact_weight=info_config.delete_contact,
        do_nothing_weight=info_config.do_nothing,
        name_prefix=name_prefix,
    )

    s_contact_delete_confirming = states.ContactDeleteConfirming(
        name=contact_delete_confirming,
        transition=t_delete_contact_confirm,
        name_prefix=name_prefix,
    )

    return (
        t_nav_address_book,
        # states
        s_address_book_page,
        s_contact_compose,
        s_contacts_browser,
        s_contact_info,
        s_contact_delete_confirming,
    )


def get_calendar_activity(
    idle: IdleConfig,
    page_config: config.CalendarPageConfig,
    edit_config: config.EventEditConfig,
    return_select: Transition,
    calendar_page: str = "calendar_page",
    event_compose: str = "event_compose",
    event_edit: str = "event_edit",
    # transitions
    nav_calendar: str = "nav_calendar",
    new_event: str = "new_event",
    write_event: str = "write_event",
    edit_event: str = "edit_event",
    delete_event: str = "delete_event",
    name_prefix: Optional[str] = None,
) -> Tuple[
    Transition,
    # states
    states.CalendarPage,
    states.EventCompose,
    states.EventEdit,
]:
    """Creates the horde calendar activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The calendar activity states and the its menu navigation transition.
    """
    # calendar transitions

    if name_prefix:
        target_calendar_page = f"{name_prefix}_{calendar_page}"
        target_event_compose = f"{name_prefix}_{event_compose}"
        target_event_edit = f"{name_prefix}_{event_edit}"
    else:
        target_calendar_page = calendar_page
        target_event_compose = event_compose
        target_event_edit = event_edit

    t_nav_calendar = DelayedTransition(
        transition_function=nav.navigate_calendar_menu,
        name=nav_calendar,
        target=target_calendar_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_new_event = DelayedTransition(
        transition_function=actions.new_calendar_event,
        name=new_event,
        target=target_event_compose,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_write_event = DelayedTransition(
        transition_function=actions.write_calendar_event,
        name=write_event,
        target=target_calendar_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_edit_event = DelayedTransition(
        transition_function=actions.edit_calendar_event,
        name=edit_event,
        target=target_event_edit,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_delete_event = DelayedTransition(
        transition_function=actions.delete_calendar_event,
        name=delete_event,
        target=target_calendar_page,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # calendar states

    s_calendar_page = states.CalendarPage(
        name=calendar_page,
        new_event=t_new_event,
        edit_event=t_edit_event,
        ret_transition=return_select,
        new_event_weight=page_config.new_event,
        edit_event_weight=page_config.edit_event,
        ret_weight=page_config.return_,
        ret_increase=page_config.extra.return_increase,
        name_prefix=name_prefix,
    )

    s_event_compose = states.EventCompose(
        name=event_compose,
        transition=t_write_event,
        name_prefix=name_prefix,
    )

    s_event_edit = states.EventEdit(
        name=event_edit,
        write_event=t_write_event,
        delete_event=t_delete_event,
        write_event_weight=edit_config.write_event,
        delete_event_weight=edit_config.delete_event,
        name_prefix=name_prefix,
    )

    return (
        t_nav_calendar,
        # states
        s_calendar_page,
        s_event_compose,
        s_event_edit,
    )


def get_base_activity(
    idle: IdleConfig,
    horde: config.HordeConfig,
    login_config: config.LoginPageConfig,
    logout_config: config.LogoutChoiceConfig,
    root: str = "selecting_activity",
    selecting_menu: str = "selecting_menu",
    login_check: str = "login_check",
    login_page: str = "login_page",
    logout_choice: str = "logout?",
    # transitions
    horde_transition: str = "go_to_horde",
    login: str = "login",
    fail_login: str = "fail_login",
    pause_horde: str = "pause_horde",
    horde_logout: str = "horde_logout",
    return_select: str = "return_select",
    name_prefix: Optional[str] = None,
) -> Tuple[
    # transitions
    Transition,
    Transition,
    Transition,
    # states
    states.LoggedInCheck,
    states.LoginPage,
    states.LogoutChoice,
]:
    """Creates the horde base activity (i.e., login and logout) and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The horde open, pause and return to selection menu transition as well as the
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

    t_horde_transition = Transition(
        transition_function=nav.GoToHordeWebsite(horde.url),
        name=horde_transition,
        target=target_login_check,
        name_prefix=name_prefix,
    )

    t_login = DelayedTransition(
        transition_function=actions.LoginToHorde(
            username=horde.username,
            password=horde.password,
        ),
        name=login,
        target=target_selecting_menu,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_fail_login = DelayedTransition(
        transition_function=actions.LoginToHorde(
            username=horde.username,
            password=horde.password,
            fail=True,
        ),
        name=fail_login,
        target=target_login_page,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_pause_horde = DelayedTransition(
        transition_function=noop,
        name=pause_horde,
        target=target_logout_choice,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_return_select = DelayedTransition(
        transition_function=noop,
        name=return_select,
        target=target_selecting_menu,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_horde_logout = DelayedTransition(
        transition_function=actions.logout_of_horde,
        name=horde_logout,
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
        logout=t_horde_logout,
        logout_prob=logout_config.logout_chance,
        name_prefix=name_prefix,
    )

    return (
        # transitions
        t_horde_transition,
        t_pause_horde,
        t_return_select,
        # states
        s_login_check,
        s_login_page,
        s_logout_choice,
    )


def get_menu_activity(
    menu_config: config.SelectingMenuConfig,
    nav_mail: Transition,
    nav_preferences: Transition,
    nav_admin: Transition,
    nav_notes: Transition,
    nav_tasks: Transition,
    nav_address_book: Transition,
    nav_calendar: Transition,
    pause_horde: Transition,
    selecting_menu: str = "selecting_menu",
    name_prefix: Optional[str] = None,
) -> states.SelectingMenu:
    """Creates the horde main menu selection activity and its underlying state and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The menu selection state
    """
    return states.SelectingMenu(
        name=selecting_menu,
        nav_mail=nav_mail,
        nav_preferences=nav_preferences,
        nav_admin=nav_admin,
        nav_notes=nav_notes,
        nav_tasks=nav_tasks,
        nav_address_book=nav_address_book,
        nav_calendar=nav_calendar,
        ret_transition=pause_horde,
        nav_mail_weight=menu_config.nav_mail,
        nav_preferences_weight=menu_config.nav_preferences,
        nav_admin_weight=menu_config.nav_admin,
        nav_notes_weight=menu_config.nav_notes,
        nav_tasks_weight=menu_config.nav_tasks,
        nav_address_book_weight=menu_config.nav_address_book,
        nav_calendar_weight=menu_config.nav_calendar,
        ret_weight=menu_config.return_,
        ret_increase=menu_config.extra.return_increase,
        name_prefix=name_prefix,
    )
