from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import json
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.database import (
    list_pending_reviews, 
    get_review, 
    update_review, 
    upsert_emergency_report, 
    list_hotlines, 
    get_hotline,
    count_reports,
    list_reports
)
from app.services.ai import geo_router_node, build_dispatch_confirmation

router = APIRouter()

def _severity_score(value: str | None) -> int:
    if not value:
        return 0
    normalized = str(value).strip().lower()
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

class AdminApproveRequest(BaseModel):
    call_id: str
    override_hotline_ids: Optional[List[int]] = None  # IDs are integers in SQL
    review_notes: Optional[str] = ""

class AdminRejectRequest(BaseModel):
    call_id: str
    review_notes: Optional[str] = ""

@router.get("/pending")
async def list_pending():
    return await list_pending_reviews()

@router.get("/hotlines")
async def list_hotlines_api():
    return await list_hotlines()

@router.get("/metrics")
async def get_metrics():
    total = await count_reports()
    
    last_24h = datetime.utcnow() - timedelta(hours=24)
    reports_24h_list = await list_reports(limit=1000, since=last_24h)
    reports_24h = len(reports_24h_list)

    all_reports = await list_reports(limit=1000)
    
    by_status = {}
    scores = []
    for r in all_reports:
        status = r.get("status") or "unknown"
        by_status[status] = by_status.get(status, 0) + 1
        scores.append(_severity_score(r.get("severity")))

    avg_score = round(sum(scores) / len(scores), 2) if scores else 0
    pending = await list_pending_reviews()

    return {
        "total_reports": total,
        "reports_24h": reports_24h,
        "avg_severity_score": avg_score,
        "avg_severity_label": _severity_label(avg_score),
        "by_status": by_status,
        "pending_reviews": len(pending)
    }

@router.get("/breakdown")
async def get_breakdown(days: int = 7):
    if days < 1:
        days = 1
    start_date = datetime.utcnow().date() - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, datetime.min.time())

    reports = await list_reports(limit=2000, since=start_dt)

    by_day: dict[str, int] = {}
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        by_day[day.isoformat()] = 0

    by_type: dict[str, int] = {}
    for report in reports:
        ts_str = report.get("timestamp")
        if ts_str:
            day_key = ts_str[:10]
            by_day[day_key] = by_day.get(day_key, 0) + 1

        raw_types = report.get("emergency_types") or ""
        for entry in str(raw_types).split(","):
            cleaned = entry.strip()
            if not cleaned:
                continue
            by_type[cleaned] = by_type.get(cleaned, 0) + 1

    day_series = [{"date": date_key, "count": by_day[date_key]} for date_key in sorted(by_day.keys())]
    type_series = [
        {"type": key, "count": value}
        for key, value in sorted(by_type.items(), key=lambda item: item[1], reverse=True)
    ]

    return {"by_day": day_series, "by_type": type_series}

@router.get("/heatmap")
async def get_heatmap(limit: int = 200):
    reports = await list_reports(limit=limit)

    points = []
    for report in reports:
        lat = report.get("caller_lat")
        lon = report.get("caller_lon")
        if lat is None or lon is None:
            continue
        points.append({
            "lat": lat,
            "lon": lon,
            "weight": max(_severity_score(report.get("severity")), 1),
            "severity": report.get("severity") or "",
            "type": report.get("emergency_types") or ""
        })

    return points

@router.get("/reports")
async def list_reports_api(limit: int = 20, offset: int = 0):
    return await list_reports(limit=limit, offset=offset)

@router.post("/review/approve")
async def approve_review(request: AdminApproveRequest):
    review = await get_review(request.call_id)
    if not review:
        raise HTTPException(status_code=404, detail="Call not found")

    approved_hotlines: List[Dict[str, Any]] = []

    if request.override_hotline_ids:
        for h_id in request.override_hotline_ids:
            h = await get_hotline(h_id)
            if h:
                approved_hotlines.append(h)
    else:
        recommendations = review.get("recommended_hotlines", [])
        if not recommendations:
            recommendations = geo_router_node({
                "location": review.get("location", {}),
                "extracted_details": review.get("extracted_details", {})
            }).get("routed_hotlines", [])
        approved_hotlines = recommendations

    await update_review(request.call_id, {
        "review_status": "approved",
        "approved_hotlines": approved_hotlines,
        "review_notes": request.review_notes or ""
    })

    await upsert_emergency_report(
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
    review = await get_review(request.call_id)
    if not review:
        raise HTTPException(status_code=404, detail="Call not found")

    await update_review(request.call_id, {
        "review_status": "rejected",
        "review_notes": request.review_notes or ""
    })

    await upsert_emergency_report(
        call_id=request.call_id,
        status="rejected",
        extracted_details=review.get("extracted_details", {}),
        location=review.get("location", {}),
        routed_hotlines=[]
    )

    return {"status": "rejected"}
