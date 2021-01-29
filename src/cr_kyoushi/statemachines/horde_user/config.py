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
)
from selenium import webdriver

from cr_kyoushi.simulation.model import (
    ApproximateFloat,
    WorkSchedule,
)

from ..core.config import IdleConfig
from ..core.selenium import SeleniumConfig


__all__ = [
    "StatemachineConfig",
    "Context",
]


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
