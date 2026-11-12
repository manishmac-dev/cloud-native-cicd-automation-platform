import os
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [ORDER-SERVICE] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_order.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    product_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(30), nullable=False)
    created_at = Column(String(50), nullable=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

SERVICE_NAME = os.getenv("SERVICE_NAME", "order-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

app = FastAPI(
    title="Order Service API",
    description="Microservice handling customer order creation and status tracking.",
    version=SERVICE_VERSION
)

class OrderCreateRequest(BaseModel):
    user_id: int = Field(..., gt=0, examples=[1])
    product_name: str = Field(..., min_length=2, examples=["Nespresso Coffee Machine"])
    quantity: int = Field(..., gt=0, examples=[1])
    total_amount: float = Field(..., gt=0, examples=[14999.0])

class OrderStatusUpdate(BaseModel):
    status: str = Field(..., examples=["CONFIRMED"])

class OrderResponse(BaseModel):
    id: int
    user_id: int
    product_name: str
    quantity: int
    total_amount: float
    status: str
    created_at: str

    class Config:
        from_attributes = True

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "database_backend": "postgresql" if "postgresql" in DATABASE_URL else "sqlite",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/v1/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Orders"])
def create_order(order: OrderCreateRequest, db: Session = Depends(get_db)):
    new_order = OrderModel(
        user_id=order.user_id,
        product_name=order.product_name,
        quantity=order.quantity,
        total_amount=order.total_amount,
        status="PENDING",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    logger.info(f"Order created in DB: ID {new_order.id} for User {order.user_id}")
    return new_order

@app.get("/api/v1/orders", response_model=List[OrderResponse], tags=["Orders"])
def list_orders(db: Session = Depends(get_db)):
    return db.query(OrderModel).all()

@app.get("/api/v1/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order

@app.patch("/api/v1/orders/{order_id}/status", response_model=OrderResponse, tags=["Orders"])
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order.status = payload.status.upper()
    db.commit()
    db.refresh(order)
    logger.info(f"Order {order_id} status updated to {order.status}")
    return order