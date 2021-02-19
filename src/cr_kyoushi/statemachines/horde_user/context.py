"""The horde activities context model classes"""
import sys

from datetime import datetime
from enum import Enum
from typing import (
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    FilePath,
)

from cr_kyoushi.simulation.model import ApproximateFloat

from ..core.model import BaseInfo
from ..core.selenium import (
    SeleniumContext,
    SeleniumContextModel,
)


if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


__all__ = [
    "HordeContext",
    "Context",
    "BaseInfo",
    "MailSendType",
    "MailInfo",
    "CalendarEventInfo",
    "GroupInfo",
    "ContactInfo",
    "TaskInfo",
    "MemoInfo",
]


class MailSendType(str, Enum):
    """Mail send types enum"""

    NEW = "new"
    """New emails"""

    REPLY = "reply"
    """Email replies"""

    FORWARD = "forward"
    """Email forwards"""


class MailInfo(BaseInfo):
    """Info context class used to pass mail info between states"""

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
    """Info context class used to pass calendar event info between states"""

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
    """Info context class used to pass group info between states"""

    gid: Optional[int] = Field(
        None,
        description="The horde group id",
    )

    name: Optional[str] = Field(
        None,
        description="The horde group name",
    )


class ContactInfo(BaseInfo):
    """Info context class used to pass contact info between states"""

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
    """Info context class used to pass task info between states"""

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
    """Info context class used to pass memo (note) info between states"""

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
    """Horde activity specific context class containing various info fields."""

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


class Context(SeleniumContext, Protocol):
    """Horde state machine context protocol"""

    horde: HordeContext
    """The horde specific context variables"""


class ContextModel(SeleniumContextModel):
    """Horde state machine context class"""

    horde: HordeContext = Field(
        HordeContext(),
        description="The horde specific context variables",
    )
