from datetime import date
from types import TracebackType
from typing import Self

import httpx

from passrw_alerts.scraper.models import CarTariff, Station, Train
from passrw_alerts.scraper.parsers import parse_car_places, parse_stations, parse_trains

DEFAULT_BASE_URL = "https://pass.rw.by"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "ru,en;q=0.8",
}


class PassRwError(RuntimeError):
    pass


class PassRwClient:
    """Async client for pass.rw.by. Use as `async with PassRwClient() as client: ...`."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 30, http: httpx.AsyncClient | None = None):
        self._http = http or httpx.AsyncClient(base_url=base_url, headers=DEFAULT_HEADERS, timeout=timeout)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ):
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    async def search_stations(self, term: str) -> list[Station]:
        response = await self._get("/ru/ajax/autocomplete/search/", {"term": term})
        return parse_stations(response.json())

    async def get_trains(self, origin: Station, destination: Station, travel_date: date) -> list[Train]:
        """Both station name and code are required: the site returns no trains without names."""
        params = {
            "from": origin.name,
            "from_exp": origin.exp,
            "to": destination.name,
            "to_exp": destination.exp,
            "date": travel_date.isoformat(),
        }
        response = await self._get("/ru/route/", params)
        return parse_trains(response.text)

    async def get_car_places(
        self, origin_exp: str, destination_exp: str, travel_date: date, train_number: str, car_type: int
    ) -> list[CarTariff]:
        params = {
            "from": origin_exp,
            "to": destination_exp,
            "date": travel_date.isoformat(),
            "train_number": train_number,
            "car_type": car_type,
        }
        response = await self._get("/ru/ajax/route/car_places/", params)
        return parse_car_places(response.json())

    async def _get(self, path: str, params: dict[str, str | int]) -> httpx.Response:
        try:
            response = await self._http.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise PassRwError(f"GET {path} failed: {error}") from error
        return response
