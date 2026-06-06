from fastapi.testclient import TestClient


def test_search_after_import(app_modules, excel_fixture_path):
    load_data = app_modules["data_loader"].load_data
    load_data(str(excel_fixture_path))

    client = TestClient(app_modules["main"].app)

    response = client.get("/search", params={"q": "Policy"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["title"] == "EMI Policy in Higher Education" for item in payload["items"])

    response = client.get("/search", params={"q": "classrooms"})
    assert response.status_code == 200
    payload = response.json()
    assert any("Classrooms" in item["title"] for item in payload["items"]) or payload["total"] >= 1

    response = client.get("/search", params={"year_from": 2021, "year_to": 2022})
    assert response.status_code == 200
    payload = response.json()
    years = {item["year"] for item in payload["items"]}
    assert 2020 not in years

    response = client.get("/search", params={"page": 1, "page_size": 2})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) <= 2

    response = client.get("/search", params={"sort": "year_desc"})
    assert response.status_code == 200
    payload = response.json()
    years = [item["year"] for item in payload["items"] if item["year"] is not None]
    if len(years) >= 2:
        assert years == sorted(years, reverse=True)
