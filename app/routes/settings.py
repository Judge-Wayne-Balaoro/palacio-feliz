from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.utils import success, error
from app.utils.settings_store import load_settings, save_settings

settings_bp = Blueprint("settings", __name__)

@settings_bp.get("/")
def get_settings():
    return success(load_settings())

@settings_bp.put("/")
@jwt_required()
def update_settings():
    data = request.get_json(silent=True) or {}
    required = ["resort_name", "contact_email", "contact_phone", "address"]
    for field in required:
        if field in data and not str(data.get(field, "")).strip():
            return error(f"{field} cannot be empty.", 400)
    return success(save_settings(data), "Settings updated.")
