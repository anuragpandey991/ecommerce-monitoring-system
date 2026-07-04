from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from ingestion.schemas import EcommerceEvent


ALLOWED_PAYMENT_METHODS = {"upi", "card", "netbanking", "wallet"}
ALLOWED_REGIONS = {"IN-NORTH", "IN-SOUTH", "IN-WEST", "IN-EAST"}
ALLOWED_FAILURE_REASONS = {"TIMEOUT", "INSUFFICIENT_FUNDS", "SERVICE_UNAVAILABLE"}

def validate_event(event: EcommerceEvent) -> None:
    """
    Raises ValueError if the event violates hard invariants.
    """

    _validate_event_time(event.event_time)
    _validate_price(event.price)
    _validate_latency(event.latency_ms)
    _validate_payment_method(event.payment_method)
    _validate_failure_reason(event.failure_reason)
    _validate_region(event.region)


def _validate_event_time(event_time: datetime) -> None:
    now = datetime.now(timezone.utc)
    if event_time > now:
        raise ValueError("event_time cannot be in the future")


def _validate_price(price: Optional[float]) -> None:
    if price is not None and price < 0:
        raise ValueError("price cannot be negative")


def _validate_latency(latency_ms: Optional[int]) -> None:
    if latency_ms is not None and latency_ms < 0:
        raise ValueError("latency_ms cannot be negative")


def _validate_payment_method(payment_method: Optional[str]) -> None:
    if payment_method is None:
        return
    if payment_method not in ALLOWED_PAYMENT_METHODS:
        raise ValueError(f"invalid payment_method: {payment_method}")

def _validate_failure_reason(failure_reason: Optional[str]) -> None:
    if failure_reason is None:
        return
    if failure_reason not in ALLOWED_FAILURE_REASONS:
        raise ValueError(f"invalid failure_reason: {failure_reason}")
    
def _validate_region(region: str) -> None:
    if region not in ALLOWED_REGIONS:
        raise ValueError(f"invalid region: {region}")
