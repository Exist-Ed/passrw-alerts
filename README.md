A Telegram bot with a Mini App that tracks sold-out trains on [pass.rw.by](https://pass.rw.by) and sends a message when seats become available.

> [!WARNING]
> **This is an educational pet project, built purely to learn Telegram bots, Mini Apps, MongoDB and Docker. It is not a public service.**
>
> pass.rw.by prohibits automated access: clause 81 of its
> [e-ticket rules](https://pass.rw.by/ru/help/travel-documents-tickets/electronic-travel-documents/rules-of-registration-and-use-of-electronic-travel-documents-tickets-on-trains-with-numbered-seats-.html)
> treats *regular search queries for specific routes sent on a time pattern* as a violation, and the site runs active
> anti-bot protection. Do not use this code to poll the site. The author takes no responsibility for any use of this code.

## The problem

Popular Belarusian trains often sell out days in advance. Seats still come back when tickets are returned, extra cars are added or unfinished bookings expire, but they are bought again within minutes. Today the only way to catch one is to keep reloading the site by hand.

## The idea

1. In the Mini App, pick the stations and a date, choose a train and the seat categories you need (seated, platzkart, coupe, SV, bike, accessible).
2. When new seats appear, the bot sends one message containing:
   - the train and the seats that appeared;
   - the total number of free seats;
   - a link to the site;
   - **"Got a ticket"** / **"Keep searching"** buttons.
3. Alerts continue until you confirm the purchase or the train departs. Subscriptions are listed in **"My trains"**.

The bot never buys tickets; you buy them yourself on the official site.

## Architecture (planned)

A worker fetches each tracked route once for all subscribers and compares free seats with the previous snapshot. An aiogram bot delivers the alerts. A FastAPI backend serves the React Mini App. Data is stored in MongoDB, with Metabase for statistics. Everything runs with `docker compose` on a home server, and the Mini App is exposed through Cloudflare Tunnel.

**Stack:** Python 3.13, uv, httpx, selectolax, pydantic, aiogram 3, FastAPI, MongoDB, React + `@telegram-apps/telegram-ui`, Docker, Metabase.

## Status

- ✅ Project skeleton and the pass.rw.by scraper with offline tests.
- ✅ Rate-limit test: the anti-bot challenge triggered after ~10 minutes at ~2 requests per minute.
- ⏳ Worker, bot, API, Mini App, Docker setup.

## Development

```bash
uv sync                 # install deps (requires uv)
uv run pytest           # offline tests on saved fixtures
uv run ruff check .     # lint
uv run ruff format .    # format
uv run python -m passrw_alerts.scraper Минск Гомель 2026-10-20   # one live request
```

The scraper lives in `src/passrw_alerts/scraper/`:
- `client.py` handles HTTP;
- `parsers.py` turns raw HTML/JSON into pydantic models without network access;
- `php_serialize.py` decodes the PHP-serialized train data embedded in the route page.
