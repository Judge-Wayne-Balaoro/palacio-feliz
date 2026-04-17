import os
from flask import Flask, render_template, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_obj=None):
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(
        __name__,
        template_folder=os.path.join(root_dir, 'templates'),
        static_folder=os.path.join(root_dir, 'static'),
        static_url_path='/static',
    )

    if config_obj is None:
        from config import get_config
        config_obj = get_config()
    app.config.from_object(config_obj)

    for sub in ('reviews', 'valid_ids', 'payments', 'packages'):
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], sub), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Auto-create tables on startup (useful for Render deployment)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.error(f"Failed to create tables: {e}")

    from app.routes.auth import auth_bp
    from app.routes.bookings import bookings_bp
    from app.routes.packages import packages_bp
    from app.routes.reviews import reviews_bp
    from app.routes.calendar import calendar_bp
    from app.routes.payments import payments_bp
    from app.routes.guests import guests_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(bookings_bp, url_prefix='/api/bookings')
    app.register_blueprint(packages_bp, url_prefix='/api/packages')
    app.register_blueprint(reviews_bp, url_prefix='/api/reviews')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(guests_bp, url_prefix='/api/guests')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')

    # FIX #1: Serve uploaded files via /uploads/<path>
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.get('/')
    def customer_page():
        return render_template('customer.html')

    @app.get('/login')
    def login_page():
        return render_template('log_in.html')

    @app.get('/admin')
    def admin_page():
        return render_template('admin.html')

    @app.get('/home')
    def home_redirect():
        return redirect(url_for('customer_page'))

    return app
