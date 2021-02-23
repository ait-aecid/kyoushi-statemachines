"""The wordpress wordpress editor activities context model classes"""
import sys

from typing import (
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)

from ..core.model import BaseInfo
from ..core.selenium import (
    SeleniumContext,
    SeleniumContextModel,
)


if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class WordpressPostInfo(BaseInfo):
    title: Optional[str] = Field(
        None,
        description="The post title",
    )

    content: Optional[List[str]] = Field(
        None,
        description="The post content as a list of paragraphs",
    )


class WordpressCommentReplyInfo(BaseInfo):
    cid: Optional[str] = Field(
        None,
        description="The id of the comment that is being replied to",
    )

    pid: Optional[str] = Field(
        None,
        description="The if of post the comment was posted on",
    )

    content: Optional[str] = Field(
        None,
        description="The reply content",
    )


class WordpressEditorContext(BaseModel):

    username: str = Field(
        "mmustermann",
        description="The editors username",
    )

    password: str = Field(
        "passwd123",
        description="The editors password",
    )

    post: WordpressPostInfo = Field(
        WordpressPostInfo(),
        description="The post that is being created",
    )

    comment_reply: WordpressCommentReplyInfo = Field(
        WordpressCommentReplyInfo(),
        description="The reply that is being created",
    )


class Context(SeleniumContext, Protocol):
    """Wordpress wordpress editor state machine context class"""

    wp_editor: WordpressEditorContext = Field(
        WordpressEditorContext(),
        description="The wordpress editor activity context",
    )


class ContextModel(SeleniumContextModel):
    """Wordpress wordpress editor state machine context class"""

    wp_editor: WordpressEditorContext = Field(
        WordpressEditorContext(),
        description="The wordpress editor activity context",
    )
