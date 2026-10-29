"""Pure functions turning raw pass.rw.by responses into models. No network here."""

import json
import re
from datetime import UTC, date, datetime
from typing import Any

from selectolax.lexbor import LexborHTMLParser, LexborNode

from passrw_alerts.scraper import php_serialize
from passrw_alerts.scraper.models import Car, CarTariff, Station, TariffOffer, Train


class ParseError(ValueError):
    pass


def parse_stations(payload: list[dict[str, Any]]) -> list[Station]:
    stations = []
    for item in payload:
        lat, lon = item.get("lat"), item.get("lon")
        # Station entries (gid != "0") come with lat/lon swapped; city entries are correct.
        if item.get("gid", "0") != "0":
            lat, lon = lon, lat
        stations.append(
            Station(
                exp=item["exp"],
                name=item["value"],
                prefix=item.get("prefix", ""),
                label=item.get("label", item["value"]),
                region=item.get("label_tail", ""),
                lat=lat,
                lon=lon,
            )
        )
    return stations


def parse_trains(html: str) -> list[Train]:
    tree = LexborHTMLParser(html)
    return [_parse_train_row(row) for row in tree.css("div.sch-table__row[data-train-id]")]


def parse_car_places(payload: dict[str, Any]) -> list[CarTariff]:
    """An `{"e": ...}` payload is how the site answers for sold-out trains: treat it as no seats."""
    if "e" in payload:
        return []
    return [
        CarTariff(
            class_service=tariff.get("typeAbbr", ""),
            title=tariff.get("type", ""),
            price_byn=_parse_decimal(tariff.get("price_byn")),
            is_bicycle=bool(tariff.get("isBicycle")),
            is_car_for_disabled=bool(tariff.get("is_car_for_disabled")),
            cars=[
                Car(
                    number=car["number"],
                    sub_type=car.get("subType", ""),
                    carrier=car.get("carrier", ""),
                    empty_places=car.get("emptyPlaces", []),
                    upper_places=car.get("upperPlaces"),
                    lower_places=car.get("lowerPlaces"),
                )
                for car in tariff.get("cars", [])
            ],
        )
        for tariff in payload.get("tariffs", [])
    ]


def _parse_train_row(row: LexborNode) -> Train:
    attrs = row.attributes
    train_id = attrs.get("data-train-id") or ""
    try:
        *_, departure_ts, arrival_ts = train_id.split("_")
        departure = datetime.fromtimestamp(int(departure_ts), UTC)
        arrival = datetime.fromtimestamp(int(arrival_ts), UTC)
    except ValueError as error:
        raise ParseError(f"unexpected train id {train_id!r}") from error

    route_input = row.css_first("input.js-sch-item-route")
    route = php_serialize.loads(route_input.attributes["value"]) if route_input else None

    return Train(
        train_id=train_id,
        number=attrs.get("data-train-number") or "",
        train_type=attrs.get("data-train-type") or "",
        train_type_title=_text(row, ".sch-table__route-type"),
        route_title=_text(row, ".train-route"),
        from_station=_text(row, ".train-from-name"),
        to_station=_text(row, ".train-to-name"),
        travel_date=_travel_date(row, route),
        departure=departure,
        arrival=arrival,
        duration_minutes=int(_attr(row, ".train-duration-time", "data-value") or 0),
        selling_allowed=attrs.get("data-ticket_selling_allowed") == "true",
        tariffs=_parse_tariffs(route) if route else [],
    )


def _parse_tariffs(route: dict[str, Any]) -> list[TariffOffer]:
    offers = []
    for place in php_serialize.as_list(route.get("places")):
        car_type = int(place["car_type"])
        multi = php_serialize.as_list(place.get("price_multi"))
        if multi:
            offers.extend(
                TariffOffer(
                    car_type=car_type,
                    class_service=item.get("classservice", ""),
                    free_seats=int(item.get("places") or 0),
                    prices_byn=[float(p) for p in php_serialize.as_list(item.get("prices"))],
                    is_bike_allowed=bool(item.get("is_bike_allowed")),
                    is_special=bool(item.get("is_special")),
                )
                for item in multi
            )
        else:
            free_seats = place.get("free_seats")
            price = place.get("price")
            offers.append(
                TariffOffer(
                    car_type=car_type,
                    class_service="",
                    free_seats=int(free_seats) if str(free_seats).isdigit() else None,
                    prices_byn=[float(price)] if isinstance(price, int | float) else [],
                    available=bool(place.get("available", True)),
                )
            )
    return offers


def _travel_date(row: LexborNode, route: dict[str, Any] | None) -> date:
    if route and route.get("train_dep_date"):
        return date.fromisoformat(route["train_dep_date"])
    wrap = row.parent
    info = wrap.attributes.get("data-train-info") if wrap else None
    if not info:
        raise ParseError(f"no travel date for train {row.attributes.get('data-train-id')}")
    return date.fromisoformat(json.loads(info)["date"])


def _text(node: LexborNode, selector: str) -> str:
    found = node.css_first(selector)
    return re.sub(r"\s+", " ", found.text()).strip() if found else ""


def _attr(node: LexborNode, selector: str, name: str) -> str | None:
    found = node.css_first(selector)
    return found.attributes.get(name) if found else None


def _parse_decimal(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(" ", "").replace(",", "."))
    except ValueError:
        return None
