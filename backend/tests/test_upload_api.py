from fastapi.testclient import TestClient


def test_upload_requires_token(app_modules, excel_fixture_path):
    client = TestClient(app_modules["main"].app)
    with open(excel_fixture_path, "rb") as f:
        response = client.post("/admin/upload-excel", files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 401


def test_upload_wrong_token(app_modules, excel_fixture_path):
    client = TestClient(app_modules["main"].app)
    with open(excel_fixture_path, "rb") as f:
        response = client.post(
            "/admin/upload-excel",
            headers={"X-Admin-Token": "wrong-token"},
            files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert response.status_code == 401


def test_upload_ok(app_modules, excel_fixture_path, admin_token):
    client = TestClient(app_modules["main"].app)
    with open(excel_fixture_path, "rb") as f:
        response = client.post(
            "/admin/upload-excel",
            headers={"X-Admin-Token": admin_token},
            files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "inserted" in payload
    assert "updated" in payload
    assert "skipped" in payload
    assert "errors" in payload


def test_upload_bad_extension(app_modules, admin_token):
    client = TestClient(app_modules["main"].app)
    response = client.post(
        "/admin/upload-excel",
        headers={"X-Admin-Token": admin_token},
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_corrupt_excel(app_modules, admin_token):
    client = TestClient(app_modules["main"].app)
    response = client.post(
        "/admin/upload-excel",
        headers={"X-Admin-Token": admin_token},
        files={"file": ("test.xlsx", b"not-a-real-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code in (400, 500)
