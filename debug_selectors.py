"""
debug_selectors.py — Inspect LinkedIn feed HTML to find correct CSS selectors.

Run this when the scraper finds 0 posts. It opens a visible browser, loads
your feed, and tells you exactly which selectors match the current HTML.

Usage:
    python debug_selectors.py

Output:
    - Prints match counts for each candidate selector
    - Saves debug_screenshot.png so you can see what the browser loaded
    - Prints outer HTML snippets of matched elements
"""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

from scraper import LINKEDIN_BASE_URL, _patch_webdriver

AUTH_STATE_PATH = "auth_state.json"

CANDIDATE_SELECTORS = [
    "div[data-urn]",
    "div[data-id]",
    "div[data-activity-urn]",
    "div.feed-shared-update-v2",
    "div.occludable-update",
    "article",
    "li.feed-shared-update-v2",
    "[data-urn*='activity']",
    "[data-id*='activity']",
]


async def debug():
    if not os.path.exists(AUTH_STATE_PATH):
        print(f"ERROR: '{AUTH_STATE_PATH}' not found.")
        print("Run 'python setup_auth.py' first to save your LinkedIn session.")
        sys.exit(1)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            storage_state=AUTH_STATE_PATH,
        )

        page = await context.new_page()
        await _patch_webdriver(page)

        print("Navigating to LinkedIn feed...")
        await page.goto(LINKEDIN_BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        await page.goto(f"{LINKEDIN_BASE_URL}/feed/", wait_until="domcontentloaded", timeout=30000)

        print("Waiting 5 seconds for feed to render...")
        await asyncio.sleep(5)

        print("\nSaving screenshot to debug_screenshot.png...")
        try:
            await page.screenshot(path="debug_screenshot.png", full_page=False, timeout=0)
        except Exception as e:
            print(f"  (screenshot failed: {e})")

        print("\n── Selector match counts ─────────────────────────────")
        best_selector = None
        best_count = 0

        for selector in CANDIDATE_SELECTORS:
            try:
                count = await page.locator(selector).count()
                flag = " ✓ BEST" if count > best_count and count > 0 else ""
                print(f"  {count:>4}  {selector}{flag}")
                if count > best_count:
                    best_count = count
                    best_selector = selector
            except Exception as e:
                print(f"     ?  {selector}  (error: {e})")

        print("──────────────────────────────────────────────────────")

        if best_selector and best_count > 0:
            print(f"\nBest match: {best_selector!r} ({best_count} elements)")
            print("\nFirst 3 matching elements (outer HTML snippet):")
            locator = page.locator(best_selector)
            for i in range(min(3, best_count)):
                try:
                    el = locator.nth(i)
                    html = await el.evaluate("el => el.outerHTML.slice(0, 200)")
                    urn = await el.get_attribute("data-urn") or await el.get_attribute("data-id") or "n/a"
                    print(f"\n  [{i}] data-urn/id: {urn}")
                    print(f"       {html[:200]}")
                except Exception:
                    pass
        else:
            print("\nNo selectors matched — inspecting actual DOM structure...")

        print("\n── DOM inspection ────────────────────────────────────")
        # Find ALL elements with data-urn regardless of tag type
        urn_elements = await page.evaluate("""() => {
            const els = document.querySelectorAll('[data-urn]');
            return Array.from(els).slice(0, 5).map(el => ({
                tag: el.tagName,
                dataUrn: (el.getAttribute('data-urn') || '').slice(0, 60),
                classes: (el.className || '').slice(0, 80),
                html: el.outerHTML.slice(0, 150)
            }));
        }""")
        if urn_elements:
            print(f"  Found {len(urn_elements)} [data-urn] elements (any tag):")
            for el in urn_elements:
                print(f"    <{el['tag']}> data-urn={el['dataUrn']}")
                print(f"    classes: {el['classes']}")
                print(f"    html: {el['html']}\n")
        else:
            print("  No [data-urn] elements found anywhere on the page.")

        # Dump first 3 children of the main feed container
        feed_children = await page.evaluate("""() => {
            const feed = document.querySelector('main') ||
                         document.querySelector('[role=main]') ||
                         document.querySelector('.scaffold-finite-scroll__content');
            if (!feed) return [{'tag':'?','classes':'','attrs':'Could not find main/feed container','html':''}];
            return Array.from(feed.children).slice(0, 3).map(el => ({
                tag: el.tagName,
                classes: (el.className || '').slice(0, 100),
                attrs: Array.from(el.attributes).map(a => a.name+'='+a.value).join(' ').slice(0, 100),
                html: el.outerHTML.slice(0, 200)
            }));
        }""")
        print("  First 3 children of main feed container:")
        for el in feed_children:
            print(f"    <{el['tag']}> classes={el['classes']}")
            print(f"    attrs: {el['attrs']}")
            print(f"    html: {el['html']}\n")
        print("──────────────────────────────────────────────────────")

        await browser.close()

    print("\nDone. Open debug_screenshot.png to see what the browser loaded.")
    if best_selector:
        print(f"\nUpdate SELECTORS['post_container'] in scraper.py to: {best_selector!r}")


if __name__ == "__main__":
    asyncio.run(debug())
