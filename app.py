from flask import Flask
from config import Config
from models import db
from routes.auth import auth_bp, init_oauth
from routes.main import main_bp
from routes.licensing import licensing_bp
from routes.api import api_bp
from routes.ocr import ocr_bp
from routes.backup import backup_bp
from routes.files import files_bp
from werkzeug.security import generate_password_hash
from datetime import datetime
import os


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Initialize OAuth
    google = init_oauth(app)

    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Context processor
    @app.context_processor
    def inject_company_name():
        from datetime import datetime
        return dict(
            company_name=app.config['COMPANY_NAME'],
            current_year=datetime.now().year
        )

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(licensing_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(files_bp)

    # Initialize database
    with app.app_context():
        init_db(app)

    return app


def init_db(app):
    from models import User, OverlaySettings

    db.create_all()

    admin_email = app.config['ADMIN_EMAIL']
    admin_password = app.config['ADMIN_PASSWORD']

    admin = User.query.filter(User.email.ilike(admin_email)).first()
    if not admin:
        admin = User(
            email=admin_email.lower(),
            password_hash=generate_password_hash(admin_password),
            is_admin=True,
            is_active=True,
            full_name='System Administrator'
        )
        db.session.add(admin)

    for category in ('funeral', 'wedding', 'ceremony'):
        settings = OverlaySettings.query.filter_by(category=category).first()
        if not settings:
            settings = OverlaySettings(category=category, **OverlaySettings.get_defaults(category))
            db.session.add(settings)

    db.session.commit()
    print(f"Database initialized with admin user: {admin_email}")


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
