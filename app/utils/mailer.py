import os
import smtplib
import ssl
from email.message import EmailMessage
from flask import current_app, request
from itsdangerous import URLSafeSerializer

from app.utils.settings_store import load_settings


def booking_cancel_token(reference_no: str) -> str:
    secret = current_app.config.get("SECRET_KEY", "dev-secret-key")
    s = URLSafeSerializer(secret, salt="booking-cancel")
    return s.dumps({"reference_no": reference_no})


def verify_booking_cancel_token(token: str):
    secret = current_app.config.get("SECRET_KEY", "dev-secret-key")
    s = URLSafeSerializer(secret, salt="booking-cancel")
    return s.loads(token)


def build_receipt_html(booking):
    settings = load_settings()
    guest_name = booking.guest.full_name if booking.guest else "Guest"
    package_name = booking.package.name if booking.package else booking.booking_type.replace("swimming", " Swimming").title()
    total_pax = booking.adults + booking.youth
    token = booking_cancel_token(booking.reference_no)
    public_base_url = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    if public_base_url:
        cancel_url = f"{public_base_url}/api/bookings/cancel/{token}"
    else:
        fallback_base = request.url_root.rstrip("/") if request else "http://127.0.0.1:5000"
        cancel_url = f"{fallback_base}/api/bookings/cancel/{token}"
    return f"""
    <div style=\"font-family:Arial,sans-serif;max-width:680px;margin:0 auto;color:#1f2937;line-height:1.6\">
      <div style=\"background:#111827;color:#fff;padding:24px;border-radius:16px 16px 0 0\">
        <h2 style=\"margin:0 0 8px;\">Thanks For Booking With Us! Enjoy your stay.</h2>
        <p style=\"margin:0;opacity:.9\">Your reservation has been reviewed and approved. Please keep this receipt for check-in.</p>
      </div>
      <div style=\"border:1px solid #e5e7eb;border-top:none;padding:24px;border-radius:0 0 16px 16px;background:#fff\">
        <p><strong>Booking Status:</strong> Confirmed</p>
        <p><strong>Booking ID:</strong> {booking.reference_no}</p>
        <p><strong>Guest Name:</strong> {guest_name}</p>
        <p><strong>Accommodation Type / Package:</strong> {package_name}</p>
        <p><strong>No. of Pax:</strong> {total_pax}</p>
        <p><strong>Check-in:</strong> {booking.check_in_date.isoformat()} {booking.check_in_time or ''}</p>
        <p><strong>Check-out:</strong> {booking.check_out_date.isoformat()} {booking.check_out_time or ''}</p>
        <p><strong>Total Paid:</strong> ₱{float(booking.downpayment):,.2f}</p>
        <p><a href=\"{cancel_url}\" style=\"display:inline-block;background:#b45309;color:#fff;padding:12px 18px;border-radius:10px;text-decoration:none;\">Cancel Booking</a></p>
        <p><strong>Important:</strong> If you cancel the booking, you have to pay 2,000 pesos as convenience fee.</p>
        <p>Please show this receipt to the receptionist of {settings['resort_name']}, along with the valid ID attached in the reservation you submitted.</p>
        <hr style=\"border:none;border-top:1px solid #e5e7eb;margin:20px 0\">
        <p style=\"font-size:12px;color:#6b7280\">© 2025 Palacio Feliz. All rights reserved.</p>
      </div>
    </div>
    """


def send_email(to_email: str, subject: str, html: str):
    host = (current_app.config.get("MAIL_SERVER") or os.getenv("MAIL_SERVER") or "").strip()
    port = int(current_app.config.get("MAIL_PORT") or os.getenv("MAIL_PORT", 587))
    username = (current_app.config.get("MAIL_USERNAME") or os.getenv("MAIL_USERNAME") or "").strip()
    password = (current_app.config.get("MAIL_PASSWORD") or os.getenv("MAIL_PASSWORD") or "").strip()
    sender = (current_app.config.get("MAIL_DEFAULT_SENDER") or username or "").strip()
    use_tls = str(current_app.config.get("MAIL_USE_TLS") or os.getenv("MAIL_USE_TLS", "true")).lower() == "true"

    if not all([host, port, username, password, sender, to_email]):
        current_app.logger.error("Email settings are not configured properly.")
        return False, "Email settings are not configured."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content("Your booking has been approved. Please view the HTML version of this email.")
    msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            if use_tls:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            server.login(username, password)
            server.send_message(msg)
        current_app.logger.info("Booking approval email sent to %s", to_email)
        return True, "Email sent successfully."
    except Exception as exc:
        current_app.logger.exception("Failed to send booking approval email to %s", to_email)
        return False, f"Email failed to send: {exc}"
