import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "order-service"


def test_create_and_update_order():
    # 1. Create a new order
    payload = {
        "user_id": 1,
        "product_name": "Nespresso Vertuo Machine",
        "quantity": 2,
        "total_amount": 25000.0
    }
    create_res = client.post("/api/v1/orders", json=payload)
    assert create_res.status_code == 201
    order_data = create_res.json()
    assert order_data["product_name"] == "Nespresso Vertuo Machine"
    assert order_data["status"] == "PENDING"
    order_id = order_data["id"]

    # 2. Fetch order details
    get_res = client.get(f"/api/v1/orders/{order_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == order_id

    # 3. Update order status
    patch_res = client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "CONFIRMED"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "CONFIRMED"