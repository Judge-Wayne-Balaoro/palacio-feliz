import json, os
from flask import current_app

DEFAULT_SETTINGS = {
    "resort_name": "Palacio Feliz",
    "contact_email": "palaciofelizprivateresort@gmail.com",
    "contact_phone": "0931-058-3564",
    "address": "Gaya Gaya Bulacan, Evergreen Ave, Bulacan",
}


def _settings_path():
    base = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "resort_settings.json")


def load_settings():
    path = _settings_path()
    if not os.path.exists(path):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = DEFAULT_SETTINGS.copy()
        merged.update({k: v for k, v in data.items() if v is not None})
        return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(data: dict):
    merged = load_settings()
    merged.update({k: v for k, v in data.items() if v is not None})
    path = _settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged
