from fastapi import FastAPI, HTTPException
from ingestion.schemas import EcommerceEvent
from ingestion.validators import validate_event
from ingestion.repository import insert_raw_event

app = FastAPI(title="E-commerce Event Ingestion")

@app.post("/track-event", status_code=202)
def track_event(event: EcommerceEvent):
    try:
        validate_event(event)
        insert_raw_event(event)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "accepted", "event_id": str(event.event_id)}
