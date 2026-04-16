"""
app/routes/payments.py  –  Payment tracking and recording
"""
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required

from app import db
from app.models import Payment, Booking
from app.utils  import success, error, save_upload

payments_bp = Blueprint("payments", __name__)


# ── GET /api/payments/  ──────────────────────────────────────────────── ADMIN
@payments_bp.get("/")
@jwt_required()
def list_payments():
    status   = request.args.get("status")   # paid | partial | pending
    page     = int(request.args.get("page",     1))
    per_page = int(request.args.get("per_page", 20))

    q = Payment.query
    if status:
        # Filter via the parent booking's payment_status
        q = q.join(Booking).filter(Booking.payment_status == status)

    paginated = q.order_by(Payment.paid_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return success({
        "items":    [p.to_dict() for p in paginated.items],
        "total":    paginated.total,
        "pages":    paginated.pages,
    })


# ── GET /api/payments/<booking_id>  ─────────────────────────────────── ADMIN
@payments_bp.get("/<int:booking_id>")
@jwt_required()
def booking_payments(booking_id):
    b = Booking.query.get_or_404(booking_id)
    return success({
        "booking_id":     b.id,
        "total_price":    float(b.total_price),
        "downpayment":    float(b.downpayment),
        "balance":        float(b.balance),
        "payment_status": b.payment_status,
        "payments":       [p.to_dict() for p in b.payments],
    })


# ── POST /api/payments/<booking_id>  ────────────────────────────────── ADMIN
@payments_bp.post("/<int:booking_id>")
@jwt_required()
def add_payment(booking_id):
    """Record an additional payment (e.g. balance settled at the venue)."""
    b = Booking.query.get_or_404(booking_id)

    if request.content_type and "multipart" in request.content_type:
        f          = request.form
        screenshot = save_upload(
            request.files.get("screenshot"),
            "payments",
            current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
        )
    else:
        f          = request.get_json(silent=True) or {}
        screenshot = None

    try:
        amount = float(f.get("amount", 0))
    except (ValueError, TypeError):
        return error("amount must be a number.", 400)

    if amount <= 0:
        return error("amount must be greater than 0.", 400)

    method   = f.get("method", "cash")
    ref_no   = f.get("reference_no", "")
    note     = f.get("note", "")

    payment = Payment(
        booking_id    = b.id,
        amount        = amount,
        method        = method,
        reference_no  = ref_no or None,
        screenshot_url= screenshot,
        note          = note or None,
    )
    db.session.add(payment)

    # Update booking balance
    total_paid = sum(float(p.amount) for p in b.payments) + amount
    b.balance  = max(0, float(b.total_price) - total_paid)

    if b.balance <= 0:
        b.payment_status = "paid"
        b.balance        = 0
    else:
        b.payment_status = "partial"

    db.session.commit()
    return success(payment.to_dict(), "Payment recorded.", 201)
