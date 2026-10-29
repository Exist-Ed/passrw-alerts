"""Manual check against the live site: python -m passrw_alerts.scraper Минск Гомель 2026-10-20"""

import argparse
import asyncio
from datetime import date
from zoneinfo import ZoneInfo

from passrw_alerts.scraper import PassRwClient

MINSK_TZ = ZoneInfo("Europe/Minsk")


async def main(origin_term: str, destination_term: str, travel_date: date) -> None:
    async with PassRwClient() as client:
        origin = (await client.search_stations(origin_term))[0]
        destination = (await client.search_stations(destination_term))[0]
        trains = await client.get_trains(origin, destination, travel_date)

    print(f"{origin.name} → {destination.name}, {travel_date}: {len(trains)} trains\n")
    for train in trains:
        departure = train.departure.astimezone(MINSK_TZ).strftime("%H:%M")
        if not train.has_numbered_seats:
            seats = "sold out" if not train.is_available else "on sale (unnumbered seats)"
        elif not train.tariffs:
            seats = "sold out"
        else:
            seats = ", ".join(f"{t.class_service or t.car_type}: {t.free_seats}" for t in train.tariffs)
        print(f"{departure}  {train.number:<6} {train.train_type:<24} {seats}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("origin")
    parser.add_argument("destination")
    parser.add_argument("date", type=date.fromisoformat)
    args = parser.parse_args()
    asyncio.run(main(args.origin, args.destination, args.date))
