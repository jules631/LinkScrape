"""
extractor.py — Extract and normalise email addresses from text.

Pure function module: no I/O, no external dependencies.
"""

import re

# Compiled once at import time for performance
_EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'
)

# Common non-human email domains / patterns to ignore
_BLOCKLIST = {
    "example.com",
    "example.org",
    "test.com",
    "noreply",
    "no-reply",
    "donotreply",
}


def extract_emails(text: str) -> set[str]:
    """
    Return a set of normalised (lowercase) email addresses found in text.

    Filters out obvious false positives via a blocklist.
    """
    found = set()
    for match in _EMAIL_RE.findall(text):
        email = match.lower().strip(".")
        local, _, domain = email.partition("@")
        # Skip blocklisted domains and local parts
        if domain in _BLOCKLIST or local in _BLOCKLIST:
            continue
        # Skip emails with consecutive dots (invalid)
        if ".." in email:
            continue
        found.add(email)
    return found
