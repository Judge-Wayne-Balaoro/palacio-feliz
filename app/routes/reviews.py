"""
app/routes/reviews.py  –  Customer review submission + admin management
"""
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required

from app import db
from app.models import Review, ReviewMedia, Guest
from app.utils  import success, error, save_upload

reviews_bp = Blueprint("reviews", __name__)

MAX_MEDIA = 6
ALLOWED_MEDIA = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "mov", "avi", "mkv"}


def _media_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return "video" if ext in ("mp4", "mov", "avi", "mkv") else "image"


# ── POST /api/reviews/  ──────────────────────────────────────────────── PUBLIC
@reviews_bp.post("/")
def submit_review():
    """
    Accepts multipart/form-data.
    Fields: guest_name, rating, body
    Files:  media[]  (up to 6 pictures or videos)
    """
    f    = request.form
    name = f.get("guest_name", "").strip()
    body = f.get("body",       "").strip()

    if not name:
        return error("guest_name is required.", 400)
    if not body:
        return error("Review text is required.", 400)

    try:
        rating = int(f.get("rating", 0))
    except ValueError:
        rating = 0

    if rating not in range(1, 6):
        return error("Rating must be between 1 and 5.", 400)

    media_files = request.files.getlist("media")
    if len(media_files) > MAX_MEDIA:
        return error(f"You can upload a maximum of {MAX_MEDIA} photos/videos.", 400)

    review = Review(
        guest_name = name,
        rating     = rating,
        body       = body,
        is_visible = True,
    )
    db.session.add(review)
    db.session.flush()   # get review.id before committing

    for mf in media_files:
        if mf and mf.filename:
            url = save_upload(mf, "reviews", ALLOWED_MEDIA)
            if url:
                db.session.add(ReviewMedia(
                    review_id  = review.id,
                    file_url   = url,
                    media_type = _media_type(mf.filename),
                ))

    db.session.commit()
    return success(review.to_dict(), "Your review has been submitted! Thank you!", 201)


# ── GET /api/reviews/  ───────────────────────────────────────────────── PUBLIC
@reviews_bp.get("/")
def list_reviews():
    """Return all visible reviews (newest first)."""
    page     = int(request.args.get("page",     1))
    per_page = int(request.args.get("per_page", 12))

    paginated = (
        Review.query
        .filter_by(is_visible=True)
        .order_by(Review.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return success({
        "items":    [r.to_dict() for r in paginated.items],
        "total":    paginated.total,
        "page":     paginated.page,
        "pages":    paginated.pages,
        "per_page": per_page,
    })


# ── GET /api/reviews/all  ────────────────────────────────────────────── ADMIN
@reviews_bp.get("/all")
@jwt_required()
def list_all_reviews():
    """Admin: all reviews including hidden."""
    page     = int(request.args.get("page",     1))
    per_page = int(request.args.get("per_page", 20))

    paginated = (
        Review.query
        .order_by(Review.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    return success({
        "items":    [r.to_dict() for r in paginated.items],
        "total":    paginated.total,
        "pages":    paginated.pages,
    })


# ── PATCH /api/reviews/<id>/visibility  ─────────────────────────────── ADMIN
@reviews_bp.patch("/<int:review_id>/visibility")
@jwt_required()
def toggle_visibility(review_id):
    """Admin can show/hide a review."""
    r    = Review.query.get_or_404(review_id)
    data = request.get_json(silent=True) or {}
    r.is_visible = bool(data.get("is_visible", not r.is_visible))
    db.session.commit()
    return success(r.to_dict(), "Visibility updated.")


# ── DELETE /api/reviews/<id>  ────────────────────────────────────────── ADMIN
@reviews_bp.delete("/<int:review_id>")
@jwt_required()
def delete_review(review_id):
    r = Review.query.get_or_404(review_id)
    db.session.delete(r)
    db.session.commit()
    return success(message="Review deleted.")
