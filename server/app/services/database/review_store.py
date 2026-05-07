import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.schema import EmergencyReview

async def upsert_review(call_id: str, payload: Dict[str, Any]) -> None:
    db: Session = SessionLocal()
    try:
        review = db.query(EmergencyReview).filter(EmergencyReview.call_id == call_id).first()
        if not review:
            review = EmergencyReview(call_id=call_id)
            db.add(review)
        
        review.review_status = payload.get("review_status", "pending")
        review.extracted_details = json.dumps(payload.get("extracted_details", {}))
        review.location = json.dumps(payload.get("location", {}))
        review.recommended_hotlines = json.dumps(payload.get("recommended_hotlines", []))
        review.approved_hotlines = json.dumps(payload.get("approved_hotlines", []))
        review.review_notes = payload.get("review_notes", "")
        review.updated_at = datetime.utcnow()
        
        db.commit()
    finally:
        db.close()

async def get_review(call_id: str) -> Optional[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        review = db.query(EmergencyReview).filter(EmergencyReview.call_id == call_id).first()
        if not review:
            return None
        
        return {
            "call_id": review.call_id,
            "review_status": review.review_status,
            "extracted_details": json.loads(review.extracted_details or "{}"),
            "location": json.loads(review.location or "{}"),
            "recommended_hotlines": json.loads(review.recommended_hotlines or "[]"),
            "approved_hotlines": json.loads(review.approved_hotlines or "[]"),
            "review_notes": review.review_notes,
            "updated_at": review.updated_at.isoformat() if review.updated_at else None
        }
    finally:
        db.close()

async def list_pending_reviews() -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        reviews = db.query(EmergencyReview).filter(EmergencyReview.review_status == "pending").all()
        return [{
            "call_id": r.call_id,
            "review_status": r.review_status,
            "extracted_details": json.loads(r.extracted_details or "{}"),
            "location": json.loads(r.location or "{}"),
            "recommended_hotlines": json.loads(r.recommended_hotlines or "[]"),
            "approved_hotlines": json.loads(r.approved_hotlines or "[]"),
            "review_notes": r.review_notes,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None
        } for r in reviews]
    finally:
        db.close()

async def update_review(call_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        review = db.query(EmergencyReview).filter(EmergencyReview.call_id == call_id).first()
        if not review:
            return None
        
        if "review_status" in updates:
            review.review_status = updates["review_status"]
        if "approved_hotlines" in updates:
            review.approved_hotlines = json.dumps(updates["approved_hotlines"])
        if "review_notes" in updates:
            review.review_notes = updates["review_notes"]
        
        review.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(review)
        
        return {
            "call_id": review.call_id,
            "review_status": review.review_status,
            "updated_at": review.updated_at.isoformat() if review.updated_at else None
        }
    finally:
        db.close()
