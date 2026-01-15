"""
Flask OBS Lower-Third Overlay System
Optimized for NovaHost CloudLinux Passenger - Production Ready
No .htaccess or passenger_wsgi.py changes required
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging to be less verbose in production
logging.basicConfig(
    level=logging.WARNING,  # Changed from INFO to WARNING
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Get absolute paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Essential Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'zearom-overlay-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    f'sqlite:///{os.path.join(BASE_DIR, "instance", "overlays.db")}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Critical: Optimized for shared hosting - minimal connections
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 1,  # Single connection pool
    'pool_recycle': 280,  # Recycle before 5 min timeout
    'pool_pre_ping': True,  # Check connections before use
    'max_overflow': 0,  # No overflow connections
    'connect_args': {
        'check_same_thread': False,
        'timeout': 20
    }
}

# File upload settings
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Company settings
app.config['COMPANY_NAME'] = os.environ.get('COMPANY_NAME', 'Zearom')

# Google OAuth (optional)
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')

# Create directories
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Optional OAuth (only if credentials provided)
try:
    if app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']:
        from authlib.integrations.flask_client import OAuth
        oauth = OAuth(app)
        google = oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
    else:
        google = None
except Exception as e:
    logger.warning(f"OAuth not configured: {e}")
    google = None


# Context processor
@app.context_processor
def inject_globals():
    return dict(company_name=app.config['COMPANY_NAME'])


# ==================== DATABASE MODELS ====================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200))
    google_id = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    full_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OverlaySettings(db.Model):
    __tablename__ = 'overlay_settings'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, unique=True, index=True)

    # Content
    main_text = db.Column(db.String(200))
    secondary_text = db.Column(db.String(200))
    ticker_text = db.Column(db.String(500))
    company_name = db.Column(db.String(100))
    company_logo = db.Column(db.String(200))
    category_image = db.Column(db.String(200))
    show_category_image = db.Column(db.Boolean, default=True)

    # Styling
    bg_color = db.Column(db.String(7), default='#000000')
    accent_color = db.Column(db.String(7), default='#FFD700')
    text_color = db.Column(db.String(7), default='#FFFFFF')
    main_font_size = db.Column(db.Integer, default=32)
    secondary_font_size = db.Column(db.Integer, default=24)
    ticker_font_size = db.Column(db.Integer, default=18)
    border_radius = db.Column(db.Integer, default=10)
    font_family = db.Column(db.String(100), default='Arial, sans-serif')
    ticker_speed = db.Column(db.Integer, default=50)
    logo_size = db.Column(db.Integer, default=80)

    # Layout
    layout_style = db.Column(db.String(50), default='default')
    show_decorative_elements = db.Column(db.Boolean, default=True)
    opacity = db.Column(db.Float, default=0.9)

    # Animations
    entrance_animation = db.Column(db.String(50), default='slide-left')
    entrance_duration = db.Column(db.Float, default=1.0)
    entrance_delay = db.Column(db.Float, default=0.0)
    text_animation = db.Column(db.String(50), default='none')
    text_animation_speed = db.Column(db.Float, default=0.05)
    image_animation = db.Column(db.String(50), default='fade-in')
    image_animation_delay = db.Column(db.Float, default=0.3)
    logo_animation = db.Column(db.String(50), default='scale-in')
    logo_animation_delay = db.Column(db.Float, default=0.5)
    ticker_entrance = db.Column(db.String(50), default='slide-up')
    ticker_entrance_delay = db.Column(db.Float, default=0.8)

    # Visibility
    is_visible = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== DECORATORS ====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        try:
            user = db.session.get(User, session['user_id'])
            if not user or not user.is_active:
                session.clear()
                flash('Your account is inactive.', 'error')
                return redirect(url_for('login'))
        except:
            session.clear()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        try:
            user = db.session.get(User, session['user_id'])
            if not user or not user.is_active or not user.is_admin:
                flash('Admin access required.', 'error')
                return redirect(url_for('control'))
        except:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ==================== DATABASE INITIALIZATION ====================

def init_db():
    """Initialize database with default data"""
    with app.app_context():
        try:
            db.create_all()

            # Create admin
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@zearom.com').lower()
            admin_password = os.environ.get('ADMIN_PASSWORD', 'Success@Zearom')

            admin = db.session.query(User).filter(User.email.ilike(admin_email)).first()
            if not admin:
                admin = User(
                    email=admin_email,
                    password_hash=generate_password_hash(admin_password),
                    is_admin=True,
                    is_active=True,
                    full_name='System Administrator'
                )
                db.session.add(admin)

            # Create default settings
            categories = {
                'funeral': {
                    'main_text': 'In Loving Memory',
                    'secondary_text': 'Celebrating a Life Well Lived',
                    'ticker_text': 'We gather today to honor and remember.',
                    'company_name': f'{app.config["COMPANY_NAME"]} Funeral Services',
                    'bg_color': '#1a1a1a',
                    'accent_color': '#8B7355',
                    'text_color': '#E8E8E8'
                },
                'wedding': {
                    'main_text': 'Together Forever',
                    'secondary_text': 'Celebrating Love & Unity',
                    'ticker_text': 'Join us as we celebrate this beautiful union.',
                    'company_name': f'{app.config["COMPANY_NAME"]} Wedding Services',
                    'bg_color': '#FFE4E1',
                    'accent_color': '#FF1493',
                    'text_color': '#8B008B'
                },
                'ceremony': {
                    'main_text': 'Special Ceremony',
                    'secondary_text': 'A Moment to Remember',
                    'ticker_text': 'Welcome to this special occasion.',
                    'company_name': f'{app.config["COMPANY_NAME"]} Event Services',
                    'bg_color': '#000080',
                    'accent_color': '#FFD700',
                    'text_color': '#FFFFFF'
                }
            }

            for cat, defaults in categories.items():
                settings = db.session.query(OverlaySettings).filter_by(category=cat).first()
                if not settings:
                    settings = OverlaySettings(category=cat, is_visible=False, **defaults)
                    db.session.add(settings)

            db.session.commit()

        except Exception as e:
            logger.error(f"Database init error: {e}")
            db.session.rollback()


# ==================== ROUTES ====================

@app.route('/')
def index():
    return redirect(url_for('control') if 'user_id' in session else url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password required.', 'error')
            return render_template('login.html')

        try:
            user = db.session.query(User).filter(User.email.ilike(email)).first()

            if not user:
                flash('Invalid credentials.', 'error')
                return render_template('login.html')

            if not user.is_active:
                flash('Account deactivated.', 'error')
                return render_template('login.html')

            if user.password_hash and check_password_hash(user.password_hash, password):
                session.clear()
                session['user_id'] = user.id
                session['user_email'] = user.email
                session['is_admin'] = user.is_admin
                session.permanent = True
                flash('Login successful!', 'success')
                return redirect(url_for('control'))

            flash('Invalid credentials.', 'error')

        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login error occurred.', 'error')

    return render_template('login.html')


@app.route('/login/google')
def google_login():
    if not google:
        flash('Google login not configured.', 'error')
        return redirect(url_for('login'))
    return google.authorize_redirect(url_for('google_callback', _external=True))


@app.route('/login/google/callback')
def google_callback():
    if not google:
        return redirect(url_for('login'))

    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if user_info:
            email = user_info['email'].lower()
            user = db.session.query(User).filter(User.email.ilike(email)).first()

            if user and user.is_active:
                if not user.google_id:
                    user.google_id = user_info['sub']
                    db.session.commit()

                session.clear()
                session['user_id'] = user.id
                session['user_email'] = user.email
                session['is_admin'] = user.is_admin
                session.permanent = True
                return redirect(url_for('control'))

            flash('Email not authorized.', 'error')
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        flash('Authentication failed.', 'error')

    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


@app.route('/control')
@login_required
def control():
    categories = ['funeral', 'wedding', 'ceremony']
    settings = {}

    try:
        for cat in categories:
            settings[cat] = db.session.query(OverlaySettings).filter_by(category=cat).first()
            if not settings[cat]:
                settings[cat] = OverlaySettings(category=cat)
                db.session.add(settings[cat])

        db.session.commit()
        current_user = db.session.get(User, session['user_id'])
        return render_template('control.html', settings=settings, categories=categories, current_user=current_user)

    except Exception as e:
        logger.error(f"Control error: {e}")
        flash('Error loading control panel.', 'error')
        return redirect(url_for('login'))


@app.route('/users')
@admin_required
def users():
    try:
        all_users = db.session.query(User).order_by(User.created_at.desc()).all()
        current_user = db.session.get(User, session['user_id'])
        return render_template('users.html', users=all_users, current_user=current_user)
    except Exception as e:
        logger.error(f"Users error: {e}")
        return redirect(url_for('control'))


@app.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    try:
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        is_admin = request.form.get('is_admin') == 'on'

        if not email or not password:
            flash('Email and password required.', 'error')
            return redirect(url_for('users'))

        if db.session.query(User).filter(User.email.ilike(email)).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('users'))

        new_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            is_admin=is_admin,
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f'User {email} created!', 'success')

    except Exception as e:
        logger.error(f"Create user error: {e}")
        db.session.rollback()
        flash('Error creating user.', 'error')

    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('users'))

        protected = os.environ.get('ADMIN_EMAIL', 'admin@zearom.com').lower()
        if user.email.lower() == protected:
            flash('Cannot modify super admin.', 'error')
            return redirect(url_for('users'))

        email = request.form.get('email', '').lower().strip()
        full_name = request.form.get('full_name', '').strip()
        is_admin = request.form.get('is_admin') == 'on'
        password = request.form.get('password', '').strip()

        if db.session.query(User).filter(User.email.ilike(email), User.id != user_id).first():
            flash('Email already in use.', 'error')
            return redirect(url_for('users'))

        user.email = email
        user.full_name = full_name
        user.is_admin = is_admin
        user.updated_at = datetime.utcnow()

        if password:
            user.password_hash = generate_password_hash(password)

        db.session.commit()
        flash(f'User {email} updated!', 'success')

    except Exception as e:
        logger.error(f"Edit user error: {e}")
        db.session.rollback()
        flash('Error updating user.', 'error')

    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            return redirect(url_for('users'))

        if user.id == session['user_id']:
            flash('Cannot deactivate yourself.', 'error')
            return redirect(url_for('users'))

        user.is_active = not user.is_active
        user.updated_at = datetime.utcnow()
        db.session.commit()

        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User {status}!', 'success')

    except Exception as e:
        logger.error(f"Toggle status error: {e}")
        db.session.rollback()

    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            return redirect(url_for('users'))

        if user.id == session['user_id']:
            flash('Cannot delete yourself.', 'error')
            return redirect(url_for('users'))

        email = user.email
        db.session.delete(user)
        db.session.commit()
        flash(f'User {email} deleted!', 'success')

    except Exception as e:
        logger.error(f"Delete user error: {e}")
        db.session.rollback()
        flash('Error deleting user.', 'error')

    return redirect(url_for('users'))


@app.route('/display')
def display():
    category = request.args.get('category', 'funeral')

    try:
        settings = db.session.query(OverlaySettings).filter_by(category=category).first()

        if not settings:
            settings = OverlaySettings(category=category)
            db.session.add(settings)
            db.session.commit()

        templates = {
            'funeral': 'display_funeral.html',
            'wedding': 'display_wedding.html',
            'ceremony': 'display_ceremony.html'
        }

        return render_template(templates.get(category, 'display_funeral.html'),
                             settings=settings, category=category)

    except Exception as e:
        logger.error(f"Display error: {e}")
        return "Display error", 500


@app.route('/api/settings/<category>', methods=['GET', 'POST'])
@login_required
def manage_settings(category):
    try:
        settings = db.session.query(OverlaySettings).filter_by(category=category).first()

        if not settings:
            settings = OverlaySettings(category=category)
            db.session.add(settings)

        if request.method == 'POST':
            data = request.form

            # Text fields
            for field in ['main_text', 'secondary_text', 'ticker_text', 'company_name',
                         'bg_color', 'accent_color', 'text_color', 'font_family', 'layout_style']:
                if field in data:
                    setattr(settings, field, data[field])

            # Integer fields
            for field in ['main_font_size', 'secondary_font_size', 'ticker_font_size',
                         'border_radius', 'ticker_speed', 'logo_size']:
                if field in data:
                    try:
                        setattr(settings, field, int(data[field]))
                    except:
                        pass

            # Float fields
            for field in ['entrance_duration', 'entrance_delay', 'text_animation_speed',
                         'image_animation_delay', 'logo_animation_delay',
                         'ticker_entrance_delay', 'opacity']:
                if field in data:
                    try:
                        setattr(settings, field, float(data[field]))
                    except:
                        pass

            # Animation fields
            for field in ['entrance_animation', 'text_animation', 'image_animation',
                         'logo_animation', 'ticker_entrance']:
                if field in data:
                    setattr(settings, field, data[field])

            # Boolean fields
            if 'show_category_image' in data:
                settings.show_category_image = data['show_category_image'] == 'true'
            if 'show_decorative_elements' in data:
                settings.show_decorative_elements = data['show_decorative_elements'] == 'true'

            settings.updated_at = datetime.utcnow()
            db.session.commit()

            return jsonify({'success': True, 'settings': settings_to_dict(settings)})

        return jsonify({'settings': settings_to_dict(settings)})

    except Exception as e:
        logger.error(f"Settings error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload/<category>/<file_type>', methods=['POST'])
@login_required
def upload_file(category, file_type):
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{category}_{file_type}_{timestamp}_{filename}"

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        file.save(filepath)

        settings = db.session.query(OverlaySettings).filter_by(category=category).first()
        if not settings:
            settings = OverlaySettings(category=category)
            db.session.add(settings)

        relative_path = f"uploads/{filename}"

        if file_type == 'logo':
            settings.company_logo = relative_path
        elif file_type == 'image':
            settings.category_image = relative_path

        settings.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'filename': relative_path,
            'url': url_for('static', filename=relative_path)
        })

    except Exception as e:
        logger.error(f"Upload error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/visibility/<category>', methods=['POST'])
@login_required
def toggle_visibility(category):
    try:
        data = request.get_json()
        settings = db.session.query(OverlaySettings).filter_by(category=category).first()

        if not settings:
            return jsonify({'error': 'Not found'}), 404

        settings.is_visible = data.get('visible', True)
        settings.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'visible': settings.is_visible})

    except Exception as e:
        logger.error(f"Visibility error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== HELPER FUNCTIONS ====================

def settings_to_dict(settings):
    """Convert settings to dictionary"""
    return {
        'main_text': settings.main_text,
        'secondary_text': settings.secondary_text,
        'ticker_text': settings.ticker_text,
        'company_name': settings.company_name,
        'company_logo': settings.company_logo,
        'category_image': settings.category_image,
        'show_category_image': settings.show_category_image,
        'bg_color': settings.bg_color,
        'accent_color': settings.accent_color,
        'text_color': settings.text_color,
        'main_font_size': settings.main_font_size,
        'secondary_font_size': settings.secondary_font_size,
        'ticker_font_size': settings.ticker_font_size,
        'border_radius': settings.border_radius,
        'font_family': settings.font_family,
        'ticker_speed': settings.ticker_speed,
        'logo_size': settings.logo_size,
        'layout_style': settings.layout_style,
        'show_decorative_elements': settings.show_decorative_elements,
        'opacity': settings.opacity,
        'is_visible': settings.is_visible,
        'entrance_animation': settings.entrance_animation,
        'entrance_duration': settings.entrance_duration,
        'entrance_delay': settings.entrance_delay,
        'text_animation': settings.text_animation,
        'text_animation_speed': settings.text_animation_speed,
        'image_animation': settings.image_animation,
        'image_animation_delay': settings.image_animation_delay,
        'logo_animation': settings.logo_animation,
        'logo_animation_delay': settings.logo_animation_delay,
        'ticker_entrance': settings.ticker_entrance,
        'ticker_entrance_delay': settings.ticker_entrance_delay
    }


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('login')), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    db.session.rollback()
    return "Internal error", 500


# ==================== HEALTH CHECK ====================

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# ==================== INITIALIZE DATABASE ====================

# Auto-initialize on first import (Passenger compatible)
try:
    init_db()
except:
    pass  # Silent fail - will retry on first request


# ==================== APPLICATION ENTRY POINT ====================

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=5000)