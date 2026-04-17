"""
models/__init__.py  –  All SQLAlchemy models for Palacio Feliz
"""
from datetime import datetime, timezone
from app import db
from werkzeug.security import generate_password_hash, check_password_hash


def _now():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN USER
# ═══════════════════════════════════════════════════════════════════════════
class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(40), default="admin")
    created_at = db.Column(db.DateTime, default=_now)

    # 🔐 SET PASSWORD (hash)
    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    # 🔐 CHECK PASSWORD
    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
        }


# ═══════════════════════════════════════════════════════════════════════════
# PACKAGE  (admin-managed; shown on customer page)
# ═══════════════════════════════════════════════════════════════════════════
class Package(db.Model):
    __tablename__ = "packages"

    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(120), nullable=False)
    description      = db.Column(db.Text)
    inclusion        = db.Column(db.Text)
    icon             = db.Column(db.String(10), default="⭐")
    image_url        = db.Column(db.String(512))

    base_price       = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    weekend_price    = db.Column(db.Numeric(12, 2))
    holiday_price    = db.Column(db.Numeric(12, 2))

    booking_type     = db.Column(db.String(30), default="custom")
    time_slot        = db.Column(db.String(80))

    included_pax     = db.Column(db.Integer, default=20)
    extra_pax_price  = db.Column(db.Numeric(10, 2), default=0)

    duration_hours   = db.Column(db.Integer)
    is_active        = db.Column(db.Boolean, default=True)
    created_at       = db.Column(db.DateTime, default=_now)
    updated_at       = db.Column(db.DateTime, default=_now, onupdate=_now)

    bookings = db.relationship("Booking", backref="package", lazy=True)

    def to_dict(self):
        return {
            "id":             self.id,
            "name":           self.name,
            "description":    self.description,
            "inclusion":      self.inclusion,
            "icon":           self.icon,
            "image_url":      self.image_url,
            "base_price":     float(self.base_price),
            "weekday_price":  float(self.base_price),
            "weekend_price":  float(self.weekend_price) if self.weekend_price is not None else None,
            "holiday_price":  float(self.holiday_price) if self.holiday_price is not None else None,
            "booking_type":   self.booking_type,
            "time_slot":      self.time_slot,
            "included_pax":   self.included_pax,
            "pax_included":   self.included_pax,
            "extra_pax_price":float(self.extra_pax_price),
            "duration_hours": self.duration_hours,
            "is_active":      self.is_active,
        }


# ═══════════════════════════════════════════════════════════════════════════
# GUEST  (contact info attached to a booking)
# ═══════════════════════════════════════════════════════════════════════════
class Guest(db.Model):
    __tablename__ = "guests"

    id           = db.Column(db.Integer, primary_key=True)
    first_name   = db.Column(db.String(80),  nullable=False)
    last_name    = db.Column(db.String(80),  nullable=False)
    email        = db.Column(db.String(120), nullable=False)
    phone        = db.Column(db.String(30),  nullable=False)
    valid_id_url = db.Column(db.String(512))
    created_at   = db.Column(db.DateTime, default=_now)

    bookings = db.relationship("Booking", backref="guest", lazy=True)
    reviews  = db.relationship("Review",  backref="guest", lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            "id":           self.id,
            "first_name":   self.first_name,
            "last_name":    self.last_name,
            "full_name":    self.full_name,
            "email":        self.email,
            "phone":        self.phone,
            "valid_id_url": self.valid_id_url,
            "created_at":   self.created_at.isoformat(),
            "total_bookings": len(self.bookings),
        }


