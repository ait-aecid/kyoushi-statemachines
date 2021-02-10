"""The owncloud user activities context model classes"""


from typing import Optional

from faker import Faker
from pydantic import (
    BaseModel,
    Field,
)
from selenium import webdriver

from ..core.model import BaseInfo


class FileInfo(BaseInfo):
    fid: Optional[str] = Field(
        None,
        description="The file id",
    )

    file_type: Optional[str] = Field(
        None,
        description="The files type",
    )

    size: Optional[int] = Field(
        None,
        description="The files size",
    )

    name: Optional[str] = Field(
        None,
        description="The files name",
    )

    path: Optional[str] = Field(
        None,
        description="The files path",
    )

    mime: Optional[str] = Field(
        None,
        description="The files mime type",
    )

    mtime: Optional[int] = Field(
        None,
        description="The files modification time as epoch int",
    )

    etag: Optional[str] = Field(
        None,
        description="The files etag",
    )

    permissions: Optional[int] = Field(
        None,
        description="The users permissions for this file",
    )

    share_permissions: Optional[int] = Field(
        None,
        description="The users share permissions for this file",
    )


class Context(BaseModel):
    """Owncloud user state machine context class"""

    driver: webdriver.Remote
    """The selenium web driver"""

    main_window: str = Field(
        ...,
        description="The main window of the webdriver",
    )

    fake: Faker
    """Faker instance to use for generating various random content"""

    class Config:
        arbitrary_types_allowed = True
