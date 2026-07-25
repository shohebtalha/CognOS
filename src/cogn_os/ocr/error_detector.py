from __future__ import annotations

import re


_ERROR_PATTERNS = [
    r"\bTraceback \(most recent call last\)",
    r"\b(SyntaxError|TypeError|ValueError|ModuleNotFoundError|ImportError|NameError):",
    r"\b(error|failed|exception)\b.*\b(line|stack|compile|runtime)\b",
    r"\bECONNREFUSED\b|\bEADDRINUSE\b|\bENOENT\b",
    r"\bpanic:\b|\bfatal error\b|\bsegmentation fault\b",
]


def contains_error_signal(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _ERROR_PATTERNS)
