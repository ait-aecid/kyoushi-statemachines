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

from .context import Context


def wait_process_output(
    log: BoundLogger,
    process: subprocess.Popen,
    wait_regex: Pattern,
):
    line = ""
    while (
        # we have output
        process.stdout is not None
        # and connected print was not yet reached
        and not wait_regex.match(line)
    ):
        line = process.stdout.readline().decode("utf-8")
        if len(line) > 0:
            log.info("VPN init", stdout=line)
        sleep(0.1)


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
        context: Context,
        target: Optional[str],
    ):
        if context.vpn_process is None or context.vpn_process.poll() is not None:
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
            if context.vpn_process.poll() is None and not timed_out:
                log.info("Connected to VPN")
            else:
                log.error("Failed to connect to VPN")
                raise Exception("VPN Connection error")
        else:
            log.info("Already connected to VPN")


def vpn_disconnect(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    vpn_process = context.vpn_process
    if vpn_process is not None and vpn_process.poll() is None:
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
    else:
        log.info("VPN process not running")
