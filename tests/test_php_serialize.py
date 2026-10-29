import pytest

from passrw_alerts.scraper import php_serialize


def test_scalars():
    assert php_serialize.loads("N;") is None
    assert php_serialize.loads("b:1;") is True
    assert php_serialize.loads("i:-42;") == -42
    assert php_serialize.loads("d:19.92;") == 19.92


def test_string_length_is_in_bytes():
    assert php_serialize.loads('s:12:"Гомель";') == "Гомель"


def test_nested_array():
    data = 'a:2:{s:4:"name";s:5:"612Щ";s:6:"places";a:2:{i:0;i:47;i:1;i:16;}}'
    assert php_serialize.loads(data) == {"name": "612Щ", "places": {0: 47, 1: 16}}


def test_as_list_orders_by_key():
    assert php_serialize.as_list({1: "b", 0: "a"}) == ["a", "b"]
    assert php_serialize.as_list(None) == []


@pytest.mark.parametrize("bad", ['s:10:"short";', "a:1:{i:0;", "x:1;", "i:1;junk"])
def test_malformed_input_raises(bad):
    with pytest.raises(php_serialize.PhpUnserializeError):
        php_serialize.loads(bad)
