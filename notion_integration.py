"""
notion_integration.py — Write scraped emails to a Notion database.

Expected database schema (must be created manually in Notion):
  - Email          (Title)   — primary identifier
  - Source Post URL (URL)    — LinkedIn post the email came from
  - Date Added     (Date)    — ISO timestamp of when it was scraped
  - Status         (Select)  — "New" / "Contacted" / "Unsubscribed"

Setup:
  1. Create a Notion integration at https://www.notion.so/my-integrations
  2. Share your database with that integration (open database → ... → Connections)
  3. Set NOTION_API_KEY and NOTION_DATABASE_ID in .env
"""

import asyncio
import logging
from datetime import datetime, timezone

from notion_client import AsyncClient
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


class NotionIntegration:
    def __init__(self, api_key: str, database_id: str):
        self.client = AsyncClient(auth=api_key)
        self.database_id = database_id
        # In-memory cache populated at startup to avoid per-email API lookups
        self._existing_emails: set[str] = set()

    async def fetch_existing_emails(self) -> set[str]:
        """
        Paginate through all records in the database and cache email values.
        Called once at startup so we can do O(1) dedup checks during the run.
        """
        logger.info("Fetching existing emails from Notion...")
        existing: set[str] = set()
        cursor = None

        while True:
            kwargs: dict = {"database_id": self.database_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor

            try:
                response = await self.client.databases.query(**kwargs)
            except APIResponseError as e:
                logger.error("Notion API error while fetching existing emails: %s", e)
                break

            for page in response.get("results", []):
                try:
                    title_parts = page["properties"]["Email"]["title"]
                    if title_parts:
                        email = title_parts[0]["text"]["content"].lower().strip()
                        existing.add(email)
                except (KeyError, IndexError):
                    continue

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        self._existing_emails = existing
        logger.info("Found %d existing emails in Notion.", len(existing))
        return existing

    async def add_email(self, email: str, source_url: str) -> bool:
        """
        Create a new page in the Notion database for this email.
        Returns True on success, False on failure.
        Respects Notion's 3 req/s rate limit via a 0.4 s post-write sleep.
        """
        email = email.lower().strip()
        success = False
        try:
            await self.client.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "Email": {
                        "title": [{"text": {"content": email}}]
                    },
                    "Source Post URL": {
                        "url": source_url
                    },
                    "Date Added": {
                        "date": {"start": datetime.now(timezone.utc).isoformat()}
                    },
                    "Status": {
                        "select": {"name": "New"}
                    },
                },
            )
            self._existing_emails.add(email)
            success = True
        except APIResponseError as e:
            logger.error("Failed to add %s to Notion: %s", email, e)
        finally:
            # Always throttle to stay under Notion's 3 req/s rate limit
            await asyncio.sleep(0.4)
        return success
