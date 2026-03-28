# LinkScrape

Automatically collect emails from LinkedIn "drop your email" posts and add them to your Notion newsletter database.

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

### Configure

```bash
cp .env.example .env
# Fill in your credentials — see Setup Guide below
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
2. You grab your `li_at` cookie from your browser (30 seconds, one-time)
3. You set up a Notion integration and database (5 minutes, one-time)
4. You fill in `.env` with your credentials
5. You run `python main.py`
6. The tool opens a headless browser, scrolls your feed, expands all comment sections, and finds every email address
7. All emails appear in Notion tagged `New`, ready to export into Mailchimp, Beehiiv, ConvertKit, or any other newsletter tool

---

## Setup Guide

### 1. Get your LinkedIn `li_at` cookie

This is your LinkedIn session identifier. It lets the tool browse LinkedIn as you, without triggering a login form or 2FA.

1. Log into [LinkedIn](https://www.linkedin.com) in Chrome or Firefox
2. Open DevTools: press `F12` (or right-click → Inspect)
3. Go to **Application** tab → **Cookies** → `https://www.linkedin.com`
4. Find the cookie named `li_at` and copy its **Value**
5. Paste it into `.env` as `LINKEDIN_LI_AT_COOKIE=<your value>`

> The cookie expires after roughly a year, or sooner if you log out of all sessions. If the tool reports an auth error, refresh this value.

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