# ═══════════════════════════════════════════════════════════════════════════
# BOOKING
# ═══════════════════════════════════════════════════════════════════════════
class Booking(db.Model):
    __tablename__ = "bookings"

    id              = db.Column(db.Integer, primary_key=True)
    reference_no    = db.Column(db.String(20), unique=True, nullable=False)

    guest_id        = db.Column(db.Integer, db.ForeignKey("guests.id"), nullable=False)
    package_id      = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=True)

    booking_type    = db.Column(db.String(20), nullable=False)
    check_in_date   = db.Column(db.Date, nullable=False)
    check_out_date  = db.Column(db.Date, nullable=False)
    check_in_time   = db.Column(db.String(8))
    check_out_time  = db.Column(db.String(8))

    adults          = db.Column(db.Integer, nullable=False, default=1)
    youth           = db.Column(db.Integer, nullable=False, default=0)

    total_price     = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    downpayment     = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    balance         = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    payment_method  = db.Column(db.String(20))
    payment_status  = db.Column(db.String(20), default="partial")
    payment_ref     = db.Column(db.String(120))
    payment_number  = db.Column(db.String(30))
    payment_screenshot_url = db.Column(db.String(512))

    special_request = db.Column(db.Text)
    status          = db.Column(db.String(20), default="pending")
    created_at      = db.Column(db.DateTime, default=_now)
    updated_at      = db.Column(db.DateTime, default=_now, onupdate=_now)

    payments = db.relationship("Payment", backref="booking", lazy=True,
                                cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":               self.id,
            "reference_no":     self.reference_no,
            "guest":            self.guest.to_dict() if self.guest else None,
            "package":          self.package.to_dict() if self.package else None,
            "booking_type":     self.booking_type,
            "check_in_date":    self.check_in_date.isoformat(),
            "check_out_date":   self.check_out_date.isoformat(),
            "check_in_time":    self.check_in_time,
            "check_out_time":   self.check_out_time,
            "adults":           self.adults,
            "youth":            self.youth,
            "children":         self.youth,
            "total_pax":        self.adults + self.youth,
            "total_price":      float(self.total_price),
            "downpayment":      float(self.downpayment),
            "balance":          float(self.balance),
            "payment_method":   self.payment_method,
            "payment_status":   self.payment_status,
            "payment_ref":      self.payment_ref,
            "payment_number":   self.payment_number,
            "payment_screenshot_url": self.payment_screenshot_url,
            "valid_id_url":     self.guest.valid_id_url if self.guest else None,
            "special_request":  self.special_request,
            "status":           self.status,
            "created_at":       self.created_at.isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# PAYMENT
# ═══════════════════════════════════════════════════════════════════════════
class Payment(db.Model):
    __tablename__ = "payments"

    id             = db.Column(db.Integer, primary_key=True)
    booking_id     = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    amount         = db.Column(db.Numeric(12, 2), nullable=False)
    method         = db.Column(db.String(20))
    reference_no   = db.Column(db.String(120))
    screenshot_url = db.Column(db.String(512))
    note           = db.Column(db.String(255))
    paid_at        = db.Column(db.DateTime, default=_now)

    def to_dict(self):
        return {
            "id":           self.id,
            "booking_id":   self.booking_id,
            "amount":       float(self.amount),
            "method":       self.method,
            "reference_no": self.reference_no,
            "screenshot_url": self.screenshot_url,
            "note":         self.note,
            "paid_at":      self.paid_at.isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# REVIEW
# ═══════════════════════════════════════════════════════════════════════════
class Review(db.Model):
    __tablename__ = "reviews"

    id         = db.Column(db.Integer, primary_key=True)
    guest_id   = db.Column(db.Integer, db.ForeignKey("guests.id"), nullable=True)
    guest_name = db.Column(db.String(120), nullable=False)
    rating     = db.Column(db.Integer, nullable=False)
    body       = db.Column(db.Text, nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_now)

    media = db.relationship("ReviewMedia", backref="review", lazy=True,
                             cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":         self.id,
            "guest_name": self.guest_name,
            "rating":     self.rating,
            "body":       self.body,
            "is_visible": self.is_visible,
            "created_at": self.created_at.isoformat(),
            "media":      [m.to_dict() for m in self.media],
        }


class ReviewMedia(db.Model):
    __tablename__ = "review_media"

    id         = db.Column(db.Integer, primary_key=True)
    review_id  = db.Column(db.Integer, db.ForeignKey("reviews.id"), nullable=False)
    file_url   = db.Column(db.String(512), nullable=False)
    media_type = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=_now)

    def to_dict(self):
        return {
            "id":         self.id,
            "file_url":   self.file_url,
            "media_type": self.media_type,
        }
