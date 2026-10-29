from datetime import date, datetime
from enum import IntEnum, StrEnum

from pydantic import BaseModel, computed_field


class TrainType(StrEnum):
    INTERNATIONAL = "international"
    INTERREGIONAL_BUSINESS = "interregional_business"
    INTERREGIONAL_ECONOMY = "interregional_economy"
    REGIONAL_BUSINESS = "regional_business"
    REGIONAL_ECONOMY = "regional_economy"


class CarType(IntEnum):
    UNNUMBERED = 0
    COMMON = 1
    SEATED = 2
    PLATZKART = 3
    COUPE = 4
    SOFT = 5
    SV = 6


class Station(BaseModel):
    exp: str
    name: str
    prefix: str
    label: str
    region: str
    lat: float | None = None
    lon: float | None = None


class TariffOffer(BaseModel):
    """Seats of one tariff on the route page. `free_seats` is None for unnumbered (commuter) seats."""

    car_type: int
    class_service: str
    free_seats: int | None
    prices_byn: list[float]
    is_bike_allowed: bool = False
    is_special: bool = False
    available: bool = True


class Train(BaseModel):
    train_id: str
    number: str
    train_type: str
    train_type_title: str
    route_title: str
    from_station: str
    to_station: str
    travel_date: date
    departure: datetime
    arrival: datetime
    duration_minutes: int
    selling_allowed: bool
    tariffs: list[TariffOffer]

    @computed_field
    @property
    def has_numbered_seats(self) -> bool:
        return self.train_type != TrainType.REGIONAL_ECONOMY

    @computed_field
    @property
    def free_seats(self) -> int:
        return sum(t.free_seats or 0 for t in self.tariffs)

    @computed_field
    @property
    def is_available(self) -> bool:
        if not self.selling_allowed:
            return False
        if self.has_numbered_seats:
            return self.free_seats > 0
        return any(t.available for t in self.tariffs)


class Car(BaseModel):
    number: str
    sub_type: str
    carrier: str
    empty_places: list[str]
    upper_places: int | None = None
    lower_places: int | None = None


class CarTariff(BaseModel):
    """One tariff from the car_places endpoint, with concrete free seat numbers per car."""

    class_service: str
    title: str
    price_byn: float | None
    is_bicycle: bool
    is_car_for_disabled: bool
    cars: list[Car]

    @computed_field
    @property
    def free_seats(self) -> int:
        return sum(len(car.empty_places) for car in self.cars)
