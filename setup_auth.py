"""
setup_auth.py — One-time LinkedIn authentication setup.

Opens a real browser window so you can log into LinkedIn normally.
Once logged in, saves the full browser session (all cookies) to
auth_state.json so the scraper can reuse it without logging in again.

Run this once before using the scraper:
    python setup_auth.py

Re-run it any time the scraper reports an authentication error.
"""

import asyncio
import sys
from playwright.async_api import async_playwright

AUTH_STATE_PATH = "auth_state.json"


async def setup():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
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

        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        print("\n" + "─" * 55)
        print("  A browser window has opened.")
        print("  Log into LinkedIn, then come back here and")
        print("  press Enter to save your session.")
        print("─" * 55)

        try:
            input("\n  Press Enter once you are logged in... ")
        except EOFError:
            pass

        await context.storage_state(path=AUTH_STATE_PATH)
        await browser.close()

    print(f"\n  Session saved to {AUTH_STATE_PATH}")
    print("  You can now run: python main.py --dry-run\n")


if __name__ == "__main__":
    asyncio.run(setup())
