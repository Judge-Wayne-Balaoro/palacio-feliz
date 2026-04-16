"""
app/utils/__init__.py  –  Shared helper functions
"""
import os
import uuid
import string
import random
from datetime import date, datetime
from werkzeug.utils import secure_filename
from flask import current_app


# ─── File helpers ─────────────────────────────────────────────────────────────

def _allowed(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_upload(file, subfolder: str, allowed_ext: set) -> str | None:
    """
    Save a FileStorage object to UPLOAD_FOLDER/<subfolder>.
    Returns the relative URL path (e.g. /uploads/reviews/abc.jpg) or None.
    """
    if not file or file.filename == "":
        return None
    if not _allowed(file.filename, allowed_ext):
        return None

    ext  = file.filename.rsplit(".", 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder, name)
    file.save(dest)
    return f"/uploads/{subfolder}/{name}"


# ─── Reference number ─────────────────────────────────────────────────────────

def generate_ref_no(prefix: str = "PF") -> str:
    """Generate a booking reference like PF-A3X9K2"""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{suffix}"


# ─── Pricing engine ───────────────────────────────────────────────────────────

BOOKING_TIMES = {
    "dayswimming":   {"check_in": "06:00", "check_out": "17:00"},
    "nightswimming": {"check_in": "18:00", "check_out": "05:00"},
    "overnight":     {"check_in": "08:00", "check_out": "08:00"},   # next day
}

# Philippine public holidays 2025-2026 (extend as needed)
PH_HOLIDAYS = {
    date(2025, 1, 1), date(2025, 4, 9), date(2025, 4, 17),
    date(2025, 4, 18), date(2025, 5, 1), date(2025, 6, 12),
    date(2025, 8, 25), date(2025, 11, 1), date(2025, 11, 30),
    date(2025, 12, 8), date(2025, 12, 25), date(2025, 12, 30),
    date(2026, 1, 1), date(2026, 4, 1), date(2026, 4, 2),
    date(2026, 4, 3), date(2026, 5, 1), date(2026, 6, 12),
    date(2026, 8, 31), date(2026, 11, 1), date(2026, 11, 30),
    date(2026, 12, 8), date(2026, 12, 25), date(2026, 12, 30),
}


def is_weekend_or_holiday(d: date) -> bool:
    return d.weekday() >= 5 or d in PH_HOLIDAYS   # Sat=5, Sun=6


def calculate_price(
    booking_type: str,
    check_in_date: date,
    adults: int,
    youth: int,
    package=None
) -> float:
    """
    Compute the total price based on:
      - booking type (dayswimming / nightswimming / overnight)
      - weekday vs weekend/holiday
      - total pax (adults + youth)
      - package override (if a Package row is given, use its pricing)

    Default rates (from the current rate cards):
      Day Swimming   weekday ₱10,000 | weekend ₱15,000  (base 20 pax)
      Night Swimming weekday ₱11,000 | weekend ₱16,000
      Overnight      weekday ₱20,000 | weekend ₱30,000

    Extra pax: if total pax > included_pax, charge extra_pax_price per head.
    """
    total_pax = adults + youth
    is_premium = is_weekend_or_holiday(check_in_date)

    if package:
        base  = float(package.weekend_price if is_premium and package.weekend_price
                      else package.base_price)
        incl  = package.included_pax or 20
        extra = float(package.extra_pax_price or 0)
    else:
        # Built-in defaults matching the rate-card shown in the HTML
        defaults = {
            "dayswimming":   {"weekday": 10_000, "weekend": 15_000, "included": 20, "extra": 0},
            "nightswimming": {"weekday": 11_000, "weekend": 16_000, "included": 20, "extra": 0},
            "overnight":     {"weekday": 20_000, "weekend": 30_000, "included": 20, "extra": 0},
        }
        rates = defaults.get(booking_type, defaults["dayswimming"])
        base  = rates["weekend"] if is_premium else rates["weekday"]
        incl  = rates["included"]
        extra = rates["extra"]

    # Extra-pax surcharge
    extra_pax_count = max(0, total_pax - incl)
    price = base + (extra_pax_count * extra)
    return float(price)


def get_checkout_date(booking_type: str, check_in: date) -> date:
    """Return the correct check-out date based on booking type."""
    from datetime import timedelta
    if booking_type in ("nightswimming", "overnight"):
        # Night swimming: in 6 PM, out 5 AM next day
        # Overnight: in 8 AM day-1, out 8 AM day-2
        return check_in + timedelta(days=1)
    return check_in   # day swimming: same calendar day


# ─── Response helpers ─────────────────────────────────────────────────────────

def success(data=None, message: str = "OK", status: int = 200):
    from flask import jsonify
    return jsonify({"success": True, "message": message, "data": data}), status


def error(message: str = "Error", status: int = 400, data=None):
    from flask import jsonify
    return jsonify({"success": False, "message": message, "data": data}), status
