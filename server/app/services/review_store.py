from typing import Dict, Any
from datetime import datetime

# Simple in-memory store for hackathon demo purposes
REVIEW_STORE: Dict[str, Dict[str, Any]] = {}


def upsert_review(call_id: str, payload: Dict[str, Any]) -> None:
    payload["updated_at"] = datetime.utcnow().isoformat()
    REVIEW_STORE[call_id] = payload


def get_review(call_id: str) -> Dict[str, Any] | None:
    return REVIEW_STORE.get(call_id)


def list_pending_reviews() -> Dict[str, Dict[str, Any]]:
    return {k: v for k, v in REVIEW_STORE.items() if v.get("review_status") == "pending"}


def update_review(call_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
    current = REVIEW_STORE.get(call_id)
    if not current:
        return None
    current.update(updates)
    current["updated_at"] = datetime.utcnow().isoformat()
    REVIEW_STORE[call_id] = current
    return current
