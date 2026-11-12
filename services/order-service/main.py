import os
import logging
from datetime import datetime, timezone
from typing import Dict, List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [ORDER-SERVICE] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

orders_db: Dict[int, dict] = {}
order_id_counter = 1

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/v1/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Orders"])
def create_order(order: OrderCreateRequest):
    global order_id_counter
    new_order = {
        "id": order_id_counter,
        "user_id": order.user_id,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "total_amount": order.total_amount,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    orders_db[order_id_counter] = new_order
    order_id_counter += 1
    logger.info(f"Order created: ID {new_order['id']} for User {order.user_id}")
    return new_order

@app.get("/api/v1/orders", response_model=List[OrderResponse], tags=["Orders"])
def list_orders():
    return list(orders_db.values())

@app.get("/api/v1/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
def get_order(order_id: int):
    order = orders_db.get(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order

@app.patch("/api/v1/orders/{order_id}/status", response_model=OrderResponse, tags=["Orders"])
def update_order_status(order_id: int, payload: OrderStatusUpdate):
    order = orders_db.get(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order["status"] = payload.status.upper()
    logger.info(f"Order {order_id} status updated to {order['status']}")
    return order