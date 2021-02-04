"""The wordpress wordpress editor activities context model classes"""


from typing import (
    List,
    Optional,
)

from faker import Faker
from pydantic import (
    BaseModel,
    Field,
)
from selenium import webdriver

from ..core.model import BaseInfo


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
    author: str = Field(
        "Max Mustermann",
        description="The editors name",
    )

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


class Context(BaseModel):
    """Wordpress wordpress editor state machine context class"""

    driver: webdriver.Remote
    """The selenium web driver"""

    main_window: str = Field(
        ...,
        description="The main window of the webdriver",
    )

    fake: Faker
    """Faker instance to use for generating various random content"""

    wp_editor: WordpressEditorContext = Field(
        WordpressEditorContext(),
        description="The wordpress editor activity context",
    )

    class Config:
        arbitrary_types_allowed = True
