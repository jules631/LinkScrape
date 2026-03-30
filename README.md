# LinkScrape

Scrapes emails from LinkedIn "drop your email" post comments and saves them to Notion.

![LinkScrape demo](assets/demo.gif)

---

## The Problem

LinkedIn "drop your email" posts generate hundreds of email comments — warm leads who publicly opted in. LinkedIn gives you no way to export them. No copy button, no bulk select, just an endless scroll of comments you'd have to copy one by one.

This tool automates the entire pipeline so what would take hours manually takes minutes.

## How It Works

```
LinkedIn feed  →  Extract text per scroll  →  Regex for emails  →  Deduplicate  →  Notion
```

1. **Authenticate** — saves your full LinkedIn session via a real browser login (one-time setup)
2. **Scroll** — headless browser scrolls your feed with jittered delays to avoid detection
3. **Extract** — regex scans all visible post and comment text for email addresses
4. **Write** — new emails land in Notion tagged `New`, ready to export into your newsletter tool

---

## Quick Start

**Prerequisites:** Python 3.11+, a LinkedIn account, a Notion integration + database

### 1. Install

```bash
git clone https://github.com/jules631/LinkScrape.git
cd LinkScrape
pip install -r requirements.txt
playwright install chromium
```

### 2. Authenticate (one-time)

```bash
python setup_auth.py
```

A browser opens. Log into LinkedIn normally, then press Enter in the terminal. Your session is saved to `auth_state.json`. Re-run any time the scraper reports an auth error.

### 3. Configure

```bash
cp .env.example .env
# Fill in NOTION_API_KEY and NOTION_DATABASE_ID
```

**Notion setup:**

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration** → copy the secret → paste as `NOTION_API_KEY`
2. Create a database with these properties:

   | Property | Type |
   |---|---|
   | Email | Title |
   | Source Post URL | URL |
   | Date Added | Date |
   | Status | Select (options: New, Contacted, Unsubscribed) |

3. Share the database with your integration: open the database → `...` → **Connections** → add your integration
4. Copy the database ID from the URL (`notion.so/yourworkspace/<DATABASE_ID>?v=...`) → paste as `NOTION_DATABASE_ID`

### 4. Run

```bash
python main.py --dry-run   # Preview: prints emails to terminal, writes nothing to Notion
python main.py             # Full run: writes new emails to Notion
```

---

## CLI Options

| Flag | What it does | Default |
|---|---|---|
| `--dry-run` | Print emails to terminal, skip Notion writes | off |
| `--no-headless` | Show the browser window (useful for debugging) | hidden |
| `--max-scrolls N` | Number of feed scroll iterations | 100 |

---

## Expected Output

```
09:12:05  INFO  Navigating to LinkedIn feed...
09:12:09  INFO  Feed loaded. Starting scrape...
09:12:14  INFO  Scroll 1/100 — 9497 new chars of content.
09:12:16  INFO  Scroll 2/100 — 7831 new chars of content.
...
09:14:33  INFO  Feed exhausted — no new content after 3 consecutive scrolls.

──────────────────────────────────────────────
  Posts scraped:    31
  Emails found:     94
  New emails added: 87
──────────────────────────────────────────────
```

Emails already in Notion are silently skipped — reruns are always safe.

Once complete, your Notion database has a row for every new email found:

| Email | Source Post URL | Date Added | Status |
|---|---|---|---|
| jane@gmail.com | https://linkedin.com/feed/ | 2026-03-30 | New |
| bob@outlook.com | https://linkedin.com/feed/ | 2026-03-30 | New |

Filter by `Status = New`, export as CSV, and import into Mailchimp, Beehiiv, ConvertKit, or any other newsletter tool.

---

## Notes

- **Rate limiting:** Scrolls use a 1–2s jitter plus an adaptive wait that proceeds as soon as LinkedIn renders new posts (up to 10s ceiling). Notion writes are throttled to stay within the 3 req/s API limit.
- **Deduplication:** All existing Notion emails are loaded at startup. Reruns never create duplicates.
- **Session expiry:** If auth fails, re-run `python setup_auth.py`.
