"""Configuration classes for the horde user activity and state machine"""

from typing import Dict

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    FilePath,
    HttpUrl,
    validator,
)

from ..core.config import (
    ActivityExtraConfig,
    ProbabilisticStateConfig,
)
from ..core.selenium import SeleniumStatemachineConfig
from ..core.util import positive_smaller_one


__all__ = [
    "StatemachineConfig",
    "HordeStates",
    "HordeUserStates",
    "HordeMailConfig",
    "HordeConfig",
    "ActivitySelectionConfig",
    "LoginPageConfig",
    "LogoutChoiceConfig",
    "SelectingMenuConfig",
    "MailsPageConfig",
    "MailViewConfig",
    "MailInfoConfig",
    "AdminPageConfig",
    "AdminGroupsPageConfig",
    "NotesPageConfig",
    "NoteEditorConfig",
    "TasksPageConfig",
    "AddressBookPageConfig",
    "ContactsBrowserConfig",
    "ContactInfoConfig",
    "CalendarPageConfig",
    "EventEditConfig",
]


class ActivitySelectionConfig(ProbabilisticStateConfig):
    """Horde user state machines selecting activity states configuration."""

    horde: float = Field(
        0.6,
        description="The base propability that horde will be selected.",
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

    nav_mail: float = Field(
        0.3,
        description="The base propability that nav_mail will be selected.",
    )
    nav_preferences: float = Field(
        0.1,
        description="The base propability that nav_preferences will be selected.",
    )
    nav_admin: float = Field(
        0,
        description="The base propability that nav_admin will be selected.",
    )
    nav_notes: float = Field(
        0.15,
        description="The base propability that nav_notes will be selected.",
    )
    nav_tasks: float = Field(
        0.1,
        description="The base propability that nav_tasks will be selected.",
    )
    nav_address_book: float = Field(
        0.125,
        description="The base propability that nav_address_book will be selected.",
    )
    nav_calendar: float = Field(
        0.15,
        description="The base propability that nav_calendar will be selected.",
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


class MailsPageConfig(ProbabilisticStateConfig):
    """The mails page states configuration"""

    view_mail: float = Field(
        0.45,
        description="The base propability that view mail will be selected.",
    )

    new_mail: float = Field(
        0.35,
        description="The base propability that new mail will be selected.",
    )

    refresh_mail: float = Field(
        0.1,
        description="The base propability that refresh mail will be selected.",
    )

    return_: float = Field(
        0.1,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(return_increase=1.2),
        description="Extra configuration for the state",
    )


class MailViewConfig(ProbabilisticStateConfig):
    """The mail view states configuration"""

    delete_mail: float = Field(
        0.3,
        description="The base propability that delete mail will be selected.",
    )

    open_mail: float = Field(
        0.4,
        description="The base propability that open mail will be selected.",
    )

    do_nothing: float = Field(
        0.3,
        description="The base propability that do nothing will be selected.",
    )


class MailInfoConfig(ProbabilisticStateConfig):
    """The mail info states configuration"""

    delete_mail: float = Field(
        0.3,
        description="The base propability that delete mail will be selected.",
    )

    reply_mail: float = Field(
        0.7,
        description="The base propability that reply mail will be selected.",
    )


class AdminPageConfig(ProbabilisticStateConfig):
    """The admin page states configuration"""

    nav_config: float = Field(
        0.15,
        description="The base propability that nav config will be selected.",
    )

    nav_groups: float = Field(
        0.15,
        description="The base propability that nav groups will be selected.",
    )

    nav_users: float = Field(
        0.09,
        description="The base propability that nav users will be selected.",
    )

    nav_sessions: float = Field(
        0.09,
        description="The base propability that nav sessions will be selected.",
    )

    nav_alarms: float = Field(
        0.09,
        description="The base propability that nav alarms will be selected.",
    )

    nav_locks: float = Field(
        0.09,
        description="The base propability that nav locks will be selected.",
    )

    nav_permissions: float = Field(
        0.09,
        description="The base propability that nav permissions will be selected.",
    )

    nav_php_shell: float = Field(
        0.05,
        description="The base propability that nav php shell will be selected.",
    )

    nav_sql_shell: float = Field(
        0.05,
        description="The base propability that nav sql shell will be selected.",
    )

    nav_cli_shell: float = Field(
        0.05,
        description="The base propability that nav cli shell will be selected.",
    )

    return_: float = Field(
        0.1,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(return_increase=2),
        description="Extra configuration for the state",
    )


class AdminGroupsPageConfig(ProbabilisticStateConfig):
    """The admin groups pages states configuration"""

    group_add: float = Field(
        0.45,
        description="The base propability that group add will be selected.",
    )

    group_delete: float = Field(
        0.25,
        description="The base propability that groupe delete will be selected.",
    )

    return_: float = Field(
        0.3,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(return_increase=2),
        description="Extra configuration for the state",
    )


class NotesPageConfig(ProbabilisticStateConfig):
    """The notes page states configuration"""

    new_note: float = Field(
        0.5,
        description="The base propability that new note will be selected.",
    )

    edit_note: float = Field(
        0.4,
        description="The base propability that edit note will be selected.",
    )

    return_: float = Field(
        0.1,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(return_increase=2),
        description="Extra configuration for the state",
    )


class NoteEditorConfig(ProbabilisticStateConfig):
    """The note editor states configuration"""

    write_note: float = Field(
        0.6,
        description="The base propability that write note will be selected.",
    )

    delete_note: float = Field(
        0.4,
        description="The base propability that delete note will be selected.",
    )


class TasksPageConfig(ProbabilisticStateConfig):
    """The tasks page states configuration"""

    new_task: float = Field(
        0.5,
        description="The base propability that new task will be selected.",
    )

    edit_task: float = Field(
        0.4,
        description="The base propability that edit task will be selected.",
    )

    return_: float = Field(
        0.1,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(return_increase=1.4),
        description="Extra configuration for the state",
    )


class AddressBookPageConfig(ProbabilisticStateConfig):
    """The address book page states configuration"""

    new_contact: float = Field(
        0.2,
        description="The base propability that new contact will be selected.",
    )

    browse_contacts: float = Field(
        0.675,
        description="The base propability that browse contacts will be selected.",
    )

    return_: float = Field(
        0.125,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(return_increase=1.4),
        description="Extra configuration for the state",
    )


class ContactsBrowserConfig(ProbabilisticStateConfig):
    """The contacts browser states configuration"""

    new_contact: float = Field(
        0.35,
        description="The base propability that new contact will be selected.",
    )

    view_contact: float = Field(
        0.65,
        description="The base propability that view contact will be selected.",
    )


class ContactInfoConfig(ProbabilisticStateConfig):
    """The contact info  states configuration"""

    delete_contact: float = Field(
        0.4,
        description="The base propability that delete contact will be selected.",
    )

    do_nothing: float = Field(
        0.6,
        description="The base propability that do nothing will be selected.",
    )


class CalendarPageConfig(ProbabilisticStateConfig):
    """The calendar page  states configuration"""

    new_event: float = Field(
        0.4,
        description="The base propability that new event will be selected.",
    )

    edit_event: float = Field(
        0.35,
        description="The base propability that edit event will be selected.",
    )

    return_: float = Field(
        0.25,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(return_increase=2),
        description="Extra configuration for the state",
    )


class EventEditConfig(ProbabilisticStateConfig):
    """The event edit  states configuration"""

    write_event: float = Field(
        0.6,
        description="The base propability that write event will be selected.",
    )

    delete_event: float = Field(
        0.4,
        description="The base propability that delete event will be selected.",
    )


class HordeStates(BaseModel):
    """Configuration class for all horde activity states."""

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

    mails_page: MailsPageConfig = Field(
        MailsPageConfig(),
        description="The mails page states config",
    )

    mail_view: MailViewConfig = Field(
        MailViewConfig(),
        description="The mail view states config",
    )

    mail_info: MailInfoConfig = Field(
        MailInfoConfig(),
        description="The mail info states config",
    )

    admin_page: AdminPageConfig = Field(
        AdminPageConfig(),
        description="The admin page states config",
    )

    admin_groups_page: AdminGroupsPageConfig = Field(
        AdminGroupsPageConfig(),
        description="The admin groups page states config",
    )

    notes_page: NotesPageConfig = Field(
        NotesPageConfig(),
        description="The notes page states config",
    )

    note_editor: NoteEditorConfig = Field(
        NoteEditorConfig(),
        description="The note editor states config",
    )

    tasks_page: TasksPageConfig = Field(
        TasksPageConfig(),
        description="The tasks page states config",
    )

    address_book_page: AddressBookPageConfig = Field(
        AddressBookPageConfig(),
        description="The address book page states config",
    )

    contacts_browser: ContactsBrowserConfig = Field(
        ContactsBrowserConfig(),
        description="The contacts browser states config",
    )

    contact_info: ContactInfoConfig = Field(
        ContactInfoConfig(),
        description="The contact info states config",
    )

    calendar_page: CalendarPageConfig = Field(
        CalendarPageConfig(),
        description="The calendar page states config",
    )

    event_edit: EventEditConfig = Field(
        EventEditConfig(),
        description="The event edit states config",
    )


class HordeUserStates(HordeStates):
    """Configuration class for the horde state machine states"""

    selecting_activity: ActivitySelectionConfig = Field(
        ActivitySelectionConfig(),
        description="The selecting activity states config",
    )


class HordeMailConfig(BaseModel):
    """Configuration class for the horde users mail activities"""

    contacts: Dict[EmailStr, float] = Field(
        {},
        description="The email contacts for the horde user",
    )

    attachments: Dict[FilePath, float] = Field(
        {},
        description="A dict of attachment files the user might send",
    )

    extra_recipient: float = Field(
        0.1,
        description="The propability that an additional recipient is added to a mail",
    )

    max_recipients: int = Field(
        3,
        description="The maximum amount of recipients",
    )

    attachment: float = Field(
        0.2,
        description="The propability that an attachment is added to a new email",
    )

    attachment_reply: float = Field(
        0.1,
        description="The propability that an attachment is added to a reply",
    )

    # validators
    _validate_recipient = validator("extra_recipient", allow_reuse=True)(
        positive_smaller_one
    )
    _validate_attachment = validator("attachment", allow_reuse=True)(
        positive_smaller_one
    )
    _validate_attachment_reply = validator("attachment_reply", allow_reuse=True)(
        positive_smaller_one
    )


class HordeConfig(BaseModel):
    """Configuration class for the horde user"""

    url: HttpUrl = Field(
        "http://localhost",
        description="The horde servers base URL",
    )

    first_name: str = Field(
        "Max",
        description="The firstname of the horde user",
    )

    last_name: str = Field(
        "Mustermann",
        description="The lastname of the horde user",
    )

    username: str = Field(
        "user",
        description="The horde user",
    )

    password: str = Field(
        "password",
        description="The horde users password",
    )

    max_daily: int = Field(
        10,
        description="The maximum amount of times the horde activity will be entered per day",
    )

    mail: HordeMailConfig = Field(
        HordeMailConfig(),
        description="The mail configuration for the horde user",
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

    states: HordeUserStates = Field(
        HordeUserStates(),
        description="The horde state machines states configuration",
    )

    horde: HordeConfig = Field(
        HordeConfig(),
        description="The horde user specific configuration",
    )
