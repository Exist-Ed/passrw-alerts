from datetime import UTC, date, datetime

from passrw_alerts.scraper.models import CarType, TrainType
from passrw_alerts.scraper.parsers import parse_car_places, parse_stations, parse_trains


def trains_by_number(html):
    return {train.number: train for train in parse_trains(html)}


class TestParseTrains:
    def test_minsk_gomel_parses_all_trains(self, read_fixture):
        trains = parse_trains(read_fixture("route_minsk_gomel.html"))

        assert len(trains) == 9
        assert [t.departure for t in trains] == sorted(t.departure for t in trains)

    def test_train_fields(self, read_fixture):
        train = trains_by_number(read_fixture("route_minsk_gomel.html"))["612Щ"]

        assert train.train_id == "1_612Щ_1792257960_1792270740"
        assert train.train_type == TrainType.INTERREGIONAL_ECONOMY
        assert train.train_type_title == "Межрегиональные линии экономкласса"
        assert train.route_title == "Минск-Пассажирский — Гомель"
        assert train.from_station == "Минск-Пассажирский"
        assert train.to_station == "Гомель"
        assert train.travel_date == date(2026, 10, 17)
        assert train.departure == datetime(2026, 10, 17, 17, 26, tzinfo=UTC)
        assert train.duration_minutes == 213
        assert train.selling_allowed

    def test_tariffs_come_from_serialized_route(self, read_fixture):
        train = trains_by_number(read_fixture("route_minsk_gomel.html"))["612Щ"]

        assert [(t.car_type, t.class_service, t.free_seats) for t in train.tariffs] == [
            (CarType.PLATZKART, "3У", 47),
            (CarType.COUPE, "2У", 16),
        ]
        assert train.tariffs[0].prices_byn == [19.92]
        assert train.free_seats == 63
        assert train.is_available

    def test_bike_and_special_flags(self, read_fixture):
        trains = trains_by_number(read_fixture("route_minsk_gomel.html"))

        bike = [t for t in trains["716Б"].tariffs if t.class_service == "2Р"]
        assert bike and bike[0].is_bike_allowed
        assert any(t.is_special for t in trains["756Б"].tariffs)

    def test_sold_out_train(self, read_fixture):
        train = trains_by_number(read_fixture("route_minsk_gomel.html"))["758Б"]

        assert train.tariffs == []
        assert train.free_seats == 0
        assert not train.is_available
        assert train.travel_date == date(2026, 10, 17)

    def test_international_train_has_multiple_prices(self, read_fixture):
        trains = parse_trains(read_fixture("route_minsk_moscow.html"))

        assert trains and all(t.train_type == TrainType.INTERNATIONAL for t in trains)
        assert any(len(tariff.prices_byn) > 1 for t in trains for tariff in t.tariffs)

    def test_commuter_trains_have_unnumbered_seats(self, read_fixture):
        commuters = [
            t
            for t in parse_trains(read_fixture("route_minsk_molodechno.html"))
            if t.train_type == TrainType.REGIONAL_ECONOMY
        ]

        assert len(commuters) == 16
        train = commuters[0]
        assert not train.has_numbered_seats
        assert train.tariffs[0].car_type == CarType.UNNUMBERED
        assert train.tariffs[0].free_seats is None
        assert train.tariffs[0].prices_byn == [4.26]
        assert train.is_available


class TestParseCarPlaces:
    def test_seat_numbers(self, load_json):
        tariffs = parse_car_places(load_json("car_places_612_coupe.json"))

        assert len(tariffs) == 1
        tariff = tariffs[0]
        assert tariff.class_service == "2У"
        assert tariff.price_byn == 27.65
        assert not tariff.is_bicycle
        car = tariff.cars[0]
        assert car.number == "04"
        assert car.empty_places[:3] == ["017", "018", "019"]
        assert (car.upper_places, car.lower_places) == (10, 6)
        assert tariff.free_seats == 16

    def test_sold_out_error_payload_means_no_seats(self, load_json):
        assert parse_car_places(load_json("car_places_error.json")) == []

    def test_missing_car_type_means_no_seats(self, load_json):
        assert parse_car_places(load_json("car_places_no_tariffs.json")) == []


class TestParseStations:
    def test_stations(self, load_json):
        stations = parse_stations(load_json("autocomplete_gomel.json"))

        city, station = stations[0], stations[1]
        assert (city.exp, city.name, city.prefix) == ("2100100", "Гомель", "г.")
        assert station.prefix == "ст."
        assert station.region == "г. Гомель, Гомельская обл., Беларусь"

    def test_coordinates_are_normalized(self, load_json):
        for station in parse_stations(load_json("autocomplete_gomel.json")):
            assert 51 < station.lat < 53
            assert 30 < station.lon < 32
