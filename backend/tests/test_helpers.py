import pandas as pd

from app import data_loader


def test_clean_doi():
    for value in ["x", "X", "-", "", pd.NA, "nan", "none", "null"]:
        assert data_loader.clean_doi(value) is None
    assert data_loader.clean_doi(" 10.1000/test001 ") == "10.1000/test001"


def test_parse_year():
    assert data_loader.parse_year(2020) == 2020
    assert data_loader.parse_year(2021.0) == 2021
    assert data_loader.parse_year("2022") == 2022
    assert data_loader.parse_year("invalid") is None
    assert data_loader.parse_year(pd.NA) is None


def test_clean_text_and_nullable():
    assert data_loader.clean_text("  hello ") == "hello"
    assert data_loader.clean_text(pd.NA) is None
    assert data_loader.clean_nullable_text("   ") is None
    assert data_loader.clean_nullable_text(" ok ") == "ok"


def test_is_marked():
    for value in [1, 1.0, "v", "V", "y", "yes", "true", "x"]:
        assert data_loader.is_marked(value) is True
    for value in ["", pd.NA, "0", "no", "false"]:
        assert data_loader.is_marked(value) is False
