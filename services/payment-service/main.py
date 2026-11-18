import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [PAYMENT-SERVICE] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_payment.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PaymentModel(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), unique=True, index=True, nullable=False)
    order_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False)
    processed_at = Column(String(50), nullable=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

    class Config:
        from_attributes = True

# Static health and custom upgrade message route (Placed at top to avoid conflicts)
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "message": "Payment Service is live and upgraded successfully! 💳✨",
        "database_backend": "postgresql" if "postgresql" in DATABASE_URL else "sqlite",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/v1/payments/process", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED, tags=["Payments"])
def process_payment(payment: PaymentRequest, db: Session = Depends(get_db)):
    tx_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
    new_payment = PaymentModel(
        transaction_id=tx_id,
        order_id=payment.order_id,
        user_id=payment.user_id,
        amount=payment.amount,
        payment_method=payment.payment_method.upper(),
        status="SUCCESS",
        processed_at=datetime.now(timezone.utc).isoformat()
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)
    logger.info(f"Payment processed in DB: {tx_id} for Order {payment.order_id}")
    return new_payment

@app.get("/api/v1/payments", response_model=List[PaymentResponse], tags=["Payments"])
def list_payments(db: Session = Depends(get_db)):
    return db.query(PaymentModel).all()

# Dynamic parameterized route placed strictly BELOW static routes
@app.get("/api/v1/payments/{payment_id}", response_model=PaymentResponse, tags=["Payments"])
def get_payment_status(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")
    return payment