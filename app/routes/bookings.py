"""
app/routes/bookings.py  –  Customer booking submission + admin approval
"""
from datetime import date, datetime
from flask import Blueprint, request, current_app, redirect
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Booking, Guest, Package, Payment
from app.utils  import (
    success, error,
    save_upload, generate_ref_no,
    calculate_price, get_checkout_date,
    BOOKING_TIMES,
)
from app.utils.mailer import send_email, build_receipt_html, verify_booking_cancel_token

bookings_bp = Blueprint("bookings", __name__)

VALID_TYPES = ("dayswimming", "nightswimming", "overnight")


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _check_availability(booking_type: str, check_in: date, exclude_id=None):
    q = Booking.query.filter(
        Booking.check_in_date == check_in,
        Booking.status == "approved",
    )
    if exclude_id:
        q = q.filter(Booking.id != exclude_id)

    existing = q.all()

    if not existing:
        return True, ""

    existing_types = {b.booking_type for b in existing}

    if booking_type == "overnight":
        return False, "The selected date already has an approved booking and cannot accommodate an Overnight reservation."

    if "overnight" in existing_types:
        return False, "The selected date already has an Overnight booking approved."

    if booking_type in existing_types:
        label = "Day Swimming" if booking_type == "dayswimming" else "Night Swimming"
        return False, f"The selected date already has an approved {label} booking."

    return True, ""


