"""Tests for cloud cart endpoints."""

def test_cart_requires_auth(client):
    res = client.get("/api/cart")
    assert res.status_code == 401


def test_cart_add_update_remove_flow(client):
    # Register a user
    import uuid
    email = f"cartuser_{uuid.uuid4().hex[:6]}@example.com"
    reg = client.post("/api/auth/register", json={
        "name": "Cart Tester",
        "email": email,
        "password": "password123",
        "password_confirmation": "password123",
    })
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Initially empty
    res = client.get("/api/cart", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"] == []

    # Add item
    add_res = client.post("/api/cart", json={
        "product_id": 1,
        "quantity": 2,
        "size": "41mm",
        "color": "Silver",
    }, headers=headers)
    assert add_res.status_code == 200
    data = add_res.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["quantity"] == 2
    assert data[0]["size"] == "41mm"

    # Update quantity
    update_res = client.put("/api/cart", json={
        "product_id": 1,
        "quantity": 5,
        "size": "41mm",
        "color": "Silver",
    }, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["data"][0]["quantity"] == 5

    # Delete item
    del_res = client.delete("/api/cart?product_id=1&size=41mm&color=Silver", headers=headers)
    assert del_res.status_code == 200
    assert len(del_res.json()["data"]) == 0
