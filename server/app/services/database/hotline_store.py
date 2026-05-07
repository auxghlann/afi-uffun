from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.schema import Hotline

async def list_hotlines() -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        hotlines = db.query(Hotline).all()
        return [{
            "id": h.id,
            "name": h.name,
            "type": h.type,
            "lat": h.lat,
            "lon": h.lon,
            "contact": h.contact
        } for h in hotlines]
    finally:
        db.close()

async def get_hotline(hotline_id: int) -> Optional[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        h = db.query(Hotline).filter(Hotline.id == hotline_id).first()
        if not h:
            return None
        return {
            "id": h.id,
            "name": h.name,
            "type": h.type,
            "lat": h.lat,
            "lon": h.lon,
            "contact": h.contact
        }
    finally:
        db.close()
