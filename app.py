"""
Flask OBS Overlay - Optimized for Shared Hosting
Single Display Route + WebSocket Updates + Google OAuth
Minimal Process Usage
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
load_dotenv()

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'zearom-overlay-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "instance", "overlays.db")}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 1,
    'pool_recycle': 280,
    'pool_pre_ping': True,
    'max_overflow': 0,
    'connect_args': {'check_same_thread': False, 'timeout': 20}
}
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['COMPANY_NAME'] = os.environ.get('COMPANY_NAME', 'Zearom')

# Google OAuth (optional)
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# MINIMAL SocketIO config for shared hosting
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False, ping_timeout=60, ping_interval=25)

# Optional OAuth (only if credentials provided)
google = None
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
        logger.info("Google OAuth configured successfully")
except Exception as e:
    logger.warning(f"OAuth not configured: {e}")
    google = None

# Helper functions
def settings_to_dict(s):
    """Convert OverlaySettings object to dictionary"""
    return {
        'main_text': s.main_text,
        'secondary_text': s.secondary_text,
        'ticker_text': s.ticker_text,
        'company_name': s.company_name,
        'company_logo': s.company_logo,
        'category_image': s.category_image,
        'show_category_image': s.show_category_image,
        'bg_color': s.bg_color,
        'accent_color': s.accent_color,
        'text_color': s.text_color,
        'main_font_size': s.main_font_size,
        'secondary_font_size': s.secondary_font_size,
        'ticker_font_size': s.ticker_font_size,
        'border_radius': s.border_radius,
        'font_family': s.font_family,
        'ticker_speed': s.ticker_speed,
        'logo_size': s.logo_size,
        'show_decorative_elements': s.show_decorative_elements,
        'opacity': s.opacity,
        'is_visible': s.is_visible,
        'is_active': s.is_active,
        'entrance_animation': s.entrance_animation,
        'entrance_duration': s.entrance_duration,
        'entrance_delay': s.entrance_delay,
        'text_animation': s.text_animation,
        'text_animation_speed': s.text_animation_speed,
        'image_animation': s.image_animation,
        'image_animation_delay': s.image_animation_delay,
        'logo_animation': s.logo_animation,
        'logo_animation_delay': s.logo_animation_delay,
        'ticker_entrance': s.ticker_entrance,
        'ticker_entrance_delay': s.ticker_entrance_delay,
        'category': s.category
    }

@app.context_processor
def inject_globals():
    """Inject global variables and functions into all templates"""
    return dict(
        company_name=app.config['COMPANY_NAME'],
        settings_to_dict=settings_to_dict,
        google_oauth_enabled=(google is not None)
    )

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200))
    google_id = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    full_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class OverlaySettings(db.Model):
    __tablename__ = 'overlay_settings'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, unique=True, index=True)
    main_text = db.Column(db.String(200))
    secondary_text = db.Column(db.String(200))
    ticker_text = db.Column(db.String(500))
    company_name = db.Column(db.String(100))
    company_logo = db.Column(db.String(200))
    category_image = db.Column(db.String(200))
    show_category_image = db.Column(db.Boolean, default=True)
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
    show_decorative_elements = db.Column(db.Boolean, default=True)
    opacity = db.Column(db.Float, default=0.9)
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
    is_visible = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

# Decorators
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        try:
            user = db.session.get(User, session['user_id'])
            if not user or not user.is_active:
                session.clear()
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
                return redirect(url_for('control'))
        except:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_active_category():
    active = db.session.query(OverlaySettings).filter_by(is_active=True).first()
    return active.category if active else 'funeral'

def set_active_category(category):
    try:
        db.session.query(OverlaySettings).update({'is_active': False})
        settings = db.session.query(OverlaySettings).filter_by(category=category).first()
        if settings:
            settings.is_active = True
            db.session.commit()
            return True
    except:
        db.session.rollback()
    return False

# Initialize DB
def init_db():
    with app.app_context():
        try:
            db.create_all()
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@zearom.com').lower()
            admin = db.session.query(User).filter(User.email.ilike(admin_email)).first()
            if not admin:
                admin = User(email=admin_email, password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'Success@Zearom')), is_admin=True, is_active=True, full_name='System Administrator')
                db.session.add(admin)

            categories = {
                'funeral': {'main_text': 'In Loving Memory', 'secondary_text': 'Celebrating a Life Well Lived', 'ticker_text': 'We gather today to honor and remember.', 'company_name': f'{app.config["COMPANY_NAME"]} Funeral Services', 'bg_color': '#1a1a1a', 'accent_color': '#8B7355', 'text_color': '#E8E8E8', 'is_active': True},
                'wedding': {'main_text': 'Together Forever', 'secondary_text': 'Celebrating Love & Unity', 'ticker_text': 'Join us as we celebrate this beautiful union.', 'company_name': f'{app.config["COMPANY_NAME"]} Wedding Services', 'bg_color': '#FFE4E1', 'accent_color': '#FF1493', 'text_color': '#8B008B', 'is_active': False},
                'ceremony': {'main_text': 'Special Ceremony', 'secondary_text': 'A Moment to Remember', 'ticker_text': 'Welcome to this special occasion.', 'company_name': f'{app.config["COMPANY_NAME"]} Event Services', 'bg_color': '#000080', 'accent_color': '#FFD700', 'text_color': '#FFFFFF', 'is_active': False}
            }

            for cat, defaults in categories.items():
                settings = db.session.query(OverlaySettings).filter_by(category=cat).first()
                if not settings:
                    settings = OverlaySettings(category=cat, is_visible=False, **defaults)
                    db.session.add(settings)
            db.session.commit()
        except Exception as e:
            logger.error(f"DB init error: {e}")
            db.session.rollback()

# Routes
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
        flash('Google login not configured.', 'error')
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
                    user.full_name = user_info.get('name', user.full_name)
                    db.session.commit()

                session.clear()
                session['user_id'] = user.id
                session['user_email'] = user.email
                session['is_admin'] = user.is_admin
                session.permanent = True
                flash('Login successful!', 'success')
                return redirect(url_for('control'))

            flash('Email not authorized. Please contact administrator.', 'error')
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
        active_category = get_active_category()
        return render_template('control.html', settings=settings, categories=categories, current_user=current_user, active_category=active_category)
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
        new_user = User(email=email, password_hash=generate_password_hash(password), full_name=full_name, is_admin=is_admin, is_active=True)
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
        user.updated_at = datetime.now(timezone.utc)
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
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f'User {"activated" if user.is_active else "deactivated"}!', 'success')
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
    try:
        active_category = get_active_category()
        settings = db.session.query(OverlaySettings).filter_by(category=active_category).first()
        if not settings:
            settings = OverlaySettings(category=active_category)
            db.session.add(settings)
            db.session.commit()
        return render_template('display_unified.html', settings=settings)
    except Exception as e:
        logger.error(f"Display error: {e}")
        return "Display error", 500

# API Endpoints
@app.route('/api/settings/<category>', methods=['POST'])
@login_required
def update_settings(category):
    try:
        settings = db.session.query(OverlaySettings).filter_by(category=category).first()
        if not settings:
            settings = OverlaySettings(category=category)
            db.session.add(settings)
        data = request.form
        for field in ['main_text', 'secondary_text', 'ticker_text', 'company_name', 'bg_color', 'accent_color', 'text_color', 'font_family']:
            if field in data:
                setattr(settings, field, data[field])
        for field in ['main_font_size', 'secondary_font_size', 'ticker_font_size', 'border_radius', 'ticker_speed', 'logo_size']:
            if field in data:
                try:
                    setattr(settings, field, int(data[field]))
                except:
                    pass
        for field in ['entrance_duration', 'entrance_delay', 'text_animation_speed', 'image_animation_delay', 'logo_animation_delay', 'ticker_entrance_delay', 'opacity']:
            if field in data:
                try:
                    setattr(settings, field, float(data[field]))
                except:
                    pass
        for field in ['entrance_animation', 'text_animation', 'image_animation', 'logo_animation', 'ticker_entrance']:
            if field in data:
                setattr(settings, field, data[field])
        if 'show_category_image' in data:
            settings.show_category_image = data['show_category_image'] == 'true'
        if 'show_decorative_elements' in data:
            settings.show_decorative_elements = data['show_decorative_elements'] == 'true'
        settings.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        if settings.is_active:
            socketio.emit('settings_update', {'settings': settings_to_dict(settings)})
        return jsonify({'success': True, 'settings': settings_to_dict(settings)})
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
        settings.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        if settings.is_active:
            socketio.emit('image_update', {'reload': True})
        return jsonify({'success': True, 'filename': relative_path, 'url': url_for('static', filename=relative_path)})
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
        settings.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        if settings.is_active:
            socketio.emit('visibility_update', {'visible': settings.is_visible})
        return jsonify({'success': True, 'visible': settings.is_visible})
    except Exception as e:
        logger.error(f"Visibility error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/set-active/<category>', methods=['POST'])
@login_required
def set_active(category):
    try:
        if set_active_category(category):
            settings = db.session.query(OverlaySettings).filter_by(category=category).first()
            socketio.emit('category_switch', {'category': category, 'settings': settings_to_dict(settings)})
            return jsonify({'success': True, 'active_category': category})
        return jsonify({'error': 'Failed'}), 500
    except Exception as e:
        logger.error(f"Set active error: {e}")
        return jsonify({'error': str(e)}), 500

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    pass

@socketio.on('request_active_settings')
def handle_request():
    try:
        active = get_active_category()
        settings = db.session.query(OverlaySettings).filter_by(category=active).first()
        if settings:
            emit('active_settings', {'settings': settings_to_dict(settings)})
    except Exception as e:
        logger.error(f"Request settings error: {e}")

# Error Handlers
@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('login')), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    db.session.rollback()
    return "Internal error", 500

# Health Check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()})

try:
    init_db()
except:
    pass

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)