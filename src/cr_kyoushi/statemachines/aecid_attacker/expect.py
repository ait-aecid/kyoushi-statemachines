import re

from typing import Pattern


BASH_PATTERN: Pattern = re.compile(r".*@.*:.*\$\s+")
SH_PATTERN: Pattern = re.compile(r"\$\s+")
SU_PASSWORD_PROMPT: Pattern = re.compile(r"Password:\s+")
SU_FAIL: Pattern = re.compile(r"Authentication failure")
