"""
scraper.py — Authenticate to LinkedIn and scrape feed post comments.

Authentication strategy: restore a full browser session saved by setup_auth.py
(Playwright storage_state — all cookies + localStorage). This is more reliable
than injecting a single cookie and avoids LinkedIn's redirect-loop detection.

Anti-detection measures:
  - Realistic user-agent and viewport
  - navigator.webdriver patched to undefined via add_init_script
  - Jittered delays between all actions (no fixed sleeps)
  - Headless mode optional (--no-headless for debugging)

Scraping strategy: LinkedIn's current React SPA uses hashed CSS class names
and no data-* attributes, so per-post CSS selectors are unreliable. Instead we
extract all innerText from the <main> element after each scroll and let the
email regex in extractor.py find emails in the raw text.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

LINKEDIN_BASE_URL = "https://www.linkedin.com"

# ── Selectors ──────────────────────────────────────────────────────────────────
SELECTORS = {
    # Feed container — used to confirm the feed has rendered
    "feed_indicator": "main",
}


@dataclass
class ScrapedPost:
    urn: str
    url: str
    comment_texts: list[str] = field(default_factory=list)


async def _patch_webdriver(page: Page) -> None:
    """Patch navigator.webdriver so Playwright isn't fingerprinted as a bot."""
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    """)


async def create_browser_context(playwright, auth_state_path: str, headless: bool = True):
    """Launch Chromium and restore a saved LinkedIn session."""
    import os
    if not os.path.exists(auth_state_path):
        raise FileNotFoundError(
            f"\n  '{auth_state_path}' not found.\n"
            "  Run 'python setup_auth.py' first to log in and save your session.\n"
        )
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
        timezone_id="America/New_York",
        storage_state=auth_state_path,
    )
    return browser, context


async def scrape_feed(
    page: Page,
    max_scrolls: int = 50,
    scroll_delay_range: tuple[float, float] = (1.0, 2.0),
):
    """
    Async generator that scrolls the LinkedIn feed and yields ScrapedPost objects.

    LinkedIn's React SPA uses hashed CSS class names and no data-* attributes,
    so we can't target individual posts. Instead, after each scroll we extract
    all innerText from <main> and yield the *new* text (delta since last scroll)
    as a single ScrapedPost. The caller runs email regex on that text.

    Stops after max_scrolls iterations or 3 consecutive scrolls with no new content.
    """
    empty_scroll_count = 0
    prev_text_len = 0
    min_delay, max_delay = scroll_delay_range

    logger.info("Starting feed scrape (max %d scrolls)...", max_scrolls)

    # Wait for network to settle
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass

    # Wait for the main content area to appear
    try:
        await page.wait_for_selector(SELECTORS["feed_indicator"], timeout=15000)
        logger.debug("Feed container confirmed present.")
    except PlaywrightTimeoutError:
        logger.warning(
            "Feed container not found after 15s — proceeding anyway. "
            "Try --no-headless to inspect the browser."
        )

    for scroll_num in range(max_scrolls):
        # Extract all visible text from the feed
        text: str = await page.evaluate(
            "() => document.querySelector('main')?.innerText"
            " || document.body.innerText || ''"
        )

        # Only process text that's new since the last scroll
        new_text = text[prev_text_len:]
        prev_text_len = len(text)

        if new_text.strip():
            empty_scroll_count = 0
            logger.info(
                "Scroll %d/%d — %d new chars of content.",
                scroll_num + 1, max_scrolls, len(new_text),
            )
            yield ScrapedPost(
                urn=f"scroll-{scroll_num}",
                url=page.url,
                comment_texts=[new_text],
            )
        else:
            empty_scroll_count += 1
            logger.debug(
                "No new content on scroll %d (%d consecutive empty).",
                scroll_num, empty_scroll_count,
            )
            if empty_scroll_count >= 3:
                logger.info("Feed exhausted — no new content after 3 consecutive scrolls.")
                break

        # Scroll down — try all likely scroll containers so LinkedIn's
        # intersection-observer-based infinite scroll fires.
        await page.evaluate("""() => {
            const targets = [
                document.querySelector('main'),
                document.querySelector('[role="main"]'),
                document.querySelector('.scaffold-layout__main'),
                document.documentElement,
                document.body,
            ];
            for (const el of targets) {
                if (el) el.scrollTop = el.scrollHeight;
            }
            window.scrollTo(0, document.body.scrollHeight);
        }""")
        # Press End twice to scroll 2 viewport heights — loads a larger post batch
        await page.keyboard.press("End")
        await page.keyboard.press("End")

        # Short jitter so we don't hammer LinkedIn's servers
        await asyncio.sleep(random.uniform(min_delay, max_delay))

        # Adaptive wait: proceed as soon as new content appears (up to 10s)
        for _ in range(20):  # 20 × 0.5s = 10s ceiling
            await asyncio.sleep(0.5)
            current_len: int = await page.evaluate(
                "() => (document.querySelector('main')?.innerText"
                " || document.body.innerText || '').length"
            )
            if current_len > prev_text_len + 200:
                break  # New content loaded — no need to keep waiting
