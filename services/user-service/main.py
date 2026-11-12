import os
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# 1. Structured Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [USER-SERVICE] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 2. Database Configuration (12-Factor App Env Var)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_user.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. Database Table Model
class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(30), unique=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(100), nullable=False)
    full_name = Column(String(100), nullable=False)
    created_at = Column(String(50), nullable=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. FastAPI App Initialization
SERVICE_NAME = os.getenv("SERVICE_NAME", "user-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

app = FastAPI(
    title="User Service API",
    description="Microservice handling user registration, authentication, and profile management.",
    version=SERVICE_VERSION
)

# 5. Pydantic Schemas
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

    class Config:
        from_attributes = True

# 6. Endpoints
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "database_backend": "postgresql" if "postgresql" in DATABASE_URL else "sqlite",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/v1/users/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
def register_user(user: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing:
        logger.warning(f"Registration failed: Email {user.email} already exists")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = UserModel(
        username=user.username,
        email=user.email,
        password=user.password,
        full_name=user.full_name,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"User registered in DB: {user.username} (ID: {new_user.id})")
    return new_user

@app.post("/api/v1/users/login", tags=["Users"])
def login_user(credentials: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(
        UserModel.email == credentials.email,
        UserModel.password == credentials.password
    ).first()
    if not user:
        logger.warning(f"Failed login attempt for: {credentials.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    logger.info(f"User logged in: {credentials.email}")
    return {"message": "Login successful", "user_id": user.id, "username": user.username}

@app.get("/api/v1/users", response_model=List[UserResponse], tags=["Users"])
def list_users(db: Session = Depends(get_db)):
    return db.query(UserModel).all()

@app.get("/api/v1/users/{user_id}", response_model=UserResponse, tags=["Users"])
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found")
    return user