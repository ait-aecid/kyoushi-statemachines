from datetime import datetime
from enum import Enum
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from faker import Faker
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    FilePath,
    HttpUrl,
    validator,
)
from selenium import webdriver

from cr_kyoushi.simulation.model import (
    ApproximateFloat,
    WorkSchedule,
)

from ..core.config import (
    IdleConfig,
    ProbabilisticStateConfig,
)
from ..core.selenium import SeleniumConfig


__all__ = [
    "StatemachineConfig",
    "Context",
]


def positive_smaller_one(v: float) -> float:
    if v > 1 or v < 0:
        raise ValueError("must be 0 <= f <= 1!")
    return v


def greater_equal_one(v: float) -> float:
    if v < 1:
        raise ValueError("must be >= 1!")
    return v


class ActivityExtraConfig(BaseModel):
    return_increase: float = Field(
        1.25,
        description=(
            "The multiplicative factor the return transitions weight "
            "should be increased each time it is not selected."
        ),
    )

    _validate_increase = validator("return_increase", allow_reuse=True)(
        greater_equal_one
    )


class ActivitySelectionConfig(ProbabilisticStateConfig):
    horde: float = Field(
        0.6,
        description="The base propability that horde will be selected.",
    )

    idle: float = Field(
        0.4,
        description="The base propability that idle will be selected.",
    )


class LoginPageConfig(BaseModel):
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
    logout_chance: float = Field(
        0.05,
        description="The chance the user will logout when stopping the horde activity",
    )


class SelectingMenuConfig(ProbabilisticStateConfig):
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
    delete_mail: float = Field(
        0.3,
        description="The base propability that delete mail will be selected.",
    )

    reply_mail: float = Field(
        0.7,
        description="The base propability that reply mail will be selected.",
    )


class AdminPageConfig(ProbabilisticStateConfig):
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
    group_add: float = Field(
        0.45,
        description="The base propability that group add will be selected.",
    )

    group_delete: float = Field(
        0.35,
        description="The base propability that groupe delete will be selected.",
    )

    return_: float = Field(
        0.2,
        description="The base propability that the activity will be left.",
        alias="return",
    )

    extra: ActivityExtraConfig = Field(
        ActivityExtraConfig(return_increase=2),
        description="Extra configuration for the state",
    )


class NotesPageConfig(ProbabilisticStateConfig):
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
    write_note: float = Field(
        0.6,
        description="The base propability that write note will be selected.",
    )

    delete_note: float = Field(
        0.4,
        description="The base propability that delete note will be selected.",
    )


class TasksPageConfig(ProbabilisticStateConfig):
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
    new_contact: float = Field(
        0.35,
        description="The base propability that new contact will be selected.",
    )

    view_contact: float = Field(
        0.65,
        description="The base propability that view contact will be selected.",
    )


class ContactInfoConfig(ProbabilisticStateConfig):
    delete_contact: float = Field(
        0.4,
        description="The base propability that delete contact will be selected.",
    )

    do_nothing: float = Field(
        0.6,
        description="The base propability that do nothing will be selected.",
    )


class CalendarPageConfig(ProbabilisticStateConfig):
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
    write_event: float = Field(
        0.6,
        description="The base propability that write event will be selected.",
    )

    delete_event: float = Field(
        0.4,
        description="The base propability that delete event will be selected.",
    )


class HordeStates(BaseModel):
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
    selecting_activity: ActivitySelectionConfig = Field(
        ActivitySelectionConfig(),
        description="The selecting activity states config",
    )


class HordeConfig(BaseModel):
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

    contacts: Dict[EmailStr, float] = Field(
        {},
        description="The email contacts for the horde user",
    )

    attachments: Dict[FilePath, float] = Field(
        {},
        description="A dict of attachment files the user might send",
    )

    max_daily: int = Field(
        10,
        description="The maximum amount of times the horde activity will be entered per day",
    )


class StatemachineConfig(BaseModel):
    """Web browser state machine configuration model

    Example:
        ```yaml
        max_error: 0
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

    max_errors: int = Field(
        0,
        description="The maximum amount of times to try to recover from an error",
    )

    start_time: Optional[datetime] = Field(
        None,
        description="The state machines start time",
    )

    end_time: Optional[datetime] = Field(
        None,
        description="The state machines end time",
    )

    idle: IdleConfig = Field(
        IdleConfig(),
        description="The idle configuration for the state machine",
    )

    schedule: Optional[WorkSchedule] = Field(
        None,
        description="The work schedule for the web browser user",
    )

    selenium: SeleniumConfig = Field(
        SeleniumConfig(),
        description="Selenium configuration for the web browser user",
    )

    states: HordeUserStates = Field(
        HordeUserStates(),
        description="The horde state machines states configuration",
    )

    horde: HordeConfig = Field(
        HordeConfig(),
        description="The horde user specific configuration",
    )


class BaseInfo(BaseModel):
    def clear(self):
        """Resets the info object to its initial state.

        i.e., all fields are `None`
        """
        for field in self.__fields__:
            self.__setattr__(field, None)


class MailSendType(str, Enum):
    NEW = "new"
    REPLY = "reply"
    FORWARD = "forward"


class MailInfo(BaseInfo):
    send_type: Optional[MailSendType] = Field(
        None,
        description="The mail send type that is being composed for",
    )

    buid: Optional[int] = Field(
        None,
        description="The mail id that is being viewed/replied to",
    )

    mailbox: Optional[str] = Field(
        None,
        description="The mailbox id of the message that is being viewed/replied to",
    )

    recipients: Optional[List[str]] = Field(
        None,
        description="The mail recipients",
    )

    subject: Optional[str] = Field(
        None,
        description="The mail subject line",
    )

    content: Optional[str] = Field(
        None,
        description="The mail content",
    )

    attachment: Optional[FilePath] = Field(
        None,
        description="The source path of the mail attachment",
    )


class CalendarEventInfo(BaseInfo):
    id: Optional[str] = Field(
        None,
        description="The event id",
    )

    calendar: Optional[str] = Field(
        None,
        description="The calendar id",
    )

    start: Optional[datetime] = Field(
        None,
        description="The event start date and time",
    )

    end: Optional[datetime] = Field(
        None,
        description="The event end date and time",
    )

    title: Optional[str] = Field(
        None,
        description="The event title",
    )

    description: Optional[List[str]] = Field(
        None,
        description="The event description",
    )

    location: Optional[str] = Field(
        None,
        description="The event location",
    )


class GroupInfo(BaseInfo):
    gid: Optional[int] = Field(
        None,
        description="The horde group id",
    )

    name: Optional[str] = Field(
        None,
        description="The horde group name",
    )


class ContactInfo(BaseInfo):
    source: Optional[str] = Field(
        None,
        description="The contact source id",
    )

    key: Optional[str] = Field(
        None,
        description="The contact key",
    )

    name: Optional[str] = Field(
        None,
        description="The contact full name",
    )


class TaskInfo(BaseInfo):
    list_id: Optional[str] = Field(
        None,
        description="The tasklist id",
    )

    id: Optional[str] = Field(
        None,
        description="The task id",
    )

    name: Optional[str] = Field(
        None,
        description="The task name",
    )


class MemoInfo(BaseInfo):
    list_id: Optional[str] = Field(
        None,
        description="The memolist id",
    )

    target_list_id: Optional[str] = Field(
        None,
        description="The target memolist when editing a memo",
    )

    id: Optional[str] = Field(
        None,
        description="The memo id",
    )

    title: Optional[str] = Field(
        None,
        description="The memo name",
    )

    content: Optional[List[str]] = Field(
        None,
        description="The memo content",
    )

    tags: Optional[List[str]] = Field(
        None,
        description="The memos tags",
    )


class HordeContext(BaseModel):
    mail: MailInfo = Field(
        MailInfo(),
        description="The mail that is currently beeing viewed/modified",
    )

    event: CalendarEventInfo = Field(
        CalendarEventInfo(),
        description="The calendar event that is currently being modified",
    )

    group: GroupInfo = Field(
        GroupInfo(),
        description="The group that is currently being modified",
    )

    contact: ContactInfo = Field(
        ContactInfo(),
        description="The contact that is currently beeing modified",
    )

    task: TaskInfo = Field(
        TaskInfo(),
        description="The task that is currently beeing modified",
    )

    memo: MemoInfo = Field(
        MemoInfo(),
        description="The memo that is currently beeing modified",
    )

    form_field_delay: Union[float, ApproximateFloat] = Field(
        ApproximateFloat(
            min=0.5,
            max=3,
        ),
        description="The delay to use in between form fields to fill out",
    )


class Context(BaseModel):
    driver: webdriver.Remote
    """The selenium web driver"""

    main_window: str = Field(
        ...,
        description="The main window of the webdriver",
    )

    fake: Faker
    """Faker instance to use for generating various random content"""

    horde: HordeContext = Field(
        HordeContext(),
        description="The horde specific context variables",
    )

    class Config:
        arbitrary_types_allowed = True
