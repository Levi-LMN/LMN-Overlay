"""
Flask OBS Overlay SaaS Application - Updated with Template Switching
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
import sqlite3
import os
import json
import secrets
import requests
from base64 import b64encode

# Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')
app.config['MPESA_CONSUMER_KEY'] = os.environ.get('MPESA_CONSUMER_KEY', '')
app.config['MPESA_CONSUMER_SECRET'] = os.environ.get('MPESA_CONSUMER_SECRET', '')
app.config['MPESA_SHORTCODE'] = os.environ.get('MPESA_SHORTCODE', '')
app.config['MPESA_PASSKEY'] = os.environ.get('MPESA_PASSKEY', '')
app.config['MPESA_ENVIRONMENT'] = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')

# Initialize extensions
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'logos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)

# Database setup
DATABASE = 'overlays.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            name TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            google_id TEXT UNIQUE,
            logo_path TEXT,
            company_name TEXT,
            company_phone TEXT,
            company_tagline TEXT,
            show_company_info BOOLEAN DEFAULT 1,
            subscription_status TEXT DEFAULT 'trial',
            subscription_start DATE,
            subscription_end DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Overlays table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS overlays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            overlay_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            template_version TEXT NOT NULL,
            name TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Overlay data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS overlay_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            overlay_id TEXT NOT NULL,
            data_key TEXT NOT NULL,
            data_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (overlay_id) REFERENCES overlays (overlay_id),
            UNIQUE(overlay_id, data_key)
        )
    ''')

    # Payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            phone_number TEXT NOT NULL,
            mpesa_receipt TEXT,
            status TEXT DEFAULT 'pending',
            plan_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create admin user if none exists
    cursor.execute('SELECT COUNT(*) as count FROM users')
    if cursor.fetchone()['count'] == 0:
        admin_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (email, password_hash, name, is_admin, subscription_status, subscription_end,
                             company_name, company_phone, company_tagline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('admin@overlays.com', admin_password, 'Admin User', 1, 'active',
              (datetime.now() + timedelta(days=36500)).date(),
              'WAMONIC', '+254 712 345 678', 'Memorial Services'))

    conn.commit()
    conn.close()

# User model
class User(UserMixin):
    def __init__(self, id, email, name, is_admin, active, subscription_status, subscription_end):
        self.id = id
        self.email = email
        self.name = name
        self.is_admin = is_admin
        self._active = active
        self.subscription_status = subscription_status
        self.subscription_end = subscription_end

    @property
    def is_active(self):
        return self._active

    def has_active_subscription(self):
        if self.subscription_status == 'active':
            if self.subscription_end:
                return datetime.strptime(self.subscription_end, '%Y-%m-%d').date() >= datetime.now().date()
        elif self.subscription_status == 'trial':
            return True
        return False

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        return User(
            user_data['id'],
            user_data['email'],
            user_data['name'],
            user_data['is_admin'],
            user_data['is_active'],
            user_data['subscription_status'],
            user_data['subscription_end']
        )
    return None

def subscription_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.has_active_subscription():
            flash('Your subscription has expired. Please renew to continue.', 'warning')
            return redirect(url_for('subscription'))
        return f(*args, **kwargs)
    return decorated_function

def get_available_templates():
    """Get available template versions from templates/overlays folder"""
    templates = {
        'funerals': [
            {'file': 'elegant-memorial', 'title': 'Elegant Memorial'},
            {'file': 'octagon-capsule-design', 'title': 'Octagon Capsule Design'},
            {'file': 'seamless-circle-rectangle-flow', 'title': 'Seamless Circle Rectangle'},
            {'file': 'centered-banner-with-wings', 'title': 'Centered Banner with Wings'},
            {'file': 'minimalist-centered-strip', 'title': 'Minimalist Centered Strip'}
        ],
        'weddings': [
            {'file': 'romantic-celebration', 'title': 'Romantic Celebration'},
            {'file': 'elegant-wedding', 'title': 'Elegant Wedding Banner'},
            {'file': 'modern-wedding', 'title': 'Modern Wedding Design'}
        ],
        'ceremonies': [
            {'file': 'graduation-ceremony', 'title': 'Graduation Ceremony'},
            {'file': 'awards-night', 'title': 'Awards Night'},
            {'file': 'general-ceremony', 'title': 'General Ceremony'}
        ],
        'corporate': [
            {'file': 'professional-speaker', 'title': 'Professional Speaker'},
            {'file': 'conference-banner', 'title': 'Conference Banner'},
            {'file': 'webinar-layout', 'title': 'Webinar Layout'}
        ]
    }
    return templates

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and user_data['is_active']:
            if check_password_hash(user_data['password_hash'], password):
                user = User(
                    user_data['id'],
                    user_data['email'],
                    user_data['name'],
                    user_data['is_admin'],
                    user_data['is_active'],
                    user_data['subscription_status'],
                    user_data['subscription_end']
                )
                login_user(user)
                return redirect(url_for('dashboard'))

        flash('Invalid email or password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
@subscription_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM overlays 
        WHERE user_id = ? AND is_active = 1
        ORDER BY created_at DESC
    ''', (current_user.id,))
    overlays = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', overlays=overlays)

@app.route('/create-overlay', methods=['GET', 'POST'])
@login_required
@subscription_required
def create_overlay():
    if request.method == 'POST':
        event_type = request.form.get('event_type')
        template_version = request.form.get('template_version')
        overlay_name = request.form.get('name')

        overlay_id = secrets.token_urlsafe(16)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO overlays (overlay_id, user_id, event_type, template_version, name)
            VALUES (?, ?, ?, ?, ?)
        ''', (overlay_id, current_user.id, event_type, template_version, overlay_name))
        conn.commit()
        conn.close()

        return redirect(url_for('control', overlay_id=overlay_id))

    templates = get_available_templates()
    return render_template('create_overlay.html', templates=templates)

@app.route('/control/<overlay_id>')
@login_required
@subscription_required
def control(overlay_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM overlays 
        WHERE overlay_id = ? AND user_id = ?
    ''', (overlay_id, current_user.id))
    overlay = cursor.fetchone()

    if not overlay:
        conn.close()
        flash('Overlay not found', 'error')
        return redirect(url_for('dashboard'))

    cursor.execute('''
        SELECT data_key, data_value FROM overlay_data
        WHERE overlay_id = ?
    ''', (overlay_id,))
    data_rows = cursor.fetchall()

    cursor.execute('''
        SELECT logo_path, company_name, company_phone, company_tagline, show_company_info 
        FROM users WHERE id = ?
    ''', (current_user.id,))
    user_info = cursor.fetchone()
    conn.close()

    overlay_data = {row['data_key']: row['data_value'] for row in data_rows}
    display_url = url_for('display', overlay_id=overlay_id, _external=True)
    templates = get_available_templates()

    return render_template('control.html',
                         overlay=overlay,
                         overlay_data=overlay_data,
                         display_url=display_url,
                         user_info=user_info,
                         templates=templates)

@app.route('/display/<overlay_id>')
def display(overlay_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.*, u.logo_path, u.company_name, u.company_phone, 
               u.company_tagline, u.show_company_info
        FROM overlays o
        JOIN users u ON o.user_id = u.id
        WHERE o.overlay_id = ? AND o.is_active = 1
    ''', (overlay_id,))
    overlay = cursor.fetchone()

    if not overlay:
        conn.close()
        return "Overlay not found", 404

    cursor.execute('''
        SELECT data_key, data_value FROM overlay_data
        WHERE overlay_id = ?
    ''', (overlay_id,))
    data_rows = cursor.fetchall()
    conn.close()

    overlay_data = {row['data_key']: row['data_value'] for row in data_rows}

    template_path = f"overlays/{overlay['event_type']}/{overlay['template_version']}.html"

    response = app.make_response(render_template(template_path,
                         overlay=overlay,
                         overlay_data=overlay_data,
                         overlay_id=overlay_id))

    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"

    return response

@app.route('/api/overlay/<overlay_id>', methods=['GET', 'POST'])
@login_required
def api_overlay(overlay_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM overlays 
        WHERE overlay_id = ? AND user_id = ?
    ''', (overlay_id, current_user.id))
    overlay = cursor.fetchone()

    if not overlay:
        conn.close()
        return jsonify({'error': 'Overlay not found'}), 404

    if request.method == 'POST':
        data = request.json

        for key, value in data.items():
            if isinstance(value, bool):
                value = str(value).lower()

            cursor.execute('''
                INSERT INTO overlay_data (overlay_id, data_key, data_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(overlay_id, data_key) 
                DO UPDATE SET data_value = ?, updated_at = CURRENT_TIMESTAMP
            ''', (overlay_id, key, value, value))

        conn.commit()
        conn.close()

        socketio.emit('overlay_update', data, room=overlay_id)

        return jsonify({'success': True, 'message': 'Overlay updated successfully'})

    cursor.execute('''
        SELECT data_key, data_value FROM overlay_data
        WHERE overlay_id = ?
    ''', (overlay_id,))
    data_rows = cursor.fetchall()
    conn.close()

    overlay_data = {row['data_key']: row['data_value'] for row in data_rows}
    return jsonify(overlay_data)

@app.route('/api/overlay/<overlay_id>/change-template', methods=['POST'])
@login_required
def change_template(overlay_id):
    """Change overlay template version"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM overlays 
        WHERE overlay_id = ? AND user_id = ?
    ''', (overlay_id, current_user.id))
    overlay = cursor.fetchone()

    if not overlay:
        conn.close()
        return jsonify({'error': 'Overlay not found'}), 404

    data = request.json
    new_template = data.get('template_version')

    if not new_template:
        conn.close()
        return jsonify({'error': 'Template version required'}), 400

    cursor.execute('''
        UPDATE overlays 
        SET template_version = ?
        WHERE overlay_id = ?
    ''', (new_template, overlay_id))

    conn.commit()
    conn.close()

    # Notify display to reload
    socketio.emit('template_changed', {'template': new_template}, room=overlay_id)

    return jsonify({'success': True, 'message': 'Template changed successfully'})

@app.route('/upload/<file_type>', methods=['POST'])
@login_required
def upload_file(file_type):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{filename}"

        if file_type == 'logo':
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'logos', filename)
            file.save(filepath)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET logo_path = ? WHERE id = ?
            ''', (f'uploads/logos/{filename}', current_user.id))
            conn.commit()
            conn.close()

            relative_path = f'uploads/logos/{filename}'
        else:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', filename)
            file.save(filepath)
            relative_path = f'uploads/photos/{filename}'

        return jsonify({
            'success': True,
            'path': relative_path,
            'filename': filename
        })

