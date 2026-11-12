import sys
import os
from fastapi.testclient import TestClient

# Add user-service directory to Python path so we can import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "user-service"


def test_register_and_login_user():
    # 1. Register a new user
    register_payload = {
        "username": "testuser_ci",
        "email": "ci_test@example.com",
        "password": "TestPassword123",
        "full_name": "CI Test User"
    }
    reg_res = client.post("/api/v1/users/register", json=register_payload)
    assert reg_res.status_code == 201
    assert reg_res.json()["email"] == "ci_test@example.com"

    # 2. Test duplicate registration rejection
    dup_res = client.post("/api/v1/users/register", json=register_payload)
    assert dup_res.status_code == 400

    # 3. Test valid login
    login_res = client.post("/api/v1/users/login", json={
        "email": "ci_test@example.com",
        "password": "TestPassword123"
    })
    assert login_res.status_code == 200
    assert login_res.json()["message"] == "Login successful"

    # 4. Test invalid password login
    bad_login = client.post("/api/v1/users/login", json={
        "email": "ci_test@example.com",
        "password": "WrongPassword"
    })
    assert bad_login.status_code == 401