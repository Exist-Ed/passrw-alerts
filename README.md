# passrw_alerts

Telegram bot + Mini App that watches sold-out trains on [pass.rw.by](https://pass.rw.by) and alerts you when seats appear.

Project context, decisions and roadmap: [initial_context.md](initial_context.md).

## Status

| Stage | State |
|---|---|
| 0. Polling test (`scripts/poll_test.py`) | 🔄 running |
| 1. Project skeleton | ✅ |
| 2. pass.rw.by scraper | ✅ |
| 3+ | planned |

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # create .venv and install deps
uv run pytest           # tests (offline, use saved fixtures)
uv run ruff check .     # lint
uv run ruff format .    # format
```

Try the scraper against the live site:

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
  poll_test.py        # long-running ban/captcha test, stdlib only
```

## How pass.rw.by data is obtained

- `GET /ru/route/?from=…&from_exp=…&to=…&to_exp=…&date=…` — all trains of a route for a date. Every train row with tickets
  for sale has a hidden `route` input with PHP-serialized data: per-tariff free seat counts, prices, bike / disabled flags.
  Sold-out trains have no such input, only basic attributes.
- `GET /ru/ajax/route/car_places/` — concrete free seat numbers per car. Sold-out trains answer with `{"e": …}`.
- `GET /ru/ajax/autocomplete/search/?term=…` — stations with codes (`exp`).