@app.route('/update-company-info', methods=['POST'])
@login_required
def update_company_info():
    data = request.json

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET company_name = ?, company_phone = ?, company_tagline = ?, show_company_info = ?
        WHERE id = ?
    ''', (
        data.get('company_name'),
        data.get('company_phone'),
        data.get('company_tagline'),
        data.get('show_company_info', True),
        current_user.id
    ))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/subscription')
@login_required
def subscription():
    return render_template('subscription.html')

@app.route('/profile')
@login_required
def profile():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT logo_path, company_name, company_phone, company_tagline, show_company_info 
        FROM users WHERE id = ?
    ''', (current_user.id,))
    user_info = cursor.fetchone()
    conn.close()

    return render_template('profile.html', user_info=user_info)

@app.route('/remove-logo', methods=['POST'])
@login_required
def remove_logo():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT logo_path FROM users WHERE id = ?', (current_user.id,))
    result = cursor.fetchone()

    if result and result['logo_path']:
        logo_path = os.path.join('static', result['logo_path'])
        if os.path.exists(logo_path):
            try:
                os.remove(logo_path)
            except Exception as e:
                print(f"Error deleting logo file: {e}")

    cursor.execute('UPDATE users SET logo_path = NULL WHERE id = ?', (current_user.id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    conn.close()

    return render_template('admin_users.html', users=users)

# WebSocket events
@socketio.on('join')
def on_join(data):
    overlay_id = data['overlay_id']
    join_room(overlay_id)

@socketio.on('leave')
def on_leave(data):
    overlay_id = data['overlay_id']
    leave_room(overlay_id)

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)