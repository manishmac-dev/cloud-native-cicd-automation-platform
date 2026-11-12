import os
import logging
from datetime import datetime, timezone
from typing import Dict, List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# 1. Structured Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [USER-SERVICE] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 2. FastAPI App Initialization
SERVICE_NAME = os.getenv("SERVICE_NAME", "user-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

app = FastAPI(
    title="User Service API",
    description="Microservice handling user registration, authentication, and profile management.",
    version=SERVICE_VERSION
)

# 3. Data Validation Schemas (Pydantic)
class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, examples=["manish_devops"])
    email: str = Field(..., examples=["manish@example.com"])
    password: str = Field(..., min_length=6, examples=["StrongPass123"])
    full_name: str = Field(..., examples=["Manish Kumar"])

class UserLoginRequest(BaseModel):
    email: str = Field(..., examples=["manish@example.com"])
    password: str = Field(..., examples=["StrongPass123"])

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    created_at: str

# 4. Temporary In-Memory Store (Will be replaced by PostgreSQL in Phase 2)
users_db: Dict[int, dict] = {}
user_id_counter = 1

# 5. Health Check Endpoint (Critical for Docker & Kubernetes Probes)
@app.get("/health", tags=["Health"])
def health_check():
    logger.info("Health check endpoint called")
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# 6. User Registration Endpoint
@app.post("/api/v1/users/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
def register_user(user: UserRegisterRequest):
    global user_id_counter

    for existing_user in users_db.values():
        if existing_user["email"] == user.email:
            logger.warning(f"Registration failed: Email {user.email} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    new_user = {
        "id": user_id_counter,
        "username": user.username,
        "email": user.email,
        "password": user.password,
        "full_name": user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    users_db[user_id_counter] = new_user
    user_id_counter += 1

    logger.info(f"User registered successfully: {user.username} (ID: {new_user['id']})")
    return new_user

# 7. User Login Endpoint
@app.post("/api/v1/users/login", tags=["Users"])
def login_user(credentials: UserLoginRequest):
    for user in users_db.values():
        if user["email"] == credentials.email and user["password"] == credentials.password:
            logger.info(f"User logged in: {credentials.email}")
            return {
                "message": "Login successful",
                "user_id": user["id"],
                "username": user["username"]
            }

    logger.warning(f"Failed login attempt for: {credentials.email}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password"
    )

# 8. Get All Users Endpoint
@app.get("/api/v1/users", response_model=List[UserResponse], tags=["Users"])
def list_users():
    return list(users_db.values())

# 9. Get Single User Profile Endpoint
@app.get("/api/v1/users/{user_id}", response_model=UserResponse, tags=["Users"])
def get_user_profile(user_id: int):
    user = users_db.get(user_id)
    if not user:
        logger.warning(f"User profile not found for ID: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user