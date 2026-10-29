# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram bot + Mini App that watches sold-out trains on pass.rw.by (Belarusian Railways) and alerts users when seats appear. Product decisions, research results and the staged roadmap live in `context/initial_context.md` (Russian, gitignored — exists only locally) — read it before designing new features; it is the source of truth for alert logic, subscription rules and stack choices.

Current state: stages 1–2 done (project skeleton + scraper). Planned next: MongoDB in Docker → snapshot worker → aiogram bot → FastAPI API → React Mini App (`@telegram-apps/telegram-ui`) → docker compose → home Linux server deploy → Metabase. Redis was explicitly rejected; MongoDB is the only datastore.

## Commands

Uses uv (Python pinned to 3.13 via `.python-version`).

```bash
uv sync                                         # install / sync .venv from uv.lock
uv run pytest                                   # all tests (offline, fixture-based)
uv run pytest tests/test_parsers.py::TestParseTrains::test_sold_out_train   # single test
uv run ruff check . && uv run ruff format .     # lint + format
uv run python -m passrw_alerts.scraper Минск Гомель 2026-10-20               # manual live check
```

`scripts/poll_test.py` is a stdlib-only long-running rate-limit probe (writes `logs/poll_test.jsonl`); it runs without the venv so it can be copied to the home server.

## pass.rw.by: hard-won facts

**Anti-bot is real.** Polling ~2 req/min triggered a HosterGuard JS challenge after ~10 minutes: every URL returns HTTP 200 with a ~1.2 KB `<title>Verification</title>` page (sets `hg-security` cookie, checks `navigator.webdriver`). It lifted within ~20 minutes after requests stopped. Consequences:
- Never hit the live site in tests; use `tests/fixtures/`. Keep manual live calls to a handful.
- Detect the challenge page explicitly — a 200 with zero trains is a block, not "no trains".
- Do not implement challenge bypasses (cookie solving, spoofing browser fingerprints). The site's rules (clause 81 of the e-ticket rules) also forbid scheduled automated searches; the user accepted the IP-ban risk, not circumvention.
- Safe polling frequency is still being determined (next: 1 route every 5 min). Keep interval/jitter in config.

**Data sources** (all unauthenticated):
- `GET /ru/route/?from=<name>&from_exp=<code>&to=<name>&to_exp=<code>&date=YYYY-MM-DD` — HTML with all trains of a route/date. Station **names are required**; codes alone return no trains. One request covers every train on the route, so polling is keyed by (from, to, date), not per user or train.
- Each sellable train row embeds a hidden `input.js-sch-item-route` holding a **PHP-serialized array** with per-tariff seat counts, prices and `is_bike_allowed` / `is_special` flags — decoded by `php_serialize.py` (lengths are UTF-8 bytes). Sold-out rows have no such input; only HTML attributes (`data-train-id` = `1_<number>_<dep_epoch>_<arr_epoch>`, real UTC epochs).
- `GET /ru/ajax/route/car_places/` — concrete free seat numbers per car. Sold-out trains return `{"e": {...}}`; a missing car type returns `"tariffs": []`. Both mean zero seats.
- `GET /ru/ajax/autocomplete/search/` — stations. Entries with `gid != "0"` have lat/lon swapped (normalized in the parser).
- No deep link to seat selection exists (it is a POST form; row elements have no `id`, and the site strips URL fragments). Alerts link to the route page and show train number + departure time prominently.

**Domain model:** a *tariff* = car type + class-service code + flags; class codes alone are ambiguous (`2Р` is bike-enabled in business trains, not in international ones). Commuter trains (`regional_economy`, `car_type=0`) have unnumbered seats and no counts — they are tracked only via the `available` / `ticket_selling_allowed` flags, without category selection.

## Code layout

`src/passrw_alerts/scraper/` separates I/O from parsing: `client.py` (async httpx, wraps HTTP errors in `PassRwError`) only fetches; `parsers.py` holds pure functions from raw HTML/JSON to pydantic models in `models.py`. New parsing logic should come with a saved fixture and an offline test. Times are stored as UTC-aware datetimes; convert to `Europe/Minsk` only for display.

## Conventions

- Talk to the user in Russian; code, comments, docs and commit-facing text in English.
- Don't commit or push — the user manages git.
- Ruff ignores RUF001–003 because Cyrillic literals are expected.
