"""
app/routes/guests.py  –  Admin guest management
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app import db
from app.models import Guest, Booking
from app.utils  import success, error

guests_bp = Blueprint("guests", __name__)


# ── GET /api/guests/  ────────────────────────────────────────────────── ADMIN
@guests_bp.get("/")
@jwt_required()
def list_guests():
    search   = request.args.get("q", "")
    page     = int(request.args.get("page",     1))
    per_page = int(request.args.get("per_page", 20))

    q = Guest.query
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Guest.first_name.ilike(like)) |
            (Guest.last_name.ilike(like))  |
            (Guest.email.ilike(like))       |
            (Guest.phone.ilike(like))
        )

    paginated = q.order_by(Guest.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Enrich with last visit date
    result = []
    for g in paginated.items:
        d = g.to_dict()
        last = (
            Booking.query
            .filter_by(guest_id=g.id, status="completed")
            .order_by(Booking.check_in_date.desc())
            .first()
        )
        d["last_visit"] = last.check_in_date.isoformat() if last else None
        result.append(d)

    return success({
        "items":    result,
        "total":    paginated.total,
        "pages":    paginated.pages,
    })


# ── GET /api/guests/<id>  ────────────────────────────────────────────── ADMIN
@guests_bp.get("/<int:guest_id>")
@jwt_required()
def get_guest(guest_id):
    g = Guest.query.get_or_404(guest_id)
    d = g.to_dict()
    d["bookings"] = [b.to_dict() for b in g.bookings]
    return success(d)


# ── DELETE /api/guests/<id>  ─────────────────────────────────────────── ADMIN
@guests_bp.delete("/<int:guest_id>")
@jwt_required()
def delete_guest(guest_id):
    g = Guest.query.get_or_404(guest_id)
    db.session.delete(g)
    db.session.commit()
    return success(message="Guest deleted.")
