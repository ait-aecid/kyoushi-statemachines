"""The wordpress wpdiscuz activities context model classes"""

from datetime import datetime
from typing import Optional

from faker import Faker
from pydantic import (
    BaseModel,
    Field,
)
from selenium import webdriver

from ..core.model import BaseInfo


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


class Context(BaseModel):
    """Wordpress wpDisuz state machine context class"""

    driver: webdriver.Remote
    """The selenium web driver"""

    main_window: str = Field(
        ...,
        description="The main window of the webdriver",
    )

    fake: Faker
    """Faker instance to use for generating various random content"""

    wpdiscuz: WpDiscuzContext = Field(
        WpDiscuzContext(),
        description="The wpdiscuz activity context",
    )

    class Config:
        arbitrary_types_allowed = True
