"""
app/routes/dashboard.py  –  Admin dashboard stats & charts
"""
from datetime import date, timedelta
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, extract

from app import db
from app.models import Booking, Guest, Review, Payment
from app.utils  import success

dashboard_bp = Blueprint("dashboard", __name__)


def _date_range_for(range_key: str):
    """
    FIX #5: Translate a range key into (start_date, end_date).
    Supported keys: this_month, last_month, last_2_months, last_6_months, last_year
    Falls back to last 365 days for unknown keys.
    """
    today = date.today()
    if range_key == "this_month":
        start = today.replace(day=1)
        return start, today
    elif range_key == "last_month":
        first_this = today.replace(day=1)
        last_prev  = first_this - timedelta(days=1)
        start      = last_prev.replace(day=1)
        return start, last_prev
    elif range_key == "last_2_months":
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        start = (start.replace(day=1) - timedelta(days=1)).replace(day=1)
        return start, today
    elif range_key == "last_6_months":
        return today - timedelta(days=183), today
    else:
        # Default: last 12 months
        return today - timedelta(days=365), today


# ── GET /api/dashboard/stats  ───────────────────────────────────────────── ADMIN
@dashboard_bp.get("/stats")
@jwt_required()
def stats():
    total     = Booking.query.count()
    pending   = Booking.query.filter_by(status="pending").count()
    approved  = Booking.query.filter_by(status="approved").count()
    completed = Booking.query.filter_by(status="completed").count()
    cancelled = Booking.query.filter_by(status="cancelled").count()

    revenue_row   = db.session.query(func.sum(Booking.total_price)).filter(Booking.status.in_(["approved", "completed"])).scalar()
    total_revenue = float(revenue_row or 0)

    today       = date.today()
    month_start = today.replace(day=1)
    new_this_month = Booking.query.filter(
        Booking.created_at >= month_start
    ).count()

    total_guests  = Guest.query.count()
    total_reviews = Review.query.filter_by(is_visible=True).count()

    return success({
        "total_bookings":   total,
        "pending":          pending,
        "approved":         approved,
        "completed":        completed,
        "cancelled":        cancelled,
        "total_revenue":    total_revenue,
        "new_this_month":   new_this_month,
        "total_guests":     total_guests,
        "total_reviews":    total_reviews,
    })


# ── GET /api/dashboard/monthly-revenue  ─────────────────────────────────── ADMIN
@dashboard_bp.get("/monthly-revenue")
@jwt_required()
def monthly_revenue():
    today    = date.today()
    year_ago = today - timedelta(days=365)

    rows = (
        db.session.query(
            extract("year",  Booking.created_at).label("yr"),
            extract("month", Booking.created_at).label("mo"),
            func.sum(Booking.total_price).label("total"),
        )
        .filter(Booking.created_at >= year_ago, Booking.status.in_(["approved", "completed"]))
        .group_by("yr", "mo")
        .order_by("yr", "mo")
        .all()
    )

    import calendar
    result = [
        {
            "label":   f"{calendar.month_abbr[int(r.mo)]} {int(r.yr)}",
            "year":    int(r.yr),
            "month":   int(r.mo),
            "revenue": float(r.total),
        }
        for r in rows
    ]
    return success(result)


# ── GET /api/dashboard/booking-stats  ───────────────────────────────────── ADMIN
@dashboard_bp.get("/booking-stats")
@jwt_required()
def booking_stats():
    """
    FIX #5: Now reads and respects the ?range= query parameter.
    Supported values: this_month, last_month, last_2_months, last_6_months, last_year
    """
    range_key        = request.args.get("range", "last_year")
    start_date, end_date = _date_range_for(range_key)

    rows = (
        db.session.query(
            extract("year",  Booking.created_at).label("yr"),
            extract("month", Booking.created_at).label("mo"),
            Booking.status,
            func.count(Booking.id).label("cnt"),
        )
        .filter(
            Booking.created_at >= start_date,
            Booking.created_at <= end_date,
        )
        .group_by("yr", "mo", Booking.status)
        .order_by("yr", "mo")
        .all()
    )

    import calendar as cal
    buckets: dict = {}
    for r in rows:
        label = f"{cal.month_abbr[int(r.mo)]} {int(r.yr)}"
        buckets.setdefault(label, {"label": label, "total": 0,
                                    "approved": 0, "cancelled": 0,
                                    "pending": 0, "completed": 0})
        buckets[label][r.status] = int(r.cnt)
        buckets[label]["total"] += int(r.cnt)

    return success(list(buckets.values()))


# ── GET /api/dashboard/monthly-summary  ─────────────────────────────────── ADMIN
@dashboard_bp.get("/monthly-summary")
@jwt_required()
def monthly_summary():
    today    = date.today()
    year_ago = today - timedelta(days=365)

    booking_rows = (
        db.session.query(
            extract("year",  Booking.created_at).label("yr"),
            extract("month", Booking.created_at).label("mo"),
            func.count(Booking.id).label("bookings"),
            func.avg(Booking.adults + Booking.youth).label("avg_pax"),
        )
        .filter(Booking.created_at >= year_ago)
        .group_by("yr", "mo")
        .order_by("yr", "mo")
        .all()
    )

    revenue_rows = (
        db.session.query(
            extract("year",  Booking.created_at).label("yr"),
            extract("month", Booking.created_at).label("mo"),
            func.sum(Booking.total_price).label("rev"),
        )
        .filter(Booking.created_at >= year_ago, Booking.status.in_(["approved", "completed"]))
        .group_by("yr", "mo")
        .all()
    )

    rev_map = {(int(r.yr), int(r.mo)): float(r.rev) for r in revenue_rows}

    import calendar as cal
    result = []
    for r in booking_rows:
        yr, mo = int(r.yr), int(r.mo)
        result.append({
            "month":          f"{cal.month_name[mo]} {yr}",
            "total_bookings": int(r.bookings),
            "revenue":        rev_map.get((yr, mo), 0.0),
            "avg_pax":        round(float(r.avg_pax or 0), 1),
        })

    return success(result)


# ── GET /api/dashboard/recent-bookings  ─────────────────────────────────── ADMIN
@dashboard_bp.get("/recent-bookings")
@jwt_required()
def recent_bookings():
    # FIX #9: Safe int parsing
    try:
        limit = int(request.args.get("limit", 10))
    except (ValueError, TypeError):
        limit = 10

    rows = (
        Booking.query
        .order_by(Booking.created_at.desc())
        .limit(limit)
        .all()
    )
    return success([b.to_dict() for b in rows])
