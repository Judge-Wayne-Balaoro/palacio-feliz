"""
app/routes/auth.py  –  Admin login / logout / change-password
"""
from flask import Blueprint, request, current_app
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from app.models import AdminUser
from app.utils  import success, error

auth_bp = Blueprint("auth", __name__)


# ── POST /api/auth/login ──────────────────────────────────────────────────────
@auth_bp.post("/login")
def login():
    # Force JSON parsing - reject requests without proper Content-Type
    if not request.is_json:
        return error("Content-Type must be application/json.", 400)

    data = request.get_json(silent=True)
    if data is None:
        return error("Invalid JSON body.", 400)

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return error("Username and password are required.", 400)

    user = AdminUser.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return error("Invalid credentials.", 401)

    token = create_access_token(identity=str(user.id))
    return success({"token": token, "admin": user.to_dict()}, "Login successful.")


# ── GET /api/auth/me ──────────────────────────────────────────────────────────
@auth_bp.get("/me")
@jwt_required()
def me():
    uid  = int(get_jwt_identity())
    user = AdminUser.query.get_or_404(uid)
    return success(user.to_dict())


# ── POST /api/auth/change-password ───────────────────────────────────────────
@auth_bp.post("/change-password")
@jwt_required()
def change_password():
    uid  = int(get_jwt_identity())
    user = AdminUser.query.get_or_404(uid)
    data = request.get_json(silent=True) or {}

    old_pw  = data.get("current_password", "")
    new_pw  = data.get("new_password", "")
    conf_pw = data.get("confirm_password", "")

    if not check_password_hash(user.password, old_pw):
        return error("Current password is incorrect.", 401)
    if len(new_pw) < 6:
        return error("New password must be at least 6 characters.", 400)
    if new_pw != conf_pw:
        return error("Passwords do not match.", 400)

    user.password = generate_password_hash(new_pw)
    db.session.commit()
    return success(message="Password changed successfully.")


# ── POST /api/auth/register  (FIX #7: protected by SETUP_TOKEN) ──────────────
@auth_bp.post("/register")
def register():
    """
    Protected by a one-time setup token stored in SETUP_TOKEN env var.
    Pass the token in the X-Setup-Token header when creating the first admin.
    Remove or disable this route once the initial admin is created.
    """
    setup_token = request.headers.get("X-Setup-Token", "")
    expected    = current_app.config.get("SETUP_TOKEN", "")

    if not expected or setup_token != expected:
        return error("Unauthorized. Valid X-Setup-Token header required.", 403)

    if not request.is_json:
        return error("Content-Type must be application/json.", 400)

    data      = request.get_json(silent=True) or {}
    username  = data.get("username", "").strip()
    email     = data.get("email", "").strip()
    password  = data.get("password", "")
    full_name = data.get("full_name", "Admin")

    if not username or not email or not password:
        return error("username, email and password are required.", 400)

    if AdminUser.query.filter(
        (AdminUser.username == username) | (AdminUser.email == email)
    ).first():
        return error("Username or email already exists.", 409)

    user = AdminUser(
        username=username,
        email=email,
        password=generate_password_hash(password),
        full_name=full_name,
    )
    db.session.add(user)
    db.session.commit()
    return success(user.to_dict(), "Admin created.", 201)


# ── GET /api/auth/health ─────────────────────────────────────────────────────
@auth_bp.get("/health")
def health_check():
    """
    Diagnostic endpoint to check environment and admin user status.
    Useful for debugging production deployment issues.
    """
    admin_count = AdminUser.query.count()
    has_setup_token = bool(current_app.config.get("SETUP_TOKEN", ""))

    return success({
        "admin_users_count": admin_count,
        "has_setup_token": has_setup_token,
        "flask_env": current_app.config.get("FLASK_ENV", "unknown"),
        "database_configured": bool(current_app.config.get("SQLALCHEMY_DATABASE_URI")),
    })
