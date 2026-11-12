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
    assert data["service"] == "payment-service"


def test_process_and_fetch_payment():
    payload = {
        "order_id": 101,
        "user_id": 1,
        "amount": 14999.0,
        "payment_method": "UPI"
    }
    res = client.post("/api/v1/payments/process", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["transaction_id"].startswith("TXN-")

    payment_id = data["id"]
    get_res = client.get(f"/api/v1/payments/{payment_id}")
    assert get_res.status_code == 200
    assert get_res.json()["order_id"] == 101