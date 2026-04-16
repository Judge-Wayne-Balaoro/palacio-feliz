"""
seed.py  –  Initialize the database and create default admin + sample packages.

Usage:
    python seed.py
"""
import os
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import OperationalError
from run import app, db
from app.models import AdminUser, Package


def _validate_database_url():
    database_url = os.getenv("DATABASE_URL", "")
    placeholders = ("username", "password", "your_password", "change-me")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing in your .env file.")
    if any(token in database_url.lower() for token in placeholders):
        raise RuntimeError(
            "DATABASE_URL still contains placeholder values. Edit .env and replace username/password with your real MySQL credentials."
        )


def seed():
    with app.app_context():
        _validate_database_url()
        # Create all tables
        try:
            db.create_all()
        except OperationalError as exc:
            raise RuntimeError(
                "Database connection failed. Check that MySQL is running, the palacio_feliz database exists, and DATABASE_URL in .env uses the correct username/password."
            ) from exc
        print("✅  Tables created.")

        # ── Default admin ────────────────────────────────────────────────────
        if not AdminUser.query.filter_by(username="admin").first():
            admin = AdminUser(
                username  = "admin",
                email     = "admin@palaciofeliz.com",
                password  = generate_password_hash("Admin@1234"),
                full_name = "Resort Manager",
                role      = "admin",
            )
            db.session.add(admin)
            print("✅  Default admin created  →  username: admin  /  password: Admin@1234")
        else:
            print("ℹ️   Admin already exists, skipping.")

        # ── Default packages (matching the HTML rate cards) ──────────────────
        default_packages = [
            {
                "name":           "Day Tour",
                "description":    "Enjoy the resort from 6:00 AM to 5:00 PM. Includes unlimited pool access for up to 20 guests.",
                "inclusion":      "Pool access, cottage use, tables and chairs for up to 20 guests.",
                "icon":           "🌤️",
                "base_price":     10_000,
                "weekend_price":  15_000,
                "holiday_price":  18_000,
                "booking_type":   "dayswimming",
                "time_slot":      "6:00 am to 5:00 pm",
                "included_pax":   20,
                "extra_pax_price":0,
                "duration_hours": 11,
            },
            {
                "name":           "Night Tour",
                "description":    "Experience the resort from 6:00 PM to 5:00 AM. Includes unlimited pool access for up to 20 guests.",
                "inclusion":      "Night pool access, cottage use, tables and chairs for up to 20 guests.",
                "icon":           "🌙",
                "base_price":     11_000,
                "weekend_price":  16_000,
                "holiday_price":  19_000,
                "booking_type":   "nightswimming",
                "time_slot":      "6:00 pm to 5:00 am",
                "included_pax":   20,
                "extra_pax_price":0,
                "duration_hours": 11,
            },
            {
                "name":           "Overnight",
                "description":    "Stay overnight from 6:00 AM to 5:00 AM next day. Includes unlimited pool access for up to 20 guests.",
                "inclusion":      "Overnight stay, pool access, cottage use, tables and chairs for up to 20 guests.",
                "icon":           "🏡",
                "base_price":     20_000,
                "weekend_price":  30_000,
                "holiday_price":  35_000,
                "booking_type":   "overnight",
                "time_slot":      "6:00 am to 5:00 am",
                "included_pax":   20,
                "extra_pax_price":0,
                "duration_hours": 24,
            },
        ]

        added = 0
        updated = 0
        for pd in default_packages:
            existing = Package.query.filter_by(name=pd["name"]).first()
            if not existing:
                db.session.add(Package(**pd))
                added += 1
                continue

            changed = False
            for key, value in pd.items():
                if getattr(existing, key, None) != value:
                    setattr(existing, key, value)
                    changed = True
            if changed:
                updated += 1

        if added:
            print(f"✅  {added} default package(s) seeded.")
        if updated:
            print(f"✅  {updated} default package(s) updated.")
        if not added and not updated:
            print("ℹ️   Packages already up to date, skipping.")

        db.session.commit()
        print("\n🎉  Database ready.")


if __name__ == "__main__":
    seed()
