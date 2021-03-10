"""The owncloud user activities context model classes"""

import sys

from subprocess import Popen
from typing import Optional

from ..horde_user.context import Context as HordeContext
from ..horde_user.context import ContextModel as HordeContextModel
from ..owncloud_user.context import Context as OwncloudContext
from ..owncloud_user.context import ContextModel as OwncloudContextModel
from ..ssh_user.context import Context as SSHContext
from ..ssh_user.context import ContextModel as SSHContextModel
from ..web_browser.config import Context as BrowserContext
from ..web_browser.config import ContextModel as BrowserContextModel
from ..wordpress_editor.context import Context as WPEditorContext
from ..wordpress_editor.context import ContextModel as WPEditorContextModel
from ..wordpress_wpdiscuz.context import Context as WPDiscuzContext
from ..wordpress_wpdiscuz.context import ContextModel as WPDiscuzContextModel


if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class VPNContext(Protocol):
    """VPN connection context"""

    vpn_process: Optional[Popen]
    """The VPN process for remote users"""


class Context(
    HordeContext,
    OwncloudContext,
    SSHContext,
    BrowserContext,
    WPEditorContext,
    WPDiscuzContext,
    VPNContext,
    Protocol,
):
    """Beta user state machine context protocol"""


class ContextModel(
    HordeContextModel,
    OwncloudContextModel,
    SSHContextModel,
    BrowserContextModel,
    WPEditorContextModel,
    WPDiscuzContextModel,
):
    """Beta user state machine context class"""

    vpn_process: Optional[Popen]
    """The VPN process for remote users"""
