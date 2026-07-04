import requests
import random
import time
from uuid import uuid4
from datetime import datetime, timezone

API = "http://127.0.0.1:8000/track-event"

REGIONS = ["IN-NORTH","IN-SOUTH","IN-WEST", "IN-EAST"]
PAYMENTS = ["upi","card","netbanking", "wallet"]
FAILURE_REASONS = ["TIMEOUT", "INSUFFICIENT_FUNDS", "SERVICE_UNAVAILABLE"]


NORMAL_FUNNEL = {
    "product_view": 1.0,
    "add_to_cart": 0.30,
    "checkout_start": 0.20,
    "checkout_success": 0.15,
    "checkout_failed": 0.05
}

FUNNEL_ANOMALY = {
    "product_view": 1.0,
    "add_to_cart": 0.30,
    "checkout_start": 0.05,
    "checkout_success": 0.02,
    "checkout_failed": 0.03
}


def choose_event(probs):
    events = list(probs.keys())
    weights = list(probs.values())
    return random.choices(events, weights)[0]


def base_event(event_type, price_range=(500,2500), latency_range=(200,900)):

    order_id = None
    price = None
    payment_method = None
    latency = None
    failure_reason = None

    if event_type.startswith("checkout"):
        order_id = f"ORD-{random.randint(1000,9999)}"
        price = random.randint(*price_range)
        payment_method = random.choice(PAYMENTS)
        latency = random.randint(*latency_range)

    if event_type == "checkout_failed":
        failure_reason = random.choice(FAILURE_REASONS)

    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "event_time": datetime.now(timezone.utc).isoformat(),
        "user_id": random.randint(1,500),
        "product_id": random.randint(1,200),
        "order_id": order_id,
        "price": price,
        "currency": "INR",
        "payment_method": payment_method,
        "latency_ms": latency,
        "region": random.choice(REGIONS),
        "failure_reason": failure_reason
    }


def send(event):
    
    try:
        requests.post(API,json=event,timeout=2)
    except:
        pass


def normal_traffic(seconds=60):
    start=time.time()
    while time.time()-start < seconds:
        event_type=choose_event(NORMAL_FUNNEL)
        send(base_event(event_type))
        time.sleep(0.05)


def funnel_anomaly(seconds=30):
    
    print("Funnel anomaly (conversion drop)")
    start=time.time()
    while time.time()-start < seconds:
        event_type=choose_event(FUNNEL_ANOMALY)
        send(base_event(event_type))
        time.sleep(0.05)

def region_outage(seconds=30):
    print("Region outage anomaly (IN-WEST failing)")    

    start = time.time()
    while time.time() - start < seconds:

        event = base_event("checkout_failed", (500,2500), (3000,6000))
        event["region"] = "IN-WEST"
        event["failure_reason"] = "SERVICE_UNAVAILABLE"

        send(event)

def payment_method_outage(seconds=30):
    print("Payment method outage (UPI failing)")

    start = time.time()
    while time.time() - start < seconds:

        event = base_event("checkout_failed",(500,2500),(1500,5000))
        event["payment_method"] = "upi"
        event["failure_reason"] = "SERVICE_UNAVAILABLE"

        send(event)
def traffic_spike(seconds=20):
    print("Traffic spike anomaly (regional imbalance)")

    # traffic distribution during spike
    spike_regions = ["IN-NORTH", "IN-SOUTH", "IN-WEST", "IN-EAST"]
    spike_weights = [0.6, 0.2, 0.15, 0.05]   # heavy spike in NORTH

    start = time.time()

    while time.time() - start < seconds:

        # burst events
        for _ in range(random.randint(20,40)):
            event_type = choose_event(NORMAL_FUNNEL)

            event = base_event(event_type)

            # override region using spike distribution
            event["region"] = random.choices(spike_regions, spike_weights)[0]

            send(event)

        time.sleep(0.01)


if __name__ == "__main__":

    print("Normal traffic")

    normal_traffic(60)

    funnel_anomaly(30)

    normal_traffic(60)

    region_outage(30)

    normal_traffic(60)

    payment_method_outage(30)

    normal_traffic(60)

    traffic_spike(20)

    normal_traffic(20)

    print("Traffic generation complete")