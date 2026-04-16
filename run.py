"""
run.py  –  Application entry point
"""
from app import create_app, db
from app.models import AdminUser, Package, Guest, Booking, Payment, Review, ReviewMedia

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return dict(
        db=db,
        AdminUser=AdminUser,
        Package=Package,
        Guest=Guest,
        Booking=Booking,
        Payment=Payment,
        Review=Review,
        ReviewMedia=ReviewMedia,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
