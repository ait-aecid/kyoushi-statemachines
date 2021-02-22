import re
import subprocess

from multiprocessing import Process
from signal import SIGINT
from typing import (
    List,
    Optional,
    Pattern,
)

from pydantic import FilePath
from structlog.stdlib import BoundLogger

from .context import Context


#     path = '/home/user/Download/trustedzone.ovpn'
#     with open("/home/user/Download/trustedzone.ovpn", "a") as myfile:
#         myfile.write('\nscript-security 2\nup /etc/openvpn/update-resolv-conf\ndown /etc/openvpn/update-resolv-conf')
#         myfile.close()
# x = subprocess.Popen(['sudo', 'openvpn', '--auth-nocache', '--config', path])
#     try:
#         while True:
#             time.sleep(600)
#     # termination with Ctrl+C
#     except:
#         try:
#             x.kill()
#         except:
#             pass
#         while x.poll() != 0:
#             time.sleep(1)


def wait_process_output(
    log: BoundLogger,
    process: subprocess.Popen[bytes],
    wait_regex: Pattern,
):
    line = ""
    while (
        # the vpn process is alive
        process.poll() is None
        # and we have output
        and process.stdout is not None
        # and connected print was not yet reached
        and not wait_regex.match(line)
    ):
        line = process.stdout.readline().decode("utf-8")
        log.info("VPN init", stdout=line)


class VPNConnect:
    def __init__(
        self,
        config: FilePath,
        wait_regex: Pattern = re.compile("^.* Initialization Sequence Completed$"),
        timeout: float = 120,
    ):
        self.vpn_cmd: List[str] = [
            "sudo",
            "openvpn",
            "--config",
            str(config.absolute()),
        ]
        self.wait_regex: Pattern = wait_regex
        self.timeout: float = timeout

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        # bind cmd to log context
        log = log.bind(vpn_cmd=self.vpn_cmd)

        log.info("Connecting to VPN")
        context.vpn_process = subprocess.Popen(self.vpn_cmd, stdout=subprocess.PIPE)

        wait_process = Process(
            target=wait_process_output,
            name="wait_connected",
            args=(context.vpn_process, self.wait_regex),
        )

        timed_out = False
        try:
            wait_process.join(self.timeout)
        except TimeoutError:
            timed_out = True

        # need to check if process is still running here
        if context.vpn_process.poll is None and not timed_out:
            log.info("Connected to VPN")
        else:
            log.error("Failed to connect to VPN")
            raise Exception("VPN Connection error")


def vpn_disconnect(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    vpn_process = context.vpn_process
    if vpn_process is not None and vpn_process.poll() is None:
        log.info("Disconnecting from VPN")
        vpn_process.send_signal(SIGINT)
        wait_process_output(log, vpn_process, re.compile("process exiting"))
        log.info("Disconnected from VPN")
    else:
        log.info("VPN process not running")
