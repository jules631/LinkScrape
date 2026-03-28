"""
main.py — CLI entry point for LinkScrape.

Usage:
    python main.py [--max-scrolls N] [--no-headless] [--dry-run]

Options:
    --max-scrolls N     Override MAX_SCROLL_ITERATIONS from .env (default: 50)
    --no-headless       Show the browser window (useful for debugging)
    --dry-run           Scrape and extract emails but print them instead of
                        writing to Notion (safe for testing)
"""

import argparse
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from extractor import extract_emails
from notion_integration import NotionIntegration
from scraper import _patch_webdriver, create_browser_context, scrape_feed

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape LinkedIn feed comments for emails and save them to Notion."
    )
    parser.add_argument(
        "--max-scrolls",
        type=int,
        default=None,
        help="Number of feed scroll iterations (overrides MAX_SCROLL_ITERATIONS in .env)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show the browser window (useful for debugging)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print emails to stdout instead of writing to Notion",
    )
    return parser.parse_args()


def load_config(args: argparse.Namespace) -> dict:
    """Load and validate all required configuration from .env and CLI args."""
    load_dotenv()

    notion_vars = {
        "NOTION_API_KEY": os.getenv("NOTION_API_KEY", "").strip(),
        "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID", "").strip(),
    }

    missing = [k for k, v in notion_vars.items() if not v]
    if missing and not args.dry_run:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        logger.error("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    # Parse scroll delay range
    delay_str = os.getenv("SCROLL_DELAY_RANGE", "3,7")
    try:
        parts = delay_str.split(",")
        scroll_delay = (float(parts[0]), float(parts[1]))
    except Exception:
        scroll_delay = (3.0, 7.0)

    # Max scrolls: CLI arg > env var > default
    max_scrolls = args.max_scrolls
    if max_scrolls is None:
        max_scrolls = int(os.getenv("MAX_SCROLL_ITERATIONS", "100"))

    return {
        **notion_vars,
        "auth_state_path": os.getenv("AUTH_STATE_PATH", "auth_state.json"),
        "max_scrolls": max_scrolls,
        "scroll_delay": scroll_delay,
        "headless": not args.no_headless,
        "dry_run": args.dry_run,
    }


async def run(config: dict) -> None:
    dry_run = config["dry_run"]

    # ── Notion setup ──────────────────────────────────────────────────────────
    notion: NotionIntegration | None = None
    seen_emails: set[str] = set()

    if not dry_run:
        notion = NotionIntegration(config["NOTION_API_KEY"], config["NOTION_DATABASE_ID"])
        seen_emails = await notion.fetch_existing_emails()
    else:
        logger.info("DRY RUN — emails will be printed, not written to Notion.")

    # ── Browser setup ─────────────────────────────────────────────────────────
    async with async_playwright() as pw:
        browser, context = await create_browser_context(
            pw,
            auth_state_path=config["auth_state_path"],
            headless=config["headless"],
        )

        try:
            page = await context.new_page()

            await _patch_webdriver(page)

            logger.info("Navigating to LinkedIn feed...")
            await page.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)

            # ── Auth check ────────────────────────────────────────────────────
            # Give the page a moment to settle then check for expected elements
            await asyncio.sleep(3)

            current_url = page.url
            if (
                "/login" in current_url
                or "/authwall" in current_url
                or "linkedin.com/feed" not in current_url
            ):
                logger.error(
                    "LinkedIn session expired or invalid. "
                    "Run 'python setup_auth.py' to re-authenticate."
                )
                sys.exit(1)

            logger.info("Feed loaded. Starting scrape...")

            # ── Scrape loop ───────────────────────────────────────────────────
            posts_scraped = 0
            emails_found = 0
            emails_added = 0
            write_failures = 0

            async for post in scrape_feed(
                page,
                max_scrolls=config["max_scrolls"],
                scroll_delay_range=config["scroll_delay"],
            ):
                posts_scraped += 1
                post_emails: set[str] = set()

                for comment in post.comment_texts:
                    post_emails |= extract_emails(comment)

                for email in post_emails:
                    emails_found += 1

                    if email in seen_emails:
                        logger.debug("Skipping duplicate: %s", email)
                        continue

                    seen_emails.add(email)

                    if dry_run:
                        print(f"  {email}  (from {post.url or 'unknown post'})")
                        emails_added += 1
                    else:
                        success = await notion.add_email(email, post.url)
                        if success:
                            emails_added += 1
                            logger.info("Added: %s  (post: %s)", email, post.url or "n/a")
                        else:
                            write_failures += 1

        finally:
            await browser.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "─" * 50)
    print(f"  Posts scraped:    {posts_scraped}")
    print(f"  Emails found:     {emails_found}")
    print(f"  New emails added: {emails_added}")
    if write_failures:
        print(f"  Write failures:   {write_failures}  (check logs above)")
    print("─" * 50)


def main() -> None:
    args = parse_args()
    config = load_config(args)
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
