"""The wordpress wpdiscuz activities context model classes"""

import sys

from datetime import datetime
from typing import Optional

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


class PostInfo(BaseInfo):
    pid: Optional[str] = Field(
        None,
        description="The id of the post being viewed",
    )

    title: Optional[str] = Field(
        None,
        description="The title of the post being viewed",
    )

    author: Optional[str] = Field(
        None,
        description="The author of the post being viewed",
    )

    publish_date: Optional[datetime] = Field(
        None,
        description="The post datetime of the post being viewed",
    )

    link: Optional[str] = Field(
        None,
        description="The link for the post being viewed",
    )

    rating: Optional[int] = Field(
        None,
        description="The rating the beeing assigned to the post",
    )


class CommentInfo(BaseInfo):
    parent_cid: Optional[str] = Field(
        None,
        description="The comments parent id",
    )

    cid: Optional[str] = Field(
        None,
        description="The comments id",
    )

    author: Optional[str] = Field(
        None,
        description="The comment author",
    )

    email: Optional[str] = Field(
        None,
        description="The email of the comment author",
    )

    text: Optional[str] = Field(
        None,
        description="The comment text",
    )

    up_vote: Optional[bool] = Field(
        None,
        description="If a vote is a up vote or a down vote",
    )


class WpDiscuzContext(BaseModel):
    author: str = Field(
        "Max Mustermann",
        description="The wpdiscuz comment author",
    )

    email: str = Field(
        "max.mustermann@localhost.local",
        description="The wpdiscuz comment authors email",
    )

    posts_page: int = Field(
        1,
        description="The current posts page number",
    )

    post: PostInfo = Field(
        PostInfo(),
        description="The currently viewed post",
    )

    comment: CommentInfo = Field(
        CommentInfo(),
        description="The comment that is being voted on or replied to",
    )


class Context(SeleniumContext, Protocol):
    """Wordpress wpDisuz state machine context protocol"""

    wpdiscuz: WpDiscuzContext
    """The wpdiscuz activity context"""


class ContextModel(SeleniumContextModel):
    """Wordpress wpDisuz state machine context class"""

    wpdiscuz: WpDiscuzContext = Field(
        WpDiscuzContext(),
        description="The wpdiscuz activity context",
    )
