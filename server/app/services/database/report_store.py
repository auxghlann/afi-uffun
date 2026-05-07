import datetime
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import SessionLocal
from app.models.schema import EmergencyReport

async def upsert_emergency_report(
    *,
    call_id: str,
    status: str,
    extracted_details: Optional[Dict[str, Any]] = None,
    location: Optional[Dict[str, Any]] = None,
    routed_hotlines: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    details = extracted_details or {}
    loc = location or {}

    db: Session = SessionLocal()
    try:
        report = db.query(EmergencyReport).filter(EmergencyReport.call_id == call_id).first()
        
        if not report:
            report = EmergencyReport(call_id=call_id)
            db.add(report)
        
        report.status = status
        report.emergency_types = details.get("emergency_types", "")
        report.severity = details.get("severity", "")
        report.people_affected = str(details.get("people_affected", ""))
        report.summary = details.get("summary", "")
        report.caller_lat = loc.get("latitude")
        report.caller_lon = loc.get("longitude")
        report.routed_hotlines = json.dumps(routed_hotlines or [])
        report.timestamp = datetime.datetime.utcnow()
        
        db.commit()
        db.refresh(report)
        
        return {
            "call_id": report.call_id,
            "status": report.status,
            "emergency_types": report.emergency_types,
            "severity": report.severity,
            "summary": report.summary,
            "timestamp": report.timestamp.isoformat() if report.timestamp else None
        }
    finally:
        db.close()

async def count_reports() -> int:
    db: Session = SessionLocal()
    try:
        return db.query(EmergencyReport).count()
    finally:
        db.close()

async def list_reports(limit: int = 100, offset: int = 0, since: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        query = db.query(EmergencyReport)
        if since:
            query = query.filter(EmergencyReport.timestamp >= since)
        
        reports = query.order_by(EmergencyReport.timestamp.desc()).offset(offset).limit(limit).all()
        return [{
            "call_id": r.call_id,
            "status": r.status,
            "emergency_types": r.emergency_types,
            "severity": r.severity,
            "people_affected": r.people_affected,
            "summary": r.summary,
            "caller_lat": r.caller_lat,
            "caller_lon": r.caller_lon,
            "routed_hotlines": json.loads(r.routed_hotlines or "[]"),
            "timestamp": r.timestamp.isoformat() if r.timestamp else None
        } for r in reports]
    finally:
        db.close()
