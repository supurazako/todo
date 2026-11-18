# Tasks

Minimal single-owner TODO and household finance web app at https://task.supurazako.com.
Flask + Waitress + SQLite; browser JavaScript has no build step.

## Features and design

- Owner: TODO CRUD and JPY income/expense CRUD with date and description.
- Monthly income, expense and net totals. Net is not a bank-account balance.
- Existing shared viewer key reads **both TODOs and all finance records**, including summaries;
  only the owner can mutate either resource. Anonymous visitors see neither.
- UI adapted from tokuzou0829/my-todo-app; provenance and reported permission are in DESIGN_SOURCE.md.
- No new runtime dependencies or separate database server. Startup adds only
  `finance_entries` and its index to the existing SQLite store, leaving TODOs unchanged.
- A private consistent pre-migration backup was taken at `~/.config/chronos-todo/pre-finance.db`.
- Existing keys continue to work. Rotate the viewer key if its holders should no longer see finance.

## Install and test

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
node --check static/app.js
```

## Configuration

Required environment variables: `TODO_SESSION_SECRET`, `TODO_OWNER_KEY`,
`TODO_VIEWER_KEY`, `TODO_DATABASE`. Generate long random independent keys.
Database must already contain the Chronos `todo_items` table (see REQUIREMENTS.md).
The application fails closed if this database is missing; it never initializes a replacement.
`TODO_PORT` defaults to 8786. Run `.venv/bin/python app.py`.
Waitress binds only 127.0.0.1; HTTPS is supplied by Cloudflare Tunnel.
Origin is fixed to https://task.supurazako.com; adapt config deliberately for another origin.

## Current deployment

- App: user systemd unit `chronos-todo.service`
- Tunnel: user systemd unit `chronos-todo-tunnel.service`
- Secrets: `~/.config/chronos-todo/app.env` (mode 0600, never commit)
- Tunnel config: `~/.config/chronos-todo/tunnel.yml`
- Shared database: calendar-owner profile's existing SQLite database

```sh
systemctl --user status chronos-todo chronos-todo-tunnel
systemctl --user restart chronos-todo
systemctl --user stop chronos-todo-tunnel chronos-todo
```

Retrieve keys locally from the environment file; do not post the owner key in a shared channel.
After replacing a key, restart the app: all existing sessions are invalidated.
The signed cookie contains a role and opaque generation identifier, not the access key.
A global per-process login-failure limiter is intentionally simple; it resets on restart
and may temporarily block legitimate login after repeated failed attempts.

The existing reminder remains unchanged and reads the same `todo_items` table.
Before future schema changes, stop writers and take a consistent SQLite backup;
do not delete existing data or commit backups.

`smoke_browser.py` is an opt-in deployment test requiring Playwright/Chromium and
local deployment secrets. It checks both roles over public HTTPS without modifying TODOs.
Unit tests cover CRUD and reminder-query compatibility using an isolated temporary database.

Optional browser checks:
```sh
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python browser_crud.py  # isolated database; complete CRUD test
.venv/bin/python smoke_browser.py  # public deployment; no data mutations
```
