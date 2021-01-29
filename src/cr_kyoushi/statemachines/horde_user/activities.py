from typing import (
    Dict,
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
) -> Tuple[
    Transition,
    states.MailsPage,
    states.MailView,
    states.MailInfo,
    states.MailCompose,
]:
    # mail transitions

    t_nav_mail = DelayedTransition(
        transition_function=nav.navigate_mail_menu,
        name=nav_mail,
        target=mails_page,
        delay_after=idle.small,
    )

    t_refresh_mail = Transition(
        transition_function=actions.refresh_mail,
        name=refresh_mail,
        target=mails_page,
    )

    t_new_mail = DelayedTransition(
        transition_function=actions.new_mail,
        name=new_mail,
        target=mail_compose,
        delay_after=idle.small,
    )

    t_view_mail = DelayedTransition(
        transition_function=actions.view_mail,
        name=view_mail,
        target=mail_view,
        delay_after=idle.small,
    )

    t_delete_mail = DelayedTransition(
        transition_function=actions.delete_mail,
        name=delete_mail,
        target=mails_page,
        delay_after=idle.small,
    )

    t_open_mail = DelayedTransition(
        transition_function=actions.open_mail,
        name=open_mail,
        target=mail_info,
        delay_after=idle.small,
    )

    t_reply_mail = DelayedTransition(
        transition_function=actions.reply_mail,
        name=reply_mail,
        target=mail_compose,
        delay_after=idle.small,
    )

    t_send_mail = Transition(
        transition_function=actions.SendMail(
            # we cast here since mypy does not recognize EmailStr as str
            contacts=cast(Dict[str, float], horde.contacts),
            attachments={
                str(path.absolute()): p for path, p in horde.attachments.items()
            },
        ),
        name=send_mail,
        target=mails_page,
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
    )

    s_mail_view = states.MailView(
        name=mail_view,
        delete_mail=t_delete_mail,
        open_mail=t_open_mail,
        do_nothing=NoopTransition(
            name=do_nothing,
            target=mails_page,
        ),
        delete_mail_weight=view_config.delete_mail,
        open_mail_weight=view_config.open_mail,
        do_nothing_weight=view_config.do_nothing,
    )

    s_mail_info = states.MailInfo(
        name=mail_info,
        delete_mail=t_delete_mail,
        reply_mail=t_reply_mail,
        delete_mail_weight=info_config.delete_mail,
        reply_mail_weight=info_config.reply_mail,
    )

    s_mail_compose = states.MailCompose(
        name=mail_compose,
        transition=t_send_mail,
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
) -> Tuple[Transition, states.PreferencesPage, states.PreferencesPersonalPage]:
    # preferences transitions

    t_nav_preferences = DelayedTransition(
        transition_function=nav.navigate_preferences_global,
        name=nav_preferences,
        target=preferences_page,
        delay_after=idle.small,
    )

    t_nav_preferences_personal = DelayedTransition(
        transition_function=nav.navigate_preferences_personal,
        name=nav_preferences_personal,
        target=preferences_personal_page,
        delay_after=idle.small,
    )

    t_set_preferences_personal = DelayedTransition(
        transition_function=actions.SetPersonalPreferences(
            full_name=f"{horde.first_name} {horde.last_name}"
        ),
        name=set_preferences_personal,
        target=selecting_menu,
        delay_after=idle.small,
    )

    # preferences states

    s_preferences_page = states.PreferencesPage(
        name=preferences_page,
        transition=t_nav_preferences_personal,
    )

    s_preferences_personal_page = states.PreferencesPersonalPage(
        name=preferences_personal_page,
        transition=t_set_preferences_personal,
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
    # admin transitions
    t_nav_admin = DelayedTransition(
        transition_function=nav.navigate_admin_configuration,
        name=nav_admin,
        target=admin_page,
        delay_after=idle.small,
    )

    t_nav_config = DelayedTransition(
        transition_function=nav.navigate_admin_configuration,
        name=nav_config,
        target=admin_config_page,
        delay_after=idle.small,
    )

    t_check_versions = DelayedTransition(
        transition_function=actions.admin_check_versions,
        name=check_versions,
        target=admin_page,
        delay_after=idle.small,
    )

    t_nav_groups = DelayedTransition(
        transition_function=nav.navigate_admin_groups,
        name=nav_groups,
        target=admin_groups_page,
        delay_after=idle.small,
    )

    t_group_add = DelayedTransition(
        transition_function=actions.add_user_group,
        name=group_add,
        target=admin_group_added,
        delay_after=idle.small,
    )

    t_group_delete = DelayedTransition(
        transition_function=actions.delete_user_group,
        name=group_delete,
        target=admin_group_deleting,
        delay_after=idle.tiny,
    )

    t_group_delete_confirm = DelayedTransition(
        transition_function=actions.confirm_delete_user_group,
        name=group_delete_confirm,
        target=admin_groups_page,
        delay_after=idle.small,
    )

    t_nav_users = DelayedTransition(
        transition_function=nav.navigate_admin_users,
        name=nav_users,
        target=admin_page,
        delay_after=idle.small,
    )

    t_nav_sessions = DelayedTransition(
        transition_function=nav.navigate_admin_sessions,
        name=nav_sessions,
        target=admin_page,
        delay_after=idle.small,
    )

    t_nav_alarms = DelayedTransition(
        transition_function=nav.navigate_admin_alarms,
        name=nav_alarms,
        target=admin_page,
        delay_after=idle.small,
    )

    t_nav_locks = DelayedTransition(
        transition_function=nav.navigate_admin_locks,
        name=nav_locks,
        target=admin_page,
        delay_after=idle.small,
    )

    t_nav_permissions = DelayedTransition(
        transition_function=nav.navigate_admin_permissions,
        name=nav_permissions,
        target=admin_page,
        delay_after=idle.small,
    )

    t_nav_php_shell = DelayedTransition(
        transition_function=nav.navigate_admin_php_shell,
        name=nav_php_shell,
        target=admin_php_shell_page,
        delay_after=idle.small,
    )

    t_exec_php = DelayedTransition(
        transition_function=actions.admin_exec_php,
        name=exec_php,
        target=admin_page,
        delay_after=idle.small,
    )

    t_nav_sql_shell = DelayedTransition(
        transition_function=nav.navigate_admin_sql_shell,
        name=nav_sql_shell,
        target=admin_sql_shell_page,
        delay_after=idle.small,
    )

    t_exec_sql = DelayedTransition(
        transition_function=actions.admin_exec_sql,
        name=exec_sql,
        target=admin_page,
        delay_after=idle.small,
    )

    t_nav_cli_shell = DelayedTransition(
        transition_function=nav.navigate_admin_cli,
        name=nav_cli_shell,
        target=admin_cli_shell_page,
        delay_after=idle.small,
    )

    t_exec_cli = DelayedTransition(
        transition_function=actions.admin_exec_cli,
        name=exec_cli,
        target=admin_page,
        delay_after=idle.small,
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
    )

    s_admin_config_page = states.AdminConfigPage(
        name=admin_config_page,
        transition=t_check_versions,
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
    )

    s_admin_group_added = states.AdminGroupAdded(
        name=admin_group_added,
        transition=t_nav_groups,
    )

    s_admin_group_deleting = states.AdminGroupDeleting(
        name=admin_group_deleting,
        transition=t_group_delete_confirm,
    )

    s_admin_php_shell_page = states.AdminPHPShellPage(
        name=admin_php_shell_page,
        transition=t_exec_php,
    )

    s_admin_sql_shell_page = states.AdminSQLShellPage(
        name=admin_sql_shell_page,
        transition=t_exec_sql,
    )

    s_admin_cli_shell_page = states.AdminCLIShellPage(
        name=admin_cli_shell_page,
        transition=t_exec_cli,
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
) -> Tuple[
    Transition,
    # states
    states.NotesPage,
    states.NoteCreator,
    states.NoteEditor,
]:
    # notes transitions
    t_nav_notes = DelayedTransition(
        transition_function=nav.navigate_notes_menu,
        name=nav_notes,
        target=notes_page,
        delay_after=idle.small,
    )

    t_new_note = DelayedTransition(
        transition_function=actions.new_note,
        name=new_note,
        target=note_creator,
        delay_after=idle.tiny,
    )

    t_write_note = DelayedTransition(
        transition_function=actions.write_note,
        name=write_note,
        target=notes_page,
        delay_after=idle.small,
    )

    t_edit_note = DelayedTransition(
        transition_function=actions.edit_note,
        name=edit_note,
        target=note_editor,
        delay_after=idle.small,
    )

    t_delete_note = DelayedTransition(
        transition_function=actions.delete_note,
        name=delete_note,
        target=notes_page,
        delay_after=idle.small,
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
    )

    s_note_creator = states.NoteCreator(
        name=note_creator,
        transition=t_write_note,
    )

    s_note_editor = states.NoteEditor(
        name=note_editor,
        write_note=t_write_note,
        delete_note=t_delete_note,
        write_note_weight=editor_config.write_note,
        delete_note_weight=editor_config.delete_note,
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
) -> Tuple[
    Transition,
    # states
    states.TasksPage,
    states.TaskCreator,
    states.TaskEditor,
]:
    # tasks transitions
    t_nav_tasks = DelayedTransition(
        transition_function=nav.navigate_tasks_menu,
        name=nav_tasks,
        target=tasks_page,
        delay_after=idle.small,
    )

    t_new_task = DelayedTransition(
        transition_function=actions.new_task,
        name=new_task,
        target=task_creator,
        delay_after=idle.tiny,
    )

    t_save_task = DelayedTransition(
        transition_function=actions.save_new_task,
        name=save_task,
        target=tasks_page,
        delay_after=idle.small,
    )

    t_edit_task = DelayedTransition(
        transition_function=actions.edit_task,
        name=edit_task,
        target=task_editor,
        delay_after=idle.small,
    )

    t_delete_task = DelayedTransition(
        transition_function=actions.delete_task,
        name=delete_task,
        target=tasks_page,
        delay_after=idle.small,
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
    )

    s_task_creator = states.TaskCreator(
        name=task_creator,
        transition=t_save_task,
    )

    s_task_editor = states.TaskEditor(
        name=task_editor,
        transition=t_delete_task,
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
) -> Tuple[
    Transition,
    # states
    states.AddressBookPage,
    states.ContactCompose,
    states.ContactsBrowser,
    states.ContactInfo,
    states.ContactDeleteConfirming,
]:
    # address book transitions

    t_nav_address_book = DelayedTransition(
        transition_function=nav.navigate_address_book_menu,
        name=nav_address_book,
        target=address_book_page,
        delay_after=idle.small,
    )

    t_new_contact = DelayedTransition(
        transition_function=actions.start_add_contact,
        name=new_contact,
        target=contact_compose,
        delay_after=idle.tiny,
    )

    t_submit_contact = DelayedTransition(
        transition_function=actions.submit_new_contact,
        name=submit_contact,
        target=address_book_page,
        delay_after=idle.small,
    )

    t_nav_contacts_browse = DelayedTransition(
        transition_function=nav.navigate_address_book_browse,
        name=nav_contacts_browse,
        target=contacts_browser,
        delay_after=idle.small,
    )

    t_contacts_do_nothing = DelayedTransition(
        transition_function=nav.navigate_address_book_menu,
        name=do_nothing,
        target=address_book_page,
        delay_after=idle.small,
    )

    t_view_contact = DelayedTransition(
        transition_function=nav.navigate_address_book_contact,
        name=view_contact,
        target=contact_info,
        delay_after=idle.small,
    )

    t_delete_contact = DelayedTransition(
        transition_function=actions.delete_contact,
        name=delete_contact,
        target=contact_delete_confirming,
        delay_after=idle.tiny,
    )

    t_delete_contact_confirm = DelayedTransition(
        transition_function=actions.confirm_delete_contact,
        name=delete_contact_confirm,
        target=address_book_page,
        delay_after=idle.small,
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
    )

    s_contact_compose = states.ContactCompose(
        name=contact_compose,
        transition=t_submit_contact,
    )

    s_contacts_browser = states.ContactsBrowser(
        name=contacts_browser,
        new_contact=t_new_contact,
        view_contact=t_view_contact,
        new_contact_weight=browser_config.new_contact,
        view_contact_weight=browser_config.view_contact,
    )

    s_contact_info = states.ContactInfo(
        name=contact_info,
        delete_contact=t_delete_contact,
        do_nothing=t_contacts_do_nothing,
        delete_contact_weight=info_config.delete_contact,
        do_nothing_weight=info_config.do_nothing,
    )

    s_contact_delete_confirming = states.ContactDeleteConfirming(
        name=contact_delete_confirming,
        transition=t_delete_contact_confirm,
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
) -> Tuple[
    Transition,
    # states
    states.CalendarPage,
    states.EventCompose,
    states.EventEdit,
]:
    # calendar transitions

    t_nav_calendar = DelayedTransition(
        transition_function=nav.navigate_calendar_menu,
        name=nav_calendar,
        target=calendar_page,
        delay_after=idle.small,
    )

    t_new_event = DelayedTransition(
        transition_function=actions.new_calendar_event,
        name=new_event,
        target=event_compose,
        delay_after=idle.tiny,
    )

    t_write_event = DelayedTransition(
        transition_function=actions.write_calendar_event,
        name=write_event,
        target=calendar_page,
        delay_after=idle.small,
    )

    t_edit_event = DelayedTransition(
        transition_function=actions.edit_calendar_event,
        name=edit_event,
        target=event_edit,
        delay_after=idle.small,
    )

    t_delete_event = DelayedTransition(
        transition_function=actions.delete_calendar_event,
        name=delete_event,
        target=calendar_page,
        delay_after=idle.small,
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
    )

    s_event_compose = states.EventCompose(
        name=event_compose,
        transition=t_write_event,
    )

    s_event_edit = states.EventEdit(
        name=event_edit,
        write_event=t_write_event,
        delete_event=t_delete_event,
        write_event_weight=edit_config.write_event,
        delete_event_weight=edit_config.delete_event,
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

    t_horde_transition = Transition(
        transition_function=nav.GoToHordeWebsite(horde.url),
        name=horde_transition,
        target=login_check,
    )

    t_login = DelayedTransition(
        transition_function=actions.LoginToHorde(
            username=horde.username,
            password=horde.password,
        ),
        name=login,
        target=selecting_menu,
        delay_after=idle.small,
    )

    t_fail_login = DelayedTransition(
        transition_function=actions.LoginToHorde(
            username=horde.username,
            password=horde.password,
            fail=True,
        ),
        name=fail_login,
        target=login_page,
        delay_after=idle.tiny,
    )

    t_pause_horde = DelayedTransition(
        transition_function=noop,
        name=pause_horde,
        target=logout_choice,
        delay_after=idle.small,
    )

    t_return_select = DelayedTransition(
        transition_function=noop,
        name=return_select,
        target=selecting_menu,
        delay_after=idle.medium,
    )

    t_horde_logout = DelayedTransition(
        transition_function=actions.logout_of_horde,
        name=horde_logout,
        target=root,
        delay_after=idle.small,
    )

    s_login_check = states.LoggedInCheck(
        name=login_check,
        login_state=login_page,
        selecting_menu_state=selecting_menu,
    )

    s_login_page = states.LoginPage(
        name=login_page,
        login=t_login,
        fail_login=t_fail_login,
        fail_weight=login_config.fail_chance,
        fail_decrease_factor=login_config.fail_decrease,
    )

    s_logout_choice = states.LogoutChoice(
        name=logout_choice,
        logout=t_horde_logout,
        logout_prob=logout_config.logout_chance,
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
) -> states.SelectingMenu:
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
    )
