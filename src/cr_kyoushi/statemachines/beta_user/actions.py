import os
import re
import subprocess

from multiprocessing import Process
from time import sleep
from typing import (
    List,
    Optional,
    Pattern,
)

from pydantic import FilePath
from structlog.stdlib import BoundLogger

from .context import VPNContext


def wait_process_output(
    log: BoundLogger,
    process: subprocess.Popen,
    wait_regex: Pattern,
):
    """Waits for the process to output a line matching the given regex.

    Args:
        log: The logger instance
        process: The process to check on
        wait_regex: The regex to check
    """
    line = ""
    while (
        # we have output
        process.stdout is not None
        # and connected print was not yet reached
        and not wait_regex.match(line)
    ):
        line = process.stdout.readline().decode("utf-8")
        if len(line) > 0:
            log.info("VPN output", stdout=line)
        sleep(0.1)


class VPNConnect:
    """Connects to an OpenVPN server using an OpenVPN config.

    !!! Warning
        This transition function assumes that the user execute the openvpn
        command with sudo without password prompt!
    """

    def __init__(
        self,
        config: FilePath,
        wait_regex: Pattern = re.compile("^.* Initialization Sequence Completed$"),
        timeout: float = 120,
    ):
        """
        Args:
            config: The OpenVPN config file to use
            wait_regex: Regex matching the OpenVPN connected output line
            timeout: The maximum time to wait for the VPN to connect
        """
        self.vpn_cmd: List[str] = [
            "sudo",
            "openvpn",
            "--auth-nocache",
            "--config",
            str(config.absolute()),
        ]
        self.wait_regex: Pattern = wait_regex
        self.timeout: float = timeout

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: VPNContext,
        target: Optional[str],
    ):
        if context.vpn_process is None:
            # bind cmd to log context
            log = log.bind(vpn_cmd=self.vpn_cmd)

            log.info("Connecting to VPN")
            context.vpn_process = subprocess.Popen(
                self.vpn_cmd, stdout=subprocess.PIPE, preexec_fn=os.setpgrp
            )

            wait_process = Process(
                target=wait_process_output,
                name="wait_connected",
                args=(log, context.vpn_process, self.wait_regex),
            )
            wait_process.start()

            timed_out = False
            try:
                wait_process.join(self.timeout)
            except TimeoutError:
                timed_out = True

            # need to check if process is still running here
            if not timed_out:
                log.info("Connected to VPN")
            else:
                log.error("Failed to connect to VPN")
                context.vpn_process = None
                raise Exception("VPN Connection error")
        else:
            log.info("Already connected to VPN")


def vpn_disconnect(
    log: BoundLogger,
    current_state: str,
    context: VPNContext,
    target: Optional[str],
):
    """Shutsdown the OpenVPN connection

    Args:
        log: The logger instance
        current_state: The current state
        context: The sm context
        target: The target state
    """
    vpn_process = context.vpn_process
    if vpn_process is not None:
        pgid = os.getpgid(vpn_process.pid)
        log.info("Disconnecting from VPN")
        # cant use send signal since we started with sudo
        subprocess.check_output(["sudo", "kill", str(pgid)])

        wait_process = Process(
            target=wait_process_output,
            name="wait_disconnected",
            args=(log, context.vpn_process, re.compile(".*process exiting.*")),
        )
        wait_process.start()

        timed_out = False
        try:
            wait_process.join(120)
        except TimeoutError:
            timed_out = True

        if not timed_out:
            log.info("Disconnected from VPN")
        else:
            log.error("Failed to disconnect from VPN")
        context.vpn_process = None
    else:
        log.info("VPN process not running")
