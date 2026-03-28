# LinkScrape

Automatically collect emails from LinkedIn "drop your email" posts and add them to your Notion newsletter database.

![LinkScrape demo](assets/demo.gif)

> **No GIF yet?** See [demo/README.md](demo/README.md) to record one in ~2 minutes using the included simulation script.

---

## The Problem

People post on LinkedIn: *"Type your email below and I'll send you my free guide."*
Hundreds of people comment their email addresses — warm, self-selected leads who **asked** to hear from you.

But LinkedIn gives you no way to export them. No copy button. No bulk select. Just an endless scroll of comments, one by one, manually.

## The Opportunity

These are some of the highest-intent contacts you'll ever find. They publicly opted in, on a post you or someone in your network made. Getting them into your newsletter should take minutes, not hours.

LinkScrape automates the entire pipeline:

```
LinkedIn feed  →  Expand comments  →  Extract emails  →  Deduplicate  →  Notion
```

## How It Works

1. **Authenticate** — injects your `li_at` session cookie into a headless browser (no username/password, no 2FA friction)
2. **Scroll your feed** — uses Playwright to scroll through posts with human-like jitter delays
3. **Expand comments** — opens each post's comment section and loads all comments
4. **Extract emails** — regex scans every comment for valid email addresses
5. **Deduplicate** — checks against existing Notion records so reruns never create duplicates
6. **Write to Notion** — adds each new email with source post URL, date, and a `New` status tag

---

## Quick Start

### Prerequisites

