from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import json
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.review_store import list_pending_reviews, get_review, update_review
from app.services.report_store import upsert_emergency_report
from app.services.nodes import geo_router_node, build_dispatch_confirmation
from app.database import SessionLocal
from app.models.schema import Hotline, EmergencyReport

router = APIRouter()


def _severity_score(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.strip().lower()
    if normalized.startswith("high"):
        return 3
    if normalized.startswith("medium"):
        return 2
    if normalized.startswith("low"):
        return 1
    return 0


def _severity_label(score: float) -> str:
    if score >= 2.5:
        return "High"
    if score >= 1.5:
        return "Medium"
    if score > 0:
        return "Low"
    return "N/A"


def _safe_load_hotlines(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []

class AdminApproveRequest(BaseModel):
    call_id: str
    override_hotline_ids: Optional[List[int]] = None
    review_notes: Optional[str] = ""

class AdminRejectRequest(BaseModel):
    call_id: str
    review_notes: Optional[str] = ""

@router.get("/pending")
async def list_pending():
    return list_pending_reviews()

@router.get("/hotlines")
async def list_hotlines():
    db = SessionLocal()
    try:
        hotlines = db.query(Hotline).all()
        return [
            {
                "id": h.id,
                "name": h.name,
                "type": h.type,
                "lat": h.lat,
                "lon": h.lon,
                "contact": h.contact
            }
            for h in hotlines
        ]
    finally:
        db.close()


@router.get("/metrics")
async def get_metrics():
    db = SessionLocal()
    try:
        total_reports = db.query(EmergencyReport).count()
        last_24h = datetime.utcnow() - timedelta(hours=24)
        reports_24h = db.query(EmergencyReport).filter(EmergencyReport.timestamp >= last_24h).count()

        status_rows = db.query(EmergencyReport.status, func.count(EmergencyReport.id)).group_by(EmergencyReport.status).all()
        by_status = {status or "unknown": count for status, count in status_rows}

        severities = db.query(EmergencyReport.severity).all()
        scores = [_severity_score(item[0]) for item in severities]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0

        return {
            "total_reports": total_reports,
            "reports_24h": reports_24h,
            "avg_severity_score": avg_score,
            "avg_severity_label": _severity_label(avg_score),
            "by_status": by_status,
            "pending_reviews": len(list_pending_reviews())
        }
    finally:
        db.close()


@router.get("/breakdown")
async def get_breakdown(days: int = 7):
    db = SessionLocal()
    try:
        if days < 1:
            days = 1
        start_date = datetime.utcnow().date() - timedelta(days=days - 1)
        start_dt = datetime.combine(start_date, datetime.min.time())

        reports = db.query(EmergencyReport).filter(EmergencyReport.timestamp >= start_dt).all()

        by_day: dict[str, int] = {}
        for offset in range(days):
            day = start_date + timedelta(days=offset)
            by_day[day.isoformat()] = 0

        by_type: dict[str, int] = {}
        for report in reports:
            if report.timestamp:
                day_key = report.timestamp.date().isoformat()
                by_day[day_key] = by_day.get(day_key, 0) + 1

            raw_types = report.emergency_types or ""
            for entry in raw_types.split(","):
                cleaned = entry.strip()
                if not cleaned:
                    continue
                by_type[cleaned] = by_type.get(cleaned, 0) + 1

        day_series = [{"date": date_key, "count": by_day[date_key]} for date_key in by_day.keys()]
        type_series = [
            {"type": key, "count": value}
            for key, value in sorted(by_type.items(), key=lambda item: item[1], reverse=True)
        ]

        return {"by_day": day_series, "by_type": type_series}
    finally:
        db.close()


@router.get("/heatmap")
async def get_heatmap(limit: int = 200):
    db = SessionLocal()
    try:
        reports = (
            db.query(EmergencyReport)
            .order_by(EmergencyReport.timestamp.desc())
            .limit(limit)
            .all()
        )

        points = []
        for report in reports:
            if report.caller_lat is None or report.caller_lon is None:
                continue
            points.append({
                "lat": report.caller_lat,
                "lon": report.caller_lon,
                "weight": max(_severity_score(report.severity), 1),
                "severity": report.severity or "",
                "type": report.emergency_types or ""
            })

        return points
    finally:
        db.close()


@router.get("/reports")
async def list_reports(limit: int = 20, offset: int = 0):
    db = SessionLocal()
    try:
        reports = (
            db.query(EmergencyReport)
            .order_by(EmergencyReport.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            {
                "id": report.id,
                "call_id": report.call_id,
                "status": report.status,
                "emergency_types": report.emergency_types,
                "severity": report.severity,
                "people_affected": report.people_affected,
                "summary": report.summary,
                "caller_lat": report.caller_lat,
                "caller_lon": report.caller_lon,
                "routed_hotlines": _safe_load_hotlines(report.routed_hotlines),
                "timestamp": report.timestamp.isoformat() if report.timestamp else None
            }
            for report in reports
        ]
    finally:
        db.close()

@router.post("/review/approve")
async def approve_review(request: AdminApproveRequest):
    review = get_review(request.call_id)
    if not review:
        raise HTTPException(status_code=404, detail="Call not found")

    approved_hotlines: List[Dict[str, Any]] = []

    if request.override_hotline_ids:
        db = SessionLocal()
        try:
            hotlines = db.query(Hotline).filter(Hotline.id.in_(request.override_hotline_ids)).all()
            approved_hotlines = [
                {
                    "id": h.id,
                    "name": h.name,
                    "type": h.type,
                    "lat": h.lat,
                    "lon": h.lon,
                    "contact": h.contact
                }
                for h in hotlines
            ]
        finally:
            db.close()
    else:
        recommendations = review.get("recommended_hotlines", [])
        if not recommendations:
            recommendations = geo_router_node({
                "location": review.get("location", {}),
                "extracted_details": review.get("extracted_details", {})
            }).get("routed_hotlines", [])
        approved_hotlines = recommendations

    update_review(request.call_id, {
        "review_status": "approved",
        "approved_hotlines": approved_hotlines,
        "review_notes": request.review_notes or ""
    })

    upsert_emergency_report(
        call_id=request.call_id,
        status="approved",
        extracted_details=review.get("extracted_details", {}),
        location=review.get("location", {}),
        routed_hotlines=approved_hotlines
    )

    return {
        "status": "approved",
        "message": build_dispatch_confirmation(approved_hotlines),
        "approved_hotlines": approved_hotlines
    }

@router.post("/review/reject")
async def reject_review(request: AdminRejectRequest):
    review = get_review(request.call_id)
    if not review:
        raise HTTPException(status_code=404, detail="Call not found")

    update_review(request.call_id, {
        "review_status": "rejected",
        "review_notes": request.review_notes or ""
    })

    upsert_emergency_report(
        call_id=request.call_id,
        status="rejected",
        extracted_details=review.get("extracted_details", {}),
        location=review.get("location", {}),
        routed_hotlines=[]
    )

    return {"status": "rejected"}
