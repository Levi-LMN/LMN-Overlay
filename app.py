"""
Flask OBS Lower-Third Overlay System with Category-Specific Designs
Each category (funeral, wedding, ceremony) has its own unique design template.
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from functools import wraps
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///overlays.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Google OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', 'your-google-client-secret')

db = SQLAlchemy(app)

# Use threading async mode (works with Python 3.13+)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200))
    google_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OverlaySettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)

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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    with app.app_context():
        db.create_all()

        admin_email = 'admin@zearom.com'
        admin = User.query.filter(User.email.ilike(admin_email)).first()
        if not admin:
            admin = User(
                email=admin_email.lower(),
                password_hash=generate_password_hash('Success@Zearom')
            )
            db.session.add(admin)

        # Create default settings with category-specific defaults
        category_defaults = {
            'funeral': {
                'main_text': 'In Loving Memory',
                'secondary_text': 'Celebrating a Life Well Lived',
                'ticker_text': 'We gather today to honor and remember.',
                'company_name': 'Zearom Funeral Services',
                'bg_color': '#1a1a1a',
                'accent_color': '#8B7355',
                'text_color': '#E8E8E8',
                'layout_style': 'elegant'
            },
            'wedding': {
                'main_text': 'Together Forever',
                'secondary_text': 'Celebrating Love & Unity',
                'ticker_text': 'Join us as we celebrate this beautiful union.',
                'company_name': 'Zearom Wedding Services',
                'bg_color': '#FFE4E1',
                'accent_color': '#FF1493',
                'text_color': '#8B008B',
                'layout_style': 'romantic'
            },
            'ceremony': {
                'main_text': 'Special Ceremony',
                'secondary_text': 'A Moment to Remember',
                'ticker_text': 'Welcome to this special occasion.',
                'company_name': 'Zearom Event Services',
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
        print("Database initialized with admin user: admin@zearom.com / Success@Zearom")

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
            return render_template('login.html', error='Email not authorized')

        if user.password_hash and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            return redirect(url_for('control'))

        return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')

    if user_info:
        email = user_info['email'].lower()
        google_id = user_info['sub']

        user = User.query.filter(User.email.ilike(email)).first()

        if not user:
            return render_template('login.html', error='Email not authorized')

        if not user.google_id:
            user.google_id = google_id
            db.session.commit()

        session['user_id'] = user.id
        session['user_email'] = user.email
        return redirect(url_for('control'))

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/control')
@login_required
def control():
    categories = ['funeral', 'wedding', 'ceremony']
    settings = {}
    for cat in categories:
        settings[cat] = OverlaySettings.query.filter_by(category=cat).first()

    return render_template('control.html', settings=settings, categories=categories)

@app.route('/display')
def display():
    category = request.args.get('category', 'funeral')
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        settings = OverlaySettings(category=category)

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

        socketio.emit('settings_update', {
            'category': category,
            'settings': settings_to_dict(settings)
        })

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

        socketio.emit('settings_update', {
            'category': category,
            'settings': settings_to_dict(settings)
        })

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

    socketio.emit('visibility_update', {
        'category': category,
        'visible': settings.is_visible
    })

    return jsonify({'success': True, 'visible': settings.is_visible})

def settings_to_dict(settings):
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