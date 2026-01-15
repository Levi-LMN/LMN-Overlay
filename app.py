"""
Flask OBS Lower-Third Overlay System with User Management
Optimized for PythonAnywhere deployment
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from functools import wraps
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration from environment variables
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///overlays.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Company Configuration
app.config['COMPANY_NAME'] = os.environ.get('COMPANY_NAME', 'Zearom')

# Google OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', 'your-google-client-secret')

db = SQLAlchemy(app)

# Use threading async mode with optimizations for PythonAnywhere
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25
)

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Context processor to make company_name available in all templates
@app.context_processor
def inject_company_name():
    return dict(company_name=app.config['COMPANY_NAME'])

# Database Models
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

    def __repr__(self):
        return f'<User {self.email}>'

class OverlaySettings(db.Model):
    __tablename__ = 'overlay_settings'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True)

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

    # Layout specific settings
    layout_style = db.Column(db.String(50), default='default')
    show_decorative_elements = db.Column(db.Boolean, default=True)
    opacity = db.Column(db.Float, default=0.9)

    # Animation Settings
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

    def __repr__(self):
        return f'<OverlaySettings {self.category}>'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            flash('Your account has been deactivated.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            flash('Your account has been deactivated.', 'error')
            return redirect(url_for('login'))
        if not user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('control'))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    with app.app_context():
        db.create_all()

        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@zearom.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Success@Zearom')

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

        # Create default settings with category-specific defaults
        category_defaults = {
            'funeral': {
                'main_text': 'In Loving Memory',
                'secondary_text': 'Celebrating a Life Well Lived',
                'ticker_text': 'We gather today to honor and remember.',
                'company_name': f'{app.config["COMPANY_NAME"]} Funeral Services',
                'bg_color': '#1a1a1a',
                'accent_color': '#8B7355',
                'text_color': '#E8E8E8',
                'layout_style': 'elegant'
            },
            'wedding': {
                'main_text': 'Together Forever',
                'secondary_text': 'Celebrating Love & Unity',
                'ticker_text': 'Join us as we celebrate this beautiful union.',
                'company_name': f'{app.config["COMPANY_NAME"]} Wedding Services',
                'bg_color': '#FFE4E1',
                'accent_color': '#FF1493',
                'text_color': '#8B008B',
                'layout_style': 'romantic'
            },
            'ceremony': {
                'main_text': 'Special Ceremony',
                'secondary_text': 'A Moment to Remember',
                'ticker_text': 'Welcome to this special occasion.',
                'company_name': f'{app.config["COMPANY_NAME"]} Event Services',
                'bg_color': '#000080',
                'accent_color': '#FFD700',
                'text_color': '#FFFFFF',
                'layout_style': 'formal'
            }
        }

        for category, defaults in category_defaults.items():
            settings = OverlaySettings.query.filter_by(category=category).first()
            if not settings:
                settings = OverlaySettings(
                    category=category,
                    is_visible=False,
                    **defaults
                )
                db.session.add(settings)

        db.session.commit()
        print(f"Database initialized with admin user: {admin_email}")

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('control'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        email_normalized = email.lower() if email else ""
        user = User.query.filter(User.email.ilike(email_normalized)).first()

        if not user:
            flash('Email not authorized', 'error')
            return render_template('login.html')

        if not user.is_active:
            flash('Your account has been deactivated. Please contact an administrator.', 'error')
            return render_template('login.html')

        if user.password_hash and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('control'))

        flash('Invalid credentials', 'error')
        return render_template('login.html')

    return render_template('login.html')

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if user_info:
            email = user_info['email'].lower()
            google_id = user_info['sub']

            user = User.query.filter(User.email.ilike(email)).first()

            if not user:
                flash('Email not authorized', 'error')
                return redirect(url_for('login'))

            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
                return redirect(url_for('login'))

            if not user.google_id:
                user.google_id = google_id
                db.session.commit()

            session['user_id'] = user.id
            session['user_email'] = user.email
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('control'))
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash('Google authentication failed', 'error')
        return redirect(url_for('login'))

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/control')
@login_required
def control():
    categories = ['funeral', 'wedding', 'ceremony']
    settings = {}
    for cat in categories:
        settings[cat] = OverlaySettings.query.filter_by(category=cat).first()
        if not settings[cat]:
            settings[cat] = OverlaySettings(category=cat)
            db.session.add(settings[cat])

    db.session.commit()

    current_user = User.query.get(session['user_id'])
    return render_template('control.html', settings=settings, categories=categories, current_user=current_user)

# User Management Routes
@app.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    current_user = User.query.get(session['user_id'])
    return render_template('users.html', users=all_users, current_user=current_user)

@app.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    data = request.form
    email = data.get('email', '').lower().strip()
    password = data.get('password')
    full_name = data.get('full_name', '').strip()
    is_admin = data.get('is_admin') == 'on'

    if not email or not password:
        flash('Email and password are required.', 'error')
        return redirect(url_for('users'))

    existing_user = User.query.filter(User.email.ilike(email)).first()
    if existing_user:
        flash('A user with this email already exists.', 'error')
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

    flash(f'User {email} created successfully!', 'success')
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.form

    # Prevent editing the last admin
    if user.is_admin and data.get('is_admin') != 'on':
        admin_count = User.query.filter_by(is_admin=True, is_active=True).count()
        if admin_count <= 1:
            flash('Cannot remove admin privileges from the last active administrator.', 'error')
            return redirect(url_for('users'))

    email = data.get('email', '').lower().strip()
    full_name = data.get('full_name', '').strip()
    is_admin = data.get('is_admin') == 'on'
    password = data.get('password', '').strip()

    if not email:
        flash('Email is required.', 'error')
        return redirect(url_for('users'))

    # Check if email is taken by another user
    existing_user = User.query.filter(User.email.ilike(email), User.id != user_id).first()
    if existing_user:
        flash('Email already in use by another user.', 'error')
        return redirect(url_for('users'))

    user.email = email
    user.full_name = full_name
    user.is_admin = is_admin
    user.updated_at = datetime.utcnow()

    # Only update password if provided
    if password:
        user.password_hash = generate_password_hash(password)

    db.session.commit()
    flash(f'User {email} updated successfully!', 'success')
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)

    # Prevent deactivating yourself
    if user.id == session['user_id']:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('users'))

    # Prevent deactivating the last admin
    if user.is_admin and user.is_active:
        admin_count = User.query.filter_by(is_admin=True, is_active=True).count()
        if admin_count <= 1:
            flash('Cannot deactivate the last active administrator.', 'error')
            return redirect(url_for('users'))

    user.is_active = not user.is_active
    user.updated_at = datetime.utcnow()
    db.session.commit()

    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.email} {status} successfully!', 'success')
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Prevent deleting yourself
    if user.id == session['user_id']:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('users'))

    # Prevent deleting the last admin
    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash('Cannot delete the last administrator.', 'error')
            return redirect(url_for('users'))

    email = user.email
    db.session.delete(user)
    db.session.commit()

    flash(f'User {email} deleted successfully!', 'success')
    return redirect(url_for('users'))

@app.route('/display')
def display():
    category = request.args.get('category', 'funeral')
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        settings = OverlaySettings(category=category)
        db.session.add(settings)
        db.session.commit()

    # Route to category-specific template
    template_map = {
        'funeral': 'display_funeral.html',
        'wedding': 'display_wedding.html',
        'ceremony': 'display_ceremony.html'
    }

    template = template_map.get(category, 'display_funeral.html')
    return render_template(template, settings=settings, category=category)

@app.route('/api/settings/<category>', methods=['GET', 'POST'])
@login_required
def manage_settings(category):
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        settings = OverlaySettings(category=category)
        db.session.add(settings)

    if request.method == 'POST':
        data = request.form

        # Update all fields
        fields = [
            'main_text', 'secondary_text', 'ticker_text', 'company_name',
            'bg_color', 'accent_color', 'text_color', 'font_family', 'layout_style'
        ]

        for field in fields:
            if field in data:
                setattr(settings, field, data[field])

        # Integer fields
        int_fields = [
            'main_font_size', 'secondary_font_size', 'ticker_font_size',
            'border_radius', 'ticker_speed', 'logo_size'
        ]

        for field in int_fields:
            if field in data:
                setattr(settings, field, int(data[field]))

        # Float fields
        float_fields = [
            'entrance_duration', 'entrance_delay', 'text_animation_speed',
            'image_animation_delay', 'logo_animation_delay', 'ticker_entrance_delay', 'opacity'
        ]

        for field in float_fields:
            if field in data:
                setattr(settings, field, float(data[field]))

        # Animation fields
        animation_fields = [
            'entrance_animation', 'text_animation', 'image_animation',
            'logo_animation', 'ticker_entrance'
        ]

        for field in animation_fields:
            if field in data:
                setattr(settings, field, data[field])

        # Boolean fields
        if 'show_category_image' in data:
            settings.show_category_image = data['show_category_image'] == 'true'
        if 'show_decorative_elements' in data:
            settings.show_decorative_elements = data['show_decorative_elements'] == 'true'

        db.session.commit()

        # Emit socket event
        try:
            socketio.emit('settings_update', {
                'category': category,
                'settings': settings_to_dict(settings)
            })
        except Exception as e:
            print(f"Socket emit error: {e}")

        return jsonify({'success': True, 'settings': settings_to_dict(settings)})

    return jsonify({'settings': settings_to_dict(settings)})

@app.route('/api/upload/<category>/<file_type>', methods=['POST'])
@login_required
def upload_file(category, file_type):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{category}_{file_type}_{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        settings = OverlaySettings.query.filter_by(category=category).first()
        if not settings:
            settings = OverlaySettings(category=category)
            db.session.add(settings)

        relative_path = f"uploads/{filename}"

        if file_type == 'logo':
            settings.company_logo = relative_path
        elif file_type == 'image':
            settings.category_image = relative_path

        db.session.commit()

        # Emit socket event
        try:
            socketio.emit('settings_update', {
                'category': category,
                'settings': settings_to_dict(settings)
            })
        except Exception as e:
            print(f"Socket emit error: {e}")

        return jsonify({'success': True, 'filename': relative_path})

    return jsonify({'error': 'Upload failed'}), 500

@app.route('/api/visibility/<category>', methods=['POST'])
@login_required
def toggle_visibility(category):
    data = request.get_json()
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        return jsonify({'error': 'Settings not found'}), 404

    settings.is_visible = data.get('visible', True)
    db.session.commit()

    # Emit socket event
    try:
        socketio.emit('visibility_update', {
            'category': category,
            'visible': settings.is_visible
        })
    except Exception as e:
        print(f"Socket emit error: {e}")

    return jsonify({'success': True, 'visible': settings.is_visible})

def settings_to_dict(settings):
    """Convert settings object to dictionary"""
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

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)