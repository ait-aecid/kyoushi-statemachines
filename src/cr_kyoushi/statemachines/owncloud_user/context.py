"""The owncloud user activities context model classes"""

import sys

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


class UploadInfo(BaseInfo):
    directory: Optional[str] = Field(
        None,
        description="The upload target directory",
    )

    source: Optional[str] = Field(
        None,
        description="The upload source directory",
    )

    name: Optional[str] = Field(
        None,
        description="The upload files name",
    )

    keep_new: Optional[bool] = Field(
        None,
        description="If incase of replace the new file is kept or not",
    )

    keep_old: Optional[bool] = Field(
        None,
        description="If incase of replace the old file is kept or not",
    )


class OwncloudContext(BaseModel):
    upload: UploadInfo = Field(
        UploadInfo(),
        description="The file upload context information",
    )

    file: FileInfo = Field(
        FileInfo(),
        description="The file beeing viewed",
    )


class Context(SeleniumContext, Protocol):
    """Owncloud user state machine context protocol"""

    owncloud: OwncloudContext
    """The owncloud user context"""


class ContextModel(SeleniumContextModel):
    """Owncloud user state machine context class"""

    owncloud: OwncloudContext = Field(
        OwncloudContext(),
        description="The owncloud user context",
    )