- Python 3.11+
- A LinkedIn account (logged in in your browser)
- A Notion account with an integration and database set up (see [Setup Guide](#setup-guide) below)

### Install

```bash
git clone https://github.com/jules631/LinkScrape.git
cd LinkScrape

pip install -r requirements.txt
playwright install chromium
```

### Authenticate (one-time)

```bash
python setup_auth.py
```

A browser window opens. Log into LinkedIn normally, then press Enter in the terminal. Your session is saved to `auth_state.json` — no cookie hunting required. Re-run this any time the scraper reports an auth error.

### Configure

```bash
cp .env.example .env
# Fill in NOTION_API_KEY and NOTION_DATABASE_ID — see Setup Guide below
```

### Run

```bash
# Full run — scrapes feed and writes emails to Notion
python main.py

# Preview only — prints emails to terminal, nothing written to Notion
python main.py --dry-run

# Show the browser window while scraping (useful for debugging)
python main.py --no-headless

# Control how many feed pages to scroll through
python main.py --max-scrolls 100
```

---

## User Journey

1. You see a "drop your email" post on LinkedIn with 300 comments
2. You run `python setup_auth.py`, log in once through a browser window (30 seconds, one-time)
3. You set up a Notion integration and database (5 minutes, one-time)
4. You fill in `.env` with your Notion credentials
5. You run `python main.py`
6. The tool opens a headless browser, scrolls your feed, expands all comment sections, and finds every email address
7. All emails appear in Notion tagged `New`, ready to export into Mailchimp, Beehiiv, ConvertKit, or any other newsletter tool

---

## Expected Output

> To see this interactively, run `python demo/simulate_run.py` — it plays back a realistic session with real timing.

### While running

You'll see live progress in the terminal as the tool scrolls your feed and finds emails:

```
09:12:03  INFO      DRY RUN — emails will be printed, not written to Notion.
09:12:05  INFO      Navigating to LinkedIn feed...
09:12:09  INFO      Feed loaded. Starting scrape...
09:12:09  INFO      Starting feed scrape (max 50 scrolls)...
09:12:14  INFO      Scroll 1/50 — found 6 new posts (6 total seen).
09:12:21  INFO      Added: jane@gmail.com  (post: https://linkedin.com/feed/update/urn:...)
09:12:22  INFO      Added: bob@outlook.com  (post: https://linkedin.com/feed/update/urn:...)
09:12:31  INFO      Scroll 2/50 — found 5 new posts (11 total seen).
...
09:18:44  INFO      Feed exhausted — no new posts after 3 consecutive scrolls.

──────────────────────────────────────────────────
  Posts scraped:    47
  Emails found:     183
  New emails added: 176
──────────────────────────────────────────────────
```

Duplicate emails (already in Notion from a previous run) are silently skipped — you'll see `New emails added` be lower than `Emails found` on reruns.

### In Notion

Once complete, your Notion database will have a new row for every email found:

| Email | Source Post URL | Date Added | Status |
|---|---|---|---|
| jane@gmail.com | https://linkedin.com/feed/update/urn:... | March 28, 2026 | New |
| bob@outlook.com | https://linkedin.com/feed/update/urn:... | March 28, 2026 | New |
| sarah@company.com | https://linkedin.com/feed/update/urn:... | March 28, 2026 | New |

Every row starts with **Status: New** so you can filter your database by `Status = New` to see exactly what was just added.

### Getting emails into your newsletter tool

From your Notion database, export the emails and import them into your newsletter platform:

1. **Filter** your database to `Status = New`
2. **Export** as CSV (top right `...` → Export → CSV)
3. **Import** the CSV into your newsletter tool (Mailchimp, Beehiiv, ConvertKit, etc.)
4. **Update** the Status of imported rows to `Contacted` so you know they've been actioned

---

## Setup Guide

### 1. Save your LinkedIn session

```bash
python setup_auth.py
```

A browser window will open. Log into LinkedIn as you normally would, then come back to the terminal and press Enter. Your full session (all cookies) is saved to `auth_state.json`.

> If the scraper ever reports an authentication error, just run `python setup_auth.py` again.

---

### 2. Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **New integration**
3. Give it a name (e.g. "LinkScrape") and select your workspace
4. Under **Capabilities**, ensure **Read content**, **Insert content**, and **Read user information** are checked
5. Click **Submit** and copy the **Internal Integration Secret**
6. Paste it into `.env` as `NOTION_API_KEY=<your secret>`

---

### 3. Create the Notion Database

Create a new database in Notion with the following properties:

| Property Name    | Type   | Notes                                   |
|------------------|--------|-----------------------------------------|
| Email            | Title  | The primary field — must be Title type  |
| Source Post URL  | URL    | The LinkedIn post the email came from   |
| Date Added       | Date   | When the email was scraped              |
| Status           | Select | Options: New, Contacted, Unsubscribed   |

Then **share the database with your integration**:
1. Open the database in Notion
2. Click `...` (top right) → **Connections**
3. Search for and add your integration

Finally, copy the database ID from the URL:
```
notion.so/yourworkspace/<DATABASE_ID>?v=...
```
Paste it into `.env` as `NOTION_DATABASE_ID=<your id>`

---

## CLI Options

| Flag | Description | Default |
|---|---|---|
| `--max-scrolls N` | Number of feed scroll iterations | `50` (or `MAX_SCROLL_ITERATIONS` in `.env`) |
| `--no-headless` | Show the browser window | Hidden |
| `--dry-run` | Print emails to terminal, don't write to Notion | Off |

---

## Notion Database Schema

| Property        | Type   | Example Value                              |
|-----------------|--------|--------------------------------------------|
| Email           | Title  | jane@example.com                           |
| Source Post URL | URL    | https://linkedin.com/feed/update/urn:...   |
| Date Added      | Date   | 2026-03-28T14:32:00+00:00                  |
| Status          | Select | New                                        |

---

## Notes

- **Rate limiting**: LinkedIn scroll actions use randomised delays (default 3–7 s) to avoid pattern detection. Notion writes are throttled to stay within the 3 req/s API limit.
- **Deduplication**: On startup the tool fetches all existing emails from your Notion database. Emails already present are skipped — reruns are safe.
- **Selector changes**: LinkedIn periodically updates its UI. If scraping stops working, CSS selectors can be updated in the `SELECTORS` dict at the top of `scraper.py`.
