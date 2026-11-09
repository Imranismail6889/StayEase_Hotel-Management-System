"""Authenticated review and loyalty account endpoints."""


def test_my_reviews_and_loyalty_are_private(client, customer_token, auth_headers):
    headers = auth_headers(customer_token)

    reviews = client.get("/api/reviews", headers=headers)
    loyalty = client.get("/api/loyalty", headers=headers)

    assert reviews.status_code == 200
    assert reviews.get_json()["data"]["items"] == []
    assert loyalty.status_code == 200
    assert loyalty.get_json()["data"] == {
        "points": 0,
        "tier": "Silver",
        "items": [],
    }
    assert client.get("/api/reviews").status_code == 401
    assert client.get("/api/loyalty").status_code == 401
