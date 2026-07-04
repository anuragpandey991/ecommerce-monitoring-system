from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID


class EventType(str, Enum):
    product_view = "product_view"
    add_to_cart = "add_to_cart"
    checkout_start = "checkout_start"
    checkout_success = "checkout_success"
    checkout_failed = "checkout_failed"


class EcommerceEvent(BaseModel):  
    event_id: UUID
    event_type: EventType
    event_time: datetime

    region: str

    user_id: Optional[int] = None 
    product_id: Optional[int] = None
    order_id: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "INR"
    payment_method: Optional[str] = None
    latency_ms: Optional[int] = None
    failure_reason: Optional[str] = None

    schema_version: str = "1.0"
