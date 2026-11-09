"""Authentication and authorization API tests."""


def test_register_and_duplicate_email(client):
    data = {
        "name": "New Guest",
        "email": "new@example.com",
        "phone": "555-0111",
        "password": "Strongpass123!",
    }
    first = client.post("/api/auth/register", json=data)
    assert first.status_code == 201
    assert first.get_json()["data"]["user"]["email"] == data["email"]
    assert client.post("/api/auth/register", json=data).status_code == 409


def test_login_success_and_failure(client):
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "guest@example.com", "password": "Guestpass123!"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "guest@example.com", "password": "wrong-password"},
        ).status_code
        == 401
    )


def test_protected_route_and_admin_guard(client, customer_token, auth_headers):
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.get("/api/auth/me", headers=auth_headers(customer_token)).status_code
        == 200
    )
    assert (
        client.get("/api/admin/stats", headers=auth_headers(customer_token)).status_code
        == 403
    )
