import random
import re

from typing import (
    Dict,
    List,
    Optional,
)

import numpy as np

from pwnlib.tubes.process import (
    PTY,
    process,
)
from pwnlib.tubes.ssh import ssh_channel
from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation.util import sleep

from .config import Host
from .context import Context
from .expect import (
    RECEIVE_PATTERN,
    SSH_CONNECTION_REGEX,
    SSH_PASSWORD_REGEX,
    SUDO_FAIL_BOTH_REGEX,
    SUDO_FAIL_REGEX,
    SUDO_REGEX,
)


def _receive(
    log: BoundLogger,
    shell: ssh_channel,
    regex: re.Pattern = RECEIVE_PATTERN,
) -> List[str]:
    output = ""
    while not regex.search(output):
        output_part = shell.recvS()
        output += output_part
        if len(output_part) > 0:
            log.debug("Received shell output part", output_part=output_part.split("\n"))

    outlines = output.split("\n")
    log.info("Received shell output", outlines=outlines)

    return outlines


class SelectHost:
    def __init__(self, propabilities: Dict[str, float], configs: Dict[str, Host]):
        self.probs: Dict[str, float] = propabilities
        self.configs: Dict[str, Host] = configs

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        if len(self.probs) > 0:
            user = context.ssh_user
            host_id = np.random.choice(
                a=list(self.probs.keys()),
                p=list(self.probs.values()),
            )
            user.host = self.configs[host_id]
            user.commands = []
            log.info("Selected SSH host", ssh_host=user.host)
        else:
            log.error("No hosts configured")


