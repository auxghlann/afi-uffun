import datetime
import json
from typing import Any, Dict, List, Optional

from app.database import SessionLocal
from app.models.schema import EmergencyReport


def upsert_emergency_report(
    *,
    call_id: str,
    status: str,
    extracted_details: Optional[Dict[str, Any]] = None,
    location: Optional[Dict[str, Any]] = None,
    routed_hotlines: Optional[List[Dict[str, Any]]] = None
) -> EmergencyReport:
    db = SessionLocal()
    try:
        report = db.query(EmergencyReport).filter(EmergencyReport.call_id == call_id).first()
        if not report:
            report = EmergencyReport(call_id=call_id)
            db.add(report)

        details = extracted_details or {}
        loc = location or {}

        report.status = status
        report.emergency_types = details.get("emergency_types", "")
        report.severity = details.get("severity", "")
        report.people_affected = details.get("people_affected", "")
        report.summary = details.get("summary", "")
        report.caller_lat = loc.get("latitude")
        report.caller_lon = loc.get("longitude")
        report.routed_hotlines = json.dumps(routed_hotlines or [])
        report.timestamp = datetime.datetime.utcnow()

        db.commit()
        db.refresh(report)
        return report
    finally:
        db.close()
