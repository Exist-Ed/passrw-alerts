# passrw_alerts

> [!WARNING]
> **This is an educational pet project, built purely to learn Telegram bots, Mini Apps, MongoDB and Docker. It is not a public service and is not intended for production use.**
>
> pass.rw.by (Belarusian Railways) prohibits automated access to its booking service. Clause 81 of the
> [Rules for issuing and using electronic tickets for trains with numbered seats](https://pass.rw.by/ru/help/travel-documents-tickets/electronic-travel-documents/rules-of-registration-and-use-of-electronic-travel-documents-tickets-on-trains-with-numbered-seats-.html)
> lists, among violations leading to account blocking, *regular search queries for specific routes sent on a time
> pattern (every hour at a certain time / every N minutes, etc.)* and ticket purchases using robotic requests.
> The site also runs active anti-bot protection. Do not use this code to poll the site — doing so violates its rules.
> The author takes no responsibility for any use of this code.

Telegram bot + Mini App that watches sold-out trains on [pass.rw.by](https://pass.rw.by) and alerts you when seats appear.

## Status

| Stage | State |
|---|---|
| 0. Polling test (`scripts/poll_test.py`) | ✅ anti-bot challenge triggered after ~10 min at ~2 req/min |
| 1. Project skeleton | ✅ |
| 2. pass.rw.by scraper | ✅ |
| 3+ (MongoDB, worker, bot, API, Mini App, Docker, Metabase) | planned |

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # create .venv and install deps
uv run pytest           # tests (offline, use saved fixtures)
uv run ruff check .     # lint
uv run ruff format .    # format
```

Try the scraper against the live site (a single request, not polling):

```bash
uv run python -m passrw_alerts.scraper Минск Гомель 2026-10-20
```

## Layout

```
src/passrw_alerts/
  scraper/
    client.py         # async HTTP client for pass.rw.by (httpx)
    parsers.py        # raw HTML/JSON -> models, no network
    models.py         # pydantic models: Station, Train, TariffOffer, CarTariff
    php_serialize.py  # decoder for the PHP-serialized train data embedded in the page
    __main__.py       # CLI for manual checks
tests/
  fixtures/           # saved pass.rw.by responses
scripts/
  poll_test.py        # long-running rate-limit / anti-bot test, stdlib only
```

## How pass.rw.by data is obtained

- `GET /ru/route/?from=…&from_exp=…&to=…&to_exp=…&date=…` — all trains of a route for a date. Every train row with tickets
  for sale has a hidden `route` input with PHP-serialized data: per-tariff free seat counts, prices, bike / disabled flags.
  Sold-out trains have no such input, only basic attributes.
- `GET /ru/ajax/route/car_places/` — concrete free seat numbers per car. Sold-out trains answer with `{"e": …}`.
- `GET /ru/ajax/autocomplete/search/?term=…` — stations with codes (`exp`).
