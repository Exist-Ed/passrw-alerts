from datetime import date

import httpx
import pytest
import respx

from passrw_alerts.scraper import PassRwClient, PassRwError, Station

BASE_URL = "https://pass.rw.by"
MINSK = Station(exp="2100000", name="Минск", prefix="г.", label="г. Минск, Беларусь", region="Беларусь")
GOMEL = Station(exp="2100100", name="Гомель", prefix="г.", label="г. Гомель, Беларусь", region="Беларусь")


@respx.mock
async def test_get_trains_sends_names_and_codes(read_fixture):
    route = respx.get(f"{BASE_URL}/ru/route/").mock(
        return_value=httpx.Response(200, text=read_fixture("route_minsk_gomel.html"))
    )

    async with PassRwClient() as client:
        trains = await client.get_trains(MINSK, GOMEL, date(2026, 10, 17))

    assert len(trains) == 9
    params = route.calls.last.request.url.params
    assert dict(params) == {
        "from": "Минск",
        "from_exp": "2100000",
        "to": "Гомель",
        "to_exp": "2100100",
        "date": "2026-10-17",
    }


@respx.mock
async def test_get_car_places(read_fixture):
    respx.get(f"{BASE_URL}/ru/ajax/route/car_places/").mock(
        return_value=httpx.Response(200, text=read_fixture("car_places_612_coupe.json"))
    )

    async with PassRwClient() as client:
        tariffs = await client.get_car_places("2100000", "2100100", date(2026, 10, 17), "612Щ", 4)

    assert tariffs[0].free_seats == 16


@respx.mock
async def test_search_stations(read_fixture):
    respx.get(f"{BASE_URL}/ru/ajax/autocomplete/search/").mock(
        return_value=httpx.Response(200, text=read_fixture("autocomplete_gomel.json"))
    )

    async with PassRwClient() as client:
        stations = await client.search_stations("Гомель")

    assert stations[0].exp == "2100100"


@respx.mock
async def test_http_error_is_wrapped():
    respx.get(f"{BASE_URL}/ru/route/").mock(return_value=httpx.Response(503))

    async with PassRwClient() as client:
        with pytest.raises(PassRwError):
            await client.get_trains(MINSK, GOMEL, date(2026, 10, 17))
