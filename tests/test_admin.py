"""Administrator aggregate and room safety tests."""

from datetime import date, timedelta


def test_stats_aggregates(client, admin_token, auth_headers):
    response = client.get("/api/admin/stats", headers=auth_headers(admin_token))
    assert response.status_code == 200
    stats = response.get_json()["data"]
    assert stats["total_customers"] == 1
    assert stats["active_bookings"] == 0
    assert stats["room_status_counts"]["available"] == 1


def test_room_delete_blocked_by_future_booking(
    client, customer_token, admin_token, auth_headers
):
    start = date.today() + timedelta(days=15)
    payload = {
        "room_id": 1,
        "check_in": start.isoformat(),
        "check_out": (start + timedelta(days=2)).isoformat(),
        "guests": 1,
    }
    assert (
        client.post(
            "/api/bookings", json=payload, headers=auth_headers(customer_token)
        ).status_code
        == 201
    )
    response = client.delete("/api/admin/rooms/1", headers=auth_headers(admin_token))
    assert response.status_code == 409
