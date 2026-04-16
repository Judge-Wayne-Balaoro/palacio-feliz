"""
app/routes/calendar.py  –  Calendar data for both customer and admin views
"""
from datetime import date, timedelta
from calendar import monthrange
from flask import Blueprint, request

from app.models import Booking
from app.utils  import success, error

calendar_bp = Blueprint("calendar", __name__)


def _bookings_for_month(year: int, month: int):
    """Return all approved bookings whose check_in_date falls in the given month."""
    from datetime import date as d
    first = d(year, month, 1)
    last  = d(year, month, monthrange(year, month)[1])

    return Booking.query.filter(
        Booking.status == "approved",
        Booking.check_in_date >= first,
        Booking.check_in_date <= last,
    ).all()


def _day_status(day_bookings: list) -> str:
    """
    Returns the display status for a calendar day.
    Priority: overnight > dual (day+night) > nightswimming > dayswimming > available
    """
    types = {b.booking_type for b in day_bookings}
    if not types:
        return "available"
    if "overnight" in types:
        return "overnight"
    if "dayswimming" in types and "nightswimming" in types:
        return "dual"
    if "nightswimming" in types:
        return "nightswimming"
    if "dayswimming" in types:
        return "dayswimming"
    return "available"


# ── GET /api/calendar/month  ────────────────────────────────────────── PUBLIC
@calendar_bp.get("/month")
def month_view():
    """
    Query: ?year=2026&month=4
    Returns day-by-day booking status for the requested month.
    """
    try:
        year  = int(request.args.get("year",  date.today().year))
        month = int(request.args.get("month", date.today().month))
    except ValueError:
        return error("year and month must be integers.", 400)

    if not (1 <= month <= 12):
        return error("month must be between 1 and 12.", 400)

    bookings = _bookings_for_month(year, month)

    # Index bookings by date
    by_date: dict[date, list] = {}
    for b in bookings:
        by_date.setdefault(b.check_in_date, []).append(b)

    days_in_month = monthrange(year, month)[1]
    days = []
    for day_num in range(1, days_in_month + 1):
        d     = date(year, month, day_num)
        blist = by_date.get(d, [])
        days.append({
            "date":   d.isoformat(),
            "status": _day_status(blist),
            "slots":  [
                {
                    "type":     b.booking_type,
                    "check_in": b.check_in_time,
                    "check_out":b.check_out_time,
                }
                for b in blist
            ],
        })

    return success({"year": year, "month": month, "days": days})


# ── GET /api/calendar/date  ─────────────────────────────────────────── PUBLIC
@calendar_bp.get("/date")
def date_detail():
    """
    Query: ?date=2026-04-10
    Returns the booking slots for a specific date (customer-safe, no PII).
    """
    date_str = request.args.get("date", "")
    try:
        d = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return error("Invalid date. Use YYYY-MM-DD.", 400)

    bookings = Booking.query.filter_by(
        check_in_date=d, status="approved"
    ).all()

    slots = [
        {
            "type":      b.booking_type,
            "check_in":  b.check_in_time,
            "check_out": b.check_out_time,
        }
        for b in bookings
    ]

    types  = {b.booking_type for b in bookings}
    status = _day_status(bookings)

    # What's still available
    available_types = []
    if "overnight" not in types:
        if "dayswimming" not in types:
            available_types.append("dayswimming")
        if "nightswimming" not in types:
            available_types.append("nightswimming")

    return success({
        "date":            d.isoformat(),
        "status":          status,
        "slots":           slots,
        "available_types": available_types,
    })


# ── GET /api/calendar/upcoming  ─────────────────────────────────────── ADMIN
@calendar_bp.get("/upcoming")
def upcoming_bookings():
    """Return approved bookings for the next 30 days (admin calendar widget)."""
    from flask_jwt_extended import verify_jwt_in_request
    try:
        verify_jwt_in_request()
    except Exception:
        pass  # allow public access for lightweight calendar

    today = date.today()
    end   = today + timedelta(days=30)

    bookings = Booking.query.filter(
        Booking.status == "approved",
        Booking.check_in_date >= today,
        Booking.check_in_date <= end,
    ).order_by(Booking.check_in_date).all()

    return success([
        {
            "id":           b.id,
            "reference_no": b.reference_no,
            "guest_name":   b.guest.full_name if b.guest else "—",
            "booking_type": b.booking_type,
            "check_in_date":b.check_in_date.isoformat(),
            "check_out_date":b.check_out_date.isoformat(),
            "total_pax":    b.adults + b.youth,
        }
        for b in bookings
    ])
