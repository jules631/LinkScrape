#!/usr/bin/env python3
"""
simulate_run.py — Simulate a LinkScrape terminal session for demo recording.

Run this in a terminal and screen-record it to produce the demo GIF.
See demo/README.md for recording instructions.

Usage:
    python demo/simulate_run.py          # realistic delays
    python demo/simulate_run.py --fast   # instant output (for testing)
"""

import sys
import time
import argparse
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

MAX_DELAY = 2.5   # cap all inter-line pauses at this many seconds
TYPE_DELAY = 0.04  # seconds between characters when "typing"

USE_COLOR = sys.stdout.isatty()

# ── Helpers ───────────────────────────────────────────────────────────────────

def c(text: str, code: str) -> str:
    """Wrap text in an ANSI color code if stdout is a TTY."""
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def green(text: str) -> str:
    return c(text, "32")


def yellow(text: str) -> str:
    return c(text, "33")


def cyan(text: str) -> str:
    return c(text, "36")


def dim(text: str) -> str:
    return c(text, "2")


def sleep(seconds: float, fast: bool) -> None:
    if not fast:
        time.sleep(min(seconds, MAX_DELAY))


def type_line(text: str, fast: bool) -> None:
    """Print text character by character to simulate typing."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        if not fast:
            time.sleep(TYPE_DELAY)
    sys.stdout.write("\n")
    sys.stdout.flush()


def log(level: str, message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    if level == "INFO":
        lvl = green("INFO    ")
    elif level == "WARNING":
        lvl = yellow("WARNING ")
    else:
        lvl = level.ljust(8)
    print(f"{dim(now)}  {lvl}  {message}")
    sys.stdout.flush()


def divider() -> None:
    print("─" * 50)
    sys.stdout.flush()


# ── Demo script ───────────────────────────────────────────────────────────────

FAKE_POST_URL = "https://www.linkedin.com/feed/update/urn:li:activity:7194823041887682560"
FAKE_POST_URL_2 = "https://www.linkedin.com/feed/update/urn:li:activity:7194923151987792671"

EMAILS = [
    ("jane@gmail.com", FAKE_POST_URL),
    ("bob@outlook.com", FAKE_POST_URL),
    ("sarah@techstartup.com", FAKE_POST_URL),
    ("marcus.jones@gmail.com", FAKE_POST_URL_2),
    ("priya.sharma@hotmail.com", FAKE_POST_URL_2),
    ("alex@designstudio.io", FAKE_POST_URL_2),
]


def run(fast: bool) -> None:
    # ── Simulate typing the command ───────────────────────────────────────────
    sleep(0.4, fast)
    sys.stdout.write(cyan("$ "))
    sys.stdout.flush()
    type_line("python main.py", fast)
    sleep(0.6, fast)

    # ── Startup ───────────────────────────────────────────────────────────────
    log("INFO", "Fetching existing emails from Notion...")
    sleep(1.2, fast)
    log("INFO", "Found 0 existing emails in Notion.")
    sleep(0.3, fast)
    log("INFO", "Navigating to LinkedIn feed...")
    sleep(2.0, fast)
    log("INFO", "Feed loaded. Starting scrape...")
    sleep(0.2, fast)
    log("INFO", "Starting feed scrape (max 50 scrolls)...")
    sleep(0.4, fast)

    # ── Scroll 1 ──────────────────────────────────────────────────────────────
    sleep(2.5, fast)
    log("INFO", "Scroll 1/50 — found 6 new posts (6 total seen).")
    sleep(1.8, fast)
    log("INFO", f"Added: {green(EMAILS[0][0])}  (post: {dim(EMAILS[0][1])})")
    sleep(0.8, fast)
    log("INFO", f"Added: {green(EMAILS[1][0])}  (post: {dim(EMAILS[1][1])})")
    sleep(0.6, fast)
    log("INFO", f"Added: {green(EMAILS[2][0])}  (post: {dim(EMAILS[2][1])})")

    # ── Scroll 2 ──────────────────────────────────────────────────────────────
    sleep(2.5, fast)
    log("INFO", "Scroll 2/50 — found 5 new posts (11 total seen).")
    sleep(2.0, fast)
    log("INFO", f"Added: {green(EMAILS[3][0])}  (post: {dim(EMAILS[3][1])})")
    sleep(0.7, fast)
    log("INFO", f"Added: {green(EMAILS[4][0])}  (post: {dim(EMAILS[4][1])})")
    sleep(0.5, fast)
    log("INFO", f"Added: {green(EMAILS[5][0])}  (post: {dim(EMAILS[5][1])})")

    # ── Time skip ─────────────────────────────────────────────────────────────
    sleep(1.0, fast)
    print(dim("  ... (scraping continues across 45 more scroll iterations) ..."))
    sys.stdout.flush()
    sleep(2.0, fast)

    # ── Final scrolls ─────────────────────────────────────────────────────────
    log("INFO", "Scroll 47/50 — found 3 new posts (183 total seen).")
    sleep(2.5, fast)
    log("INFO", "Scroll 48/50 — found 0 new posts (183 total seen).")
    sleep(2.5, fast)
    log("INFO", "Scroll 49/50 — found 0 new posts (183 total seen).")
    sleep(2.5, fast)
    log("INFO", "Scroll 50/50 — found 0 new posts (183 total seen).")
    sleep(0.8, fast)
    log("INFO", "Feed exhausted — no new posts after 3 consecutive scrolls.")
    sleep(0.6, fast)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    divider()
    print(f"  Posts scraped:    {cyan('47')}")
    print(f"  Emails found:     {cyan('183')}")
    print(f"  New emails added: {green('176')}")
    divider()
    print()
    sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a LinkScrape terminal session.")
    parser.add_argument("--fast", action="store_true", help="Skip all delays (for testing)")
    args = parser.parse_args()
    run(fast=args.fast)


if __name__ == "__main__":
    main()