def connect(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    user = context.ssh_user
    host = context.ssh_user.host

    # bind log context
    log = log.bind(ssh_host=host)

    if host is not None:
        host_string = f"{host.username}@{host.host}"

        ssh_args = ["ssh"]

        # build proxy command
        if host.proxy_host is not None:
            assert host.proxy_ssh_key is not None
            assert host.proxy_username is not None
            proxy_key = str(host.proxy_ssh_key.absolute())
            proxy_command = (
                f"ssh -o StrictHostKeyChecking={'yes' if host.proxy_verify_host else 'no'} "
                f"-i {proxy_key} -W %h:%p "
                f"-p {host.proxy_port} {host.proxy_username}@{host.proxy_host}"
            )
            ssh_args.extend(["-o", f"ProxyCommand='{proxy_command}'"])

        if host.force_password:
            ssh_args.extend(["-o", "PreferredAuthentications=password"])

        if host.ssh_key is not None:
            ssh_args.extend(
                ["-o", "IdentitiesOnly=yes", "-i", str(host.ssh_key.absolute())]
            )

        if host.verify_host:
            ssh_args.extend(["-o", "StrictHostKeyChecking=accept-new"])
        else:
            ssh_args.extend(["-o", "StrictHostKeyChecking=no"])

        ssh_args.extend(["-p", str(host.port), host_string])

        log = log.bind(ssh_args=ssh_args)

        log.info("Connecting to SSH host")

        try:
            user.shell = process(
                argv=" ".join(ssh_args),
                shell=True,
                stdin=PTY,
            )
            output = _receive(log, user.shell, SSH_CONNECTION_REGEX)

            # if we got a password prompt
            # then enter password till we succeed
            # if we don't succeed the ssh program will end
            # and our receive will throw EOF
            while SSH_PASSWORD_REGEX.search(output[-1]):
                log.info("Entering SSH password")
                user.shell.sendline(host.password)
                output = _receive(log, user.shell, SSH_CONNECTION_REGEX)
                log.info("Entered SSH password")

            log.info("Connected to SSH host")
        except EOFError:
            log.error("Failed to connect to SSH host")

    else:
        log.error("Target host not configured")


def disconnect(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    user = context.ssh_user

    # bind log context
    log = log.bind(ssh_host=user.host)

    if user.shell is not None:
        log.info("Disconnecting from SSH Host")
        user.shell.sendline("exit")
        user.shell.close()
        log.info("Disconnected from SSH Host")

        # shell remove context
        user.shell = None
    else:
        log.error(
            "Invalid action for current state",
            ssh_action="disconnect",
        )


def _finish_command(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    user = context.ssh_user
    command = user.commands[0]

    log.info("Executed command")
    # "pop" the current command from the command chain list
    # (this only changes our view of the underlying list)
    user.commands = user.commands[1:]

    if command.idle_after is not None:
        log.info("Idle after command execution")
        sleep(user.idle_config.get(command.idle_after))
        log.info("Idled after command execution")


def select_chain(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    user = context.ssh_user
    host = user.host

    # bind log context
    log = log.bind(ssh_host=user.host)

    if host is not None:
        user.commands = random.choice(host.commands)
        user.output = []
        log.info("Selected command chain", commands=user.commands)
    else:
        log.error(
            "Invalid action for current state",
            ssh_action="select_chain",
        )


def execute_command(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    user = context.ssh_user

    # bind log context
    log = log.bind(ssh_host=user.host)

    if user.shell is not None:
        if len(user.commands) > 0:
            # reset output lines context
            user.output = []

            command = user.commands[0]
            log = log.bind(command=command)

            # chdir before executing command
            if command.chdir is not None:
                log.info("Changing directory")
                user.shell.sendline(f"cd {command.chdir}")
                _receive(log, user.shell)
                log.info("Changed directory")

            cmd = command.cmd
            expect = command.expect

            if command.sudo:
                # configure special expect for sudo
                expect = re.compile(f"({SUDO_REGEX.pattern})|({expect.pattern})")

                # configure sudo command
                sudo = "sudo"
                if command.sudo_user is not None:
                    sudo = f"{sudo} -u {command.sudo_user}"
                cmd = f"{sudo} {cmd}"

            log.info("Executing command")

            user.shell.sendline(cmd)
            user.output = _receive(log, user.shell, expect)

            # for sudo commands we have to check if
            # to check if the password prompt is present
            # if so then they are not executed yet
            if not command.sudo or not SUDO_REGEX.search(user.output[-1]):
                _finish_command(log, current_state, context, target)
        else:
            log.warn("No command to execute")

    else:
        log.error(
            "Invalid action for current state",
            ssh_action="disconnect",
        )


def enter_sudo_password(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    user = context.ssh_user
    command = user.commands[0]

    # bind log context
    log = log.bind(ssh_host=user.host, command=command)

    if (
        # ensure we have a shell
        user.shell is not None
        # on a host
        and user.host is not None
        # and output from the current command
        and user.output is not None
        and len(user.output) > 0
    ):
        if SUDO_REGEX.search(user.output[-1]):
            log.info("Entering sudo password")
            user.shell.sendline(user.host.password)
            log.info("Entered sudo password")

            # wait for command results
            user.output += _receive(log, user.shell, command.expect)
            _finish_command(log, current_state, context, target)
        else:
            log.info("Sudo password was not required")

    else:
        log.error(
            "Invalid action for current state",
            ssh_action="enter_sudo_password",
        )


def fail_sudo(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    user = context.ssh_user
    command = user.commands[0]

    # bind log context
    log = log.bind(ssh_host=user.host, command=command)

    if (
        # ensure we have a shell
        user.shell is not None
        # on a host
        and user.host is not None
        # and output from the current command
        and user.output is not None
        and len(user.output) > 0
        # and we are currently on the sudo prompt
        and SUDO_REGEX.search(user.output[-1])
    ):
        password: str
        # ensure we generate a random password
        # that is not the actual password
        while True:
            password = context.fake.password()
            if password != user.host.password:
                break
        log = log.bind(fail_password=password)

        log.info("Entering incorrect sudo password")
        user.shell.sendline(password)
        output = _receive(log, user.shell, SUDO_FAIL_BOTH_REGEX)
        log.info("Entered incorrect sudo password")

        # add output from this try to overall cmd output
        user.output.extend(output)

        # if we got the error message then we
        # failed sudo escalation
        if SUDO_FAIL_REGEX.search("\r\n".join(output)):
            log.info("Failed sudo escalation")

            if not RECEIVE_PATTERN.search(output[-1]):
                # finally we retrieve the normal bash prompt
                # if we did not do so already
                _receive(log, user.shell)
    else:
        log.error(
            "Invalid action for current state",
            ssh_action="fail_sudo",
        )
