"""Regex patterns used for the SSH users shell output parsing"""

import re

from typing import Pattern


RECEIVE_PATTERN: Pattern = re.compile(r".*@.*:.*\$\s+")
SUDO_REGEX: Pattern = re.compile(r"\[sudo\] password for .*:\s+")
SUDO_FAIL_REGEX: Pattern = re.compile(r"sudo: \d* incorrect password attempts")
SUDO_FAIL_BOTH_REGEX: Pattern = re.compile(
    r"(sudo: \d* incorrect password attempts)|(\[sudo\] password for .*:\s+)"
)
SSH_PASSWORD_REGEX: Pattern = re.compile(r".*@.* password:\s+")
SSH_CONNECTED_REGEX: Pattern = re.compile(r"\$\s+")
SSH_CONNECTION_REGEX: Pattern = re.compile(
    f"({SSH_PASSWORD_REGEX.pattern})|({SSH_CONNECTED_REGEX.pattern})"
)