def _parse_date(val: str):
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _safe_int(value, default=0):
    """FIX #9: Safe integer parsing that never raises."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC  –  Customer submits a new booking
# ════════════════════════════════════════════════════════════════════════════

@bookings_bp.post("/")
def create_booking():
    f = request.form

    required = ["first_name", "last_name", "email", "phone",
                "booking_type", "check_in_date", "adults", "payment_method", "downpayment", "package_id"]
    for field in required:
        if not f.get(field, "").strip():
            return error(f"Field '{field}' is required.", 400)

    booking_type = f["booking_type"].strip().lower()
    if booking_type not in VALID_TYPES:
        return error("booking_type must be: dayswimming, nightswimming, or overnight.", 400)

    check_in = _parse_date(f.get("check_in_date", ""))
    if not check_in:
        return error("Invalid check_in_date. Use YYYY-MM-DD.", 400)
    if check_in < date.today():
        return error("Check-in date cannot be in the past.", 400)

    check_out = get_checkout_date(booking_type, check_in)

    # FIX #9: Safe int parsing with proper error responses
    try:
        adults = int(f.get("adults", 0))
    except (ValueError, TypeError):
        return error("adults must be a valid number.", 400)
    try:
        youth = int(f.get("youth", 0))
    except (ValueError, TypeError):
        return error("youth must be a valid number.", 400)

    if adults < 1:
        return error("At least 1 adult is required.", 400)

    max_pax = current_app.config["MAX_PAX"]
    if adults + youth > max_pax:
        return error(f"Total guests cannot exceed {max_pax} pax.", 400)

    if not request.files.get("valid_id"):
        return error("Valid ID is required.", 400)

    available, reason = _check_availability(booking_type, check_in)
    if not available:
        return error(reason, 409)

    package = None
    if f.get("package_id"):
        package = Package.query.filter_by(
            id=f["package_id"], is_active=True
        ).first()
        if not package:
            return error("Selected package not found or inactive.", 404)

    if package and (adults + youth) > int(package.included_pax or max_pax):
        return error(f"Too much for pax. Maximum allowed for this package is {int(package.included_pax or max_pax)}.", 400)

    total_price = calculate_price(booking_type, check_in, adults, youth, package)

    try:
        downpayment = float(f.get("downpayment", 0))
    except ValueError:
        return error("downpayment must be a number.", 400)

    min_dp = current_app.config["DOWNPAYMENT_REQUIRED"]
    if downpayment < min_dp:
        return error(f"Minimum downpayment is ₱{min_dp:,.2f}.", 400)
    if downpayment > total_price:
        downpayment = total_price

    balance = total_price - downpayment

    payment_method = f["payment_method"].strip().lower()
    if payment_method not in ("gcash", "paymaya", "cash"):
        return error("payment_method must be: gcash, paymaya, or cash.", 400)

    payment_screenshot_url = None
    if payment_method in ("gcash", "paymaya"):
        ss_file = request.files.get("payment_screenshot")
        payment_screenshot_url = save_upload(
            ss_file, "payments",
            current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
        )
        if not payment_screenshot_url:
            return error("Transaction screenshot is required for GCash/PayMaya payments.", 400)

    valid_id_url = save_upload(
        request.files.get("valid_id"),
        "valid_ids",
        current_app.config["ALLOWED_DOC_EXTENSIONS"]
    )

    guest = Guest.query.filter_by(email=f["email"].strip().lower()).first()
    if not guest:
        guest = Guest(
            first_name=f["first_name"].strip(),
            last_name =f["last_name"].strip(),
            email     =f["email"].strip().lower(),
            phone     =f["phone"].strip(),
            valid_id_url=valid_id_url,
        )
        db.session.add(guest)
        db.session.flush()
    else:
        guest.first_name = f["first_name"].strip()
        guest.last_name  = f["last_name"].strip()
        guest.phone      = f["phone"].strip()
        if valid_id_url:
            guest.valid_id_url = valid_id_url

    times = BOOKING_TIMES.get(booking_type, {})
    booking = Booking(
        guest          = guest,
        package_id     = package.id if package else None,
        booking_type   = booking_type,
        check_in_date  = check_in,
        check_out_date = check_out,
        check_in_time  = times.get("check_in"),
        check_out_time = times.get("check_out"),
        adults         = adults,
        youth          = youth,
        total_price    = total_price,
        downpayment    = downpayment,
        balance        = balance,
        payment_method = payment_method,
        payment_status = "paid" if balance == 0 else "partial",
        payment_ref    = f.get("payment_ref", "").strip() or None,
        payment_number = f.get("payment_number", "").strip() or None,
        payment_screenshot_url = payment_screenshot_url,
        special_request= f.get("special_request", "").strip() or None,
        status         = "pending",
    )
    db.session.add(booking)

    payment_rec = Payment(
        booking    = booking,
        amount     = downpayment,
        method     = payment_method,
        reference_no=f.get("payment_ref") or None,
        screenshot_url=payment_screenshot_url,
        note       = "Downpayment upon booking",
    )
    db.session.add(payment_rec)

    # FIX #8: Retry on reference_no collision with up to 5 attempts
    for attempt in range(5):
        booking.reference_no = generate_ref_no()
        try:
            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == 4:
                return error("Could not generate a unique booking reference. Please try again.", 500)

    return success(
        booking.to_dict(),
        "Booking submitted! We'll contact you shortly to confirm.",
        201
    )


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC  –  Check availability
# ════════════════════════════════════════════════════════════════════════════

@bookings_bp.get("/check-availability")
def check_availability():
    btype     = request.args.get("booking_type", "").lower()
    date_str  = request.args.get("check_in_date", "")

    if btype not in VALID_TYPES:
        return error("Invalid booking_type.", 400)

    check_in = _parse_date(date_str)
    if not check_in:
        return error("Invalid date.", 400)

    available, reason = _check_availability(btype, check_in)
    return success({"available": available, "reason": reason})


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC  –  Calculate price preview
# ════════════════════════════════════════════════════════════════════════════

@bookings_bp.get("/price")
def price_preview():
    btype    = request.args.get("booking_type", "").lower()
    date_str = request.args.get("check_in_date", "")

    if btype not in VALID_TYPES:
        return error("Invalid booking_type.", 400)

    check_in = _parse_date(date_str)
    if not check_in:
        return error("Invalid date.", 400)

    # FIX #9: Safe int parsing on query params
    try:
        adults = int(request.args.get("adults", 1))
        youth  = int(request.args.get("youth",  0))
    except (ValueError, TypeError):
        return error("adults and youth must be valid integers.", 400)

    pkg_id  = request.args.get("package_id")
    package = None
    if pkg_id:
        package = Package.query.filter_by(id=pkg_id, is_active=True).first()

    price     = calculate_price(btype, check_in, adults, youth, package)
    check_out = get_checkout_date(btype, check_in)
    times     = BOOKING_TIMES.get(btype, {})

    return success({
        "total_price":     price,
        "check_out_date":  check_out.isoformat(),
        "check_in_time":   times.get("check_in"),
        "check_out_time":  times.get("check_out"),
        "downpayment_min": current_app.config["DOWNPAYMENT_REQUIRED"],
    })


# ════════════════════════════════════════════════════════════════════════════
# ADMIN  –  List all bookings
# ════════════════════════════════════════════════════════════════════════════

@bookings_bp.get("/")
@jwt_required()
def list_bookings():
    status      = request.args.get("status")
    search      = request.args.get("q", "")
    date_filter = request.args.get("date")

    # FIX #9: Safe int parsing
    try:
        page     = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except (ValueError, TypeError):
        page, per_page = 1, 20

    q = Booking.query.join(Guest)

    if status:
        q = q.filter(Booking.status == status)
    if date_filter:
        d = _parse_date(date_filter)
        if d:
            q = q.filter(Booking.check_in_date == d)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Guest.first_name.ilike(like)) |
            (Guest.last_name.ilike(like))  |
            (Guest.email.ilike(like))       |
            (Booking.reference_no.ilike(like))
        )

    paginated = q.order_by(Booking.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return success({
        "items":      [b.to_dict() for b in paginated.items],
        "total":      paginated.total,
        "page":       paginated.page,
        "pages":      paginated.pages,
        "per_page":   per_page,
    })


# ════════════════════════════════════════════════════════════════════════════
# ADMIN  –  Get single booking
# ════════════════════════════════════════════════════════════════════════════

@bookings_bp.get("/<int:booking_id>")
@jwt_required()
def get_booking(booking_id):
    b = Booking.query.get_or_404(booking_id)
    return success(b.to_dict())


# ════════════════════════════════════════════════════════════════════════════
# ADMIN  –  Approve / Reject / Complete / Cancel
# ════════════════════════════════════════════════════════════════════════════

@bookings_bp.patch("/<int:booking_id>/status")
@jwt_required()
def update_status(booking_id):
    b    = Booking.query.get_or_404(booking_id)
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").lower()

    allowed = ("approved", "rejected", "completed", "cancelled", "pending")
    if new_status not in allowed:
        return error(f"status must be one of: {', '.join(allowed)}", 400)

    if new_status == "approved" and b.status != "approved":
        available, reason = _check_availability(b.booking_type, b.check_in_date, exclude_id=b.id)
        if not available:
            return error(f"Cannot approve: {reason}", 409)

    b.status = new_status
    db.session.commit()

    email_notice = None
    email_sent = None
    if new_status == "approved" and b.guest and b.guest.email:
        email_sent, msg = send_email(b.guest.email, f"Booking Approved - {b.reference_no}", build_receipt_html(b))
        email_notice = msg

    payload = b.to_dict()
    if email_sent is not None:
        payload["email_sent"] = email_sent
        payload["email_notice"] = email_notice

    message = f"Booking {new_status}."
    if email_notice:
        message += f" {email_notice}"
    return success(payload, message)


# ════════════════════════════════════════════════════════════════════════════
# ADMIN  –  Delete booking
# ════════════════════════════════════════════════════════════════════════════

@bookings_bp.delete("/<int:booking_id>")
@jwt_required()
def delete_booking(booking_id):
    b = Booking.query.get_or_404(booking_id)
    db.session.delete(b)
    db.session.commit()
    return success(message="Booking deleted.")


# ════════════════════════════════════════════════════════════════════════════
# ADMIN  –  Pending count
# ════════════════════════════════════════════════════════════════════════════

@bookings_bp.get("/pending-count")
@jwt_required()
def pending_count():
    count = Booking.query.filter_by(status="pending").count()
    return success({"count": count})


@bookings_bp.get("/cancel/<token>")
def cancel_booking(token):
    try:
        payload = verify_booking_cancel_token(token)
        ref = payload.get("reference_no")
    except Exception:
        return error("Invalid or expired cancellation link.", 400)

    b = Booking.query.filter_by(reference_no=ref).first()
    if not b:
        return error("Booking not found.", 404)

    if b.status == "cancelled":
        return success({"reference_no": b.reference_no}, "Booking is already cancelled.")
    if b.status == "completed":
        return error("Completed bookings can no longer be cancelled.", 400)

    b.status = "cancelled"
    db.session.commit()

    target = current_app.config.get('PUBLIC_BASE_URL', '').rstrip('/')
    if target:
        return redirect(f"{target}/?cancelled={b.reference_no}")
    return success({"reference_no": b.reference_no}, "Booking cancelled successfully. A ₱2,000 convenience fee applies.")
