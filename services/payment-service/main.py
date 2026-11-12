import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [PAYMENT-SERVICE] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "payment-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

app = FastAPI(
    title="Payment Service API",
    description="Microservice handling simulated payment processing and transaction history.",
    version=SERVICE_VERSION
)

class PaymentRequest(BaseModel):
    order_id: int = Field(..., gt=0, examples=[1])
    user_id: int = Field(..., gt=0, examples=[1])
    amount: float = Field(..., gt=0, examples=[14999.0])
    payment_method: str = Field(..., examples=["UPI"])

class PaymentResponse(BaseModel):
    id: int
    transaction_id: str
    order_id: int
    user_id: int
    amount: float
    payment_method: str
    status: str
    processed_at: str

payments_db: Dict[int, dict] = {}
payment_id_counter = 1

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/v1/payments/process", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED, tags=["Payments"])
def process_payment(payment: PaymentRequest):
    global payment_id_counter
    tx_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
    new_payment = {
        "id": payment_id_counter,
        "transaction_id": tx_id,
        "order_id": payment.order_id,
        "user_id": payment.user_id,
        "amount": payment.amount,
        "payment_method": payment.payment_method.upper(),
        "status": "SUCCESS",
        "processed_at": datetime.now(timezone.utc).isoformat()
    }
    payments_db[payment_id_counter] = new_payment
    payment_id_counter += 1
    logger.info(f"Payment processed: {tx_id} for Order {payment.order_id}")
    return new_payment

@app.get("/api/v1/payments", response_model=List[PaymentResponse], tags=["Payments"])
def list_payments():
    return list(payments_db.values())

@app.get("/api/v1/payments/{payment_id}", response_model=PaymentResponse, tags=["Payments"])
def get_payment_status(payment_id: int):
    payment = payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")
    return payment