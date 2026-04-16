"""
app/routes/packages.py  –  Admin CRUD for packages; public read
"""
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required

from app import db
from app.models import Package
from app.utils  import success, error, save_upload

packages_bp = Blueprint("packages", __name__)


# ── GET /api/packages/  ──────────────────────────────────────────────── PUBLIC
@packages_bp.get("/")
def list_packages():
    """Customer-facing: return only active packages."""
    packages = Package.query.filter_by(is_active=True).order_by(Package.id).all()
    return success([p.to_dict() for p in packages])


# ── GET /api/packages/all  ───────────────────────────────────────────── ADMIN
@packages_bp.get("/all")
@jwt_required()
def list_all_packages():
    """Admin: return all packages including inactive."""
    packages = Package.query.order_by(Package.id).all()
    return success([p.to_dict() for p in packages])


# ── GET /api/packages/<id>  ──────────────────────────────────────────── PUBLIC
@packages_bp.get("/<int:pkg_id>")
def get_package(pkg_id):
    p = Package.query.get_or_404(pkg_id)
    return success(p.to_dict())


# ── POST /api/packages/  ─────────────────────────────────────────────── ADMIN
@packages_bp.post("/")
@jwt_required()
def create_package():
    """
    Accepts multipart/form-data (for optional image upload)
    or application/json (no image).
    """
    if request.content_type and "multipart" in request.content_type:
        f = request.form
        image_url = save_upload(
            request.files.get("image"),
            "packages",
            current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
        )
    else:
        f = request.get_json(silent=True) or {}
        image_url = None

    name = str(f.get("name", "")).strip()
    if not name:
        return error("Package name is required.", 400)

    weekday_price_raw = f.get("weekday_price", f.get("base_price", 0))
    weekend_price_raw = f.get("weekend_price", 0)
    holiday_price_raw = f.get("holiday_price", weekend_price_raw or weekday_price_raw)

    try:
        weekday_price = float(weekday_price_raw or 0)
        weekend_price = float(weekend_price_raw or 0)
        holiday_price = float(holiday_price_raw or 0)
    except (ValueError, TypeError):
        return error("Package rates must be valid numbers.", 400)

    pkg = Package(
        name           = name,
        description    = f.get("description") or f.get("inclusion", ""),
        inclusion      = f.get("inclusion") or f.get("description", ""),
        icon           = f.get("icon", "⭐"),
        image_url      = image_url,
        base_price     = weekday_price,
        weekend_price  = weekend_price,
        holiday_price  = holiday_price,
        booking_type   = f.get("booking_type", "custom"),
        time_slot      = f.get("time_slot", ""),
        included_pax   = int(f.get("included_pax", f.get("pax_included", 20))),
        extra_pax_price= float(f.get("extra_pax_price", 0)),
        duration_hours = int(f["duration_hours"]) if f.get("duration_hours") else None,
        is_active      = str(f.get("is_active", "true")).lower() != "false",
    )
    db.session.add(pkg)
    db.session.commit()
    return success(pkg.to_dict(), "Package created.", 201)


# ── PUT /api/packages/<id>  ──────────────────────────────────────────── ADMIN
@packages_bp.put("/<int:pkg_id>")
@jwt_required()
def update_package(pkg_id):
    pkg = Package.query.get_or_404(pkg_id)

    if request.content_type and "multipart" in request.content_type:
        f = request.form
        new_image = save_upload(
            request.files.get("image"),
            "packages",
            current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
        )
        if new_image:
            pkg.image_url = new_image
    else:
        f = request.get_json(silent=True) or {}

    if f.get("name"): pkg.name = f["name"].strip()
    if f.get("description") is not None: pkg.description = f["description"]
    if f.get("inclusion") is not None:
        pkg.inclusion = f["inclusion"]
        if not f.get("description"):
            pkg.description = f["inclusion"]
    if f.get("icon"): pkg.icon = f["icon"]
    if f.get("base_price") is not None or f.get("weekday_price") is not None:
        pkg.base_price = float(f.get("weekday_price", f.get("base_price", 0)) or 0)
    if f.get("weekend_price") is not None: pkg.weekend_price = float(f.get("weekend_price") or 0)
    if f.get("holiday_price") is not None: pkg.holiday_price = float(f.get("holiday_price") or 0)
    if f.get("booking_type"): pkg.booking_type = f["booking_type"]
    if f.get("time_slot") is not None: pkg.time_slot = f["time_slot"]
    if f.get("included_pax") is not None or f.get("pax_included") is not None:
        pkg.included_pax = int(f.get("included_pax", f.get("pax_included", 0)) or 0)
    if f.get("extra_pax_price") is not None: pkg.extra_pax_price = float(f.get("extra_pax_price") or 0)
    if f.get("duration_hours") is not None: pkg.duration_hours = int(f.get("duration_hours") or 0)
    if f.get("is_active") is not None:
        pkg.is_active = str(f["is_active"]).lower() != "false"

    db.session.commit()
    return success(pkg.to_dict(), "Package updated.")


# ── DELETE /api/packages/<id>  ───────────────────────────────────────── ADMIN
@packages_bp.delete("/<int:pkg_id>")
@jwt_required()
def delete_package(pkg_id):
    pkg = Package.query.get_or_404(pkg_id)
    # Soft-delete: mark inactive instead of hard-delete to preserve history
    pkg.is_active = False
    db.session.commit()
    return success(message="Package deactivated.")


# ── DELETE /api/packages/<id>/hard  ─────────────────────────────────── ADMIN
@packages_bp.delete("/<int:pkg_id>/hard")
@jwt_required()
def hard_delete_package(pkg_id):
    pkg = Package.query.get_or_404(pkg_id)
    db.session.delete(pkg)
    db.session.commit()
    return success(message="Package permanently deleted.")
