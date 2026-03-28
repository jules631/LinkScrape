"""
scraper.py — Authenticate to LinkedIn and scrape feed post comments.

Authentication strategy: inject the li_at session cookie directly, bypassing
the login form and 2FA entirely. This is more reliable than automating the
login page and far less likely to trigger bot detection.

Anti-detection measures:
  - Realistic user-agent and viewport
  - navigator.webdriver patched to undefined via add_init_script
  - Jittered delays between all actions (no fixed sleeps)
  - Headless mode optional (--no-headless for debugging)
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

# ── CSS selectors ─────────────────────────────────────────────────────────────
# Centralised here so LinkedIn UI changes only require updating this dict.
SELECTORS = {
    # A post in the feed — identified by its data-urn attribute
    "post_container": "div[data-urn]",
    # The post's unique identifier attribute
    "post_urn_attr": "data-urn",
    # Permalink to the post (used as source URL)
    "post_link": "a[href*='/feed/update/']",
    # Button that opens / focuses the comment section
    "comments_button": "button[aria-label*='comment'], button[aria-label*='Comment']",
    # Button to load additional comments
    "load_more_comments": "button[aria-label*='Load more comments'], button[aria-label*='load more comments']",
    # Individual comment text content
    "comment_text": "span.comments-comment-item-content-body, div.comments-comment-item__main-content span",
    # Element present when successfully logged into LinkedIn feed
    "feed_indicator": "div.scaffold-finite-scroll, div[data-finite-scroll-hotkey-context]",
    # Authwall — shown when the session is invalid
    "authwall": "div.authwall-join-form, div#join-form",
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


async def create_browser_context(playwright, li_at: str, headless: bool = True):
    """Launch Chromium and inject the LinkedIn session cookie."""
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
    )
    await context.add_cookies([
        {
            "name": "li_at",
            "value": li_at,
            "domain": ".linkedin.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "None",
        }
    ])
    return browser, context


async def _expand_comments(page: Page, post) -> list[str]:
    """
    Open the comment section on a post and load all comments.
    Returns a list of comment text strings.
    """
    # Try to click the comments button to open the comment section
    try:
        btn = post.locator(SELECTORS["comments_button"]).first
        if await btn.count() > 0:
            await btn.click()
            await asyncio.sleep(random.uniform(1.0, 2.0))
    except Exception:
        pass

    # Loop-click "Load more comments" until all are visible
    while True:
        try:
            load_more = post.locator(SELECTORS["load_more_comments"])
            if await load_more.count() == 0:
                break
            await load_more.first.click()
            await asyncio.sleep(random.uniform(0.8, 1.6))
        except PlaywrightTimeoutError:
            break
        except Exception:
            break

    # Collect all visible comment texts
    texts: list[str] = []
    try:
        comment_els = post.locator(SELECTORS["comment_text"])
        count = await comment_els.count()
        for i in range(count):
            try:
                text = await comment_els.nth(i).inner_text(timeout=3000)
                if text.strip():
                    texts.append(text.strip())
            except Exception:
                continue
    except Exception as e:
        logger.debug("Error collecting comment texts: %s", e)

    return texts


async def scrape_feed(
    page: Page,
    max_scrolls: int = 50,
    scroll_delay_range: tuple[float, float] = (3.0, 7.0),
):
    """
    Async generator that scrolls the LinkedIn feed and yields ScrapedPost objects.

    Each ScrapedPost contains the post URN, its URL, and all comment texts.
    Stops after max_scrolls iterations or when no new posts appear for 3 consecutive scrolls.
    """
    seen_urns: set[str] = set()
    empty_scroll_count = 0
    min_delay, max_delay = scroll_delay_range

    logger.info("Starting feed scrape (max %d scrolls)...", max_scrolls)

    for scroll_num in range(max_scrolls):
        # Find all currently visible post containers
        post_containers = page.locator(SELECTORS["post_container"])
        count = await post_containers.count()

        new_posts_this_scroll = 0

        for i in range(count):
            try:
                post = post_containers.nth(i)
                urn = await post.get_attribute(SELECTORS["post_urn_attr"])
                if not urn or urn in seen_urns:
                    continue

                seen_urns.add(urn)
                new_posts_this_scroll += 1

                # Try to get the post's permalink
                url = ""
                try:
                    link_el = post.locator(SELECTORS["post_link"]).first
                    if await link_el.count() > 0:
                        href = await link_el.get_attribute("href")
                        if href:
                            url = href if href.startswith("http") else f"https://www.linkedin.com{href}"
                except Exception:
                    pass

                logger.debug("Scraping post %s", urn)
                comment_texts = await _expand_comments(page, post)

                if comment_texts:
                    yield ScrapedPost(urn=urn, url=url, comment_texts=comment_texts)

            except PlaywrightTimeoutError:
                logger.debug("Timeout on post %d of scroll %d, skipping.", i, scroll_num)
                continue
            except Exception as e:
                logger.debug("Error processing post: %s", e)
                continue

        # Track consecutive empty scrolls to detect feed exhaustion
        if new_posts_this_scroll == 0:
            empty_scroll_count += 1
            logger.debug("No new posts on scroll %d (%d consecutive empty).", scroll_num, empty_scroll_count)
            if empty_scroll_count >= 3:
                logger.info("Feed exhausted — no new posts after 3 consecutive scrolls.")
                break
        else:
            empty_scroll_count = 0
            logger.info(
                "Scroll %d/%d — found %d new posts (%d total seen).",
                scroll_num + 1, max_scrolls, new_posts_this_scroll, len(seen_urns),
            )

        # Scroll down and wait
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        delay = random.uniform(min_delay, max_delay)
        logger.debug("Waiting %.1f s before next scroll...", delay)
        await asyncio.sleep(delay)

        # Wait for network to settle (with fallback)
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except PlaywrightTimeoutError:
            pass
