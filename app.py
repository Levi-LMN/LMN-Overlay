"""
Flask OBS Overlay System with M-Pesa Licensing
Complete version with all functionality
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Blueprint
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from functools import wraps
import os
import json
import requests
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuration
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
app.config['COMPANY_NAME'] = os.environ.get('COMPANY_NAME', 'Zearom')
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', 'your-google-client-secret')

# M-Pesa Configuration
app.config['MPESA_CONSUMER_KEY'] = os.environ.get('MPESA_CONSUMER_KEY')
app.config['MPESA_CONSUMER_SECRET'] = os.environ.get('MPESA_CONSUMER_SECRET')
app.config['MPESA_SHORTCODE'] = os.environ.get('MPESA_SHORTCODE')
app.config['MPESA_PASSKEY'] = os.environ.get('MPESA_PASSKEY')
app.config['MPESA_ENVIRONMENT'] = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')

db = SQLAlchemy(app)
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


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

    # License relationship
    license = db.relationship('License', backref='user', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'


class License(db.Model):
    __tablename__ = 'licenses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    subscription_type = db.Column(db.String(50), default='trial')
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    auto_renew = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payments = db.relationship('Payment', backref='license', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<License {self.user_id} - {self.subscription_type}>'

    def is_valid(self):
        return self.is_active and self.end_date and self.end_date > datetime.utcnow()

    def days_remaining(self):
        if not self.end_date:
            return 0
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey('licenses.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    phone_number = db.Column(db.String(20))
    mpesa_receipt = db.Column(db.String(100))
    checkout_request_id = db.Column(db.String(100))
    status = db.Column(db.String(50), default='pending')
    subscription_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Payment {self.id} - {self.status}>'


class OverlaySettings(db.Model):
    __tablename__ = 'overlay_settings'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True)

    # Content
    main_text = db.Column(db.String(200))
    secondary_text = db.Column(db.String(200))
    secondary_phrases = db.Column(db.Text)
    ticker_text = db.Column(db.String(500))
    company_name = db.Column(db.String(100))
    company_logo = db.Column(db.String(200))
    category_image = db.Column(db.String(200))
    show_category_image = db.Column(db.Boolean, default=True)
    show_company_logo = db.Column(db.Boolean, default=True)

    # Secondary Text Rotation Settings
    secondary_rotation_enabled = db.Column(db.Boolean, default=False)
    secondary_display_duration = db.Column(db.Float, default=3.0)
    secondary_transition_type = db.Column(db.String(50), default='fade')
    secondary_transition_duration = db.Column(db.Float, default=0.5)

    # Position & Size Controls
    vertical_position = db.Column(db.String(20), default='bottom')
    horizontal_position = db.Column(db.String(20), default='left')
    custom_top = db.Column(db.Integer, default=0)
    custom_bottom = db.Column(db.Integer, default=0)
    custom_left = db.Column(db.Integer, default=0)
    custom_right = db.Column(db.Integer, default=0)

    container_width = db.Column(db.String(20), default='auto')
    custom_width = db.Column(db.Integer, default=800)
    container_max_width = db.Column(db.Integer, default=1200)
    container_min_width = db.Column(db.Integer, default=600)

    container_height = db.Column(db.String(20), default='auto')
    custom_height = db.Column(db.Integer, default=200)
    container_padding = db.Column(db.Integer, default=25)

    # Font Scaling Control
    text_scale_mode = db.Column(db.String(20), default='responsive')
    text_line_height = db.Column(db.Float, default=1.2)
    text_max_lines = db.Column(db.Integer, default=2)
    enable_text_truncation = db.Column(db.Boolean, default=True)

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

    def get_secondary_phrases_list(self):
        if self.secondary_phrases:
            try:
                return json.loads(self.secondary_phrases)
            except:
                return []
        return []

    def set_secondary_phrases_list(self, phrases_list):
        self.secondary_phrases = json.dumps(phrases_list)


# M-Pesa Service
class MPesaService:
    def __init__(self):
        self.consumer_key = app.config['MPESA_CONSUMER_KEY']
        self.consumer_secret = app.config['MPESA_CONSUMER_SECRET']
        self.shortcode = app.config['MPESA_SHORTCODE']
        self.passkey = app.config['MPESA_PASSKEY']
        self.environment = app.config['MPESA_ENVIRONMENT']

        if self.environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'

    def get_access_token(self):
        url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'
        auth_str = f'{self.consumer_key}:{self.consumer_secret}'
        auth_bytes = auth_str.encode('ascii')
        auth_base64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {'Authorization': f'Basic {auth_base64}'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json().get('access_token')
        return None

    def stk_push(self, phone_number, amount, account_reference, description):
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'message': 'Failed to get access token'}

        url = f'{self.base_url}/mpesa/stkpush/v1/processrequest'
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f'{self.shortcode}{self.passkey}{timestamp}'
        password = base64.b64encode(password_str.encode()).decode('utf-8')

        phone = phone_number.replace('+', '').replace(' ', '')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone,
            'PartyB': self.shortcode,
            'PhoneNumber': phone,
            'CallBackURL': url_for('licensing.mpesa_callback', _external=True),
            'AccountReference': account_reference,
            'TransactionDesc': description
        }

        response = requests.post(url, json=payload, headers=headers)
        return response.json()


mpesa_service = MPesaService()


# Decorators
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


def license_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user = User.query.get(session['user_id'])
        if user.is_admin:
            return f(*args, **kwargs)

        if not user.license or not user.license.is_valid():
            flash('Your subscription has expired. Please renew to continue.', 'error')
            return redirect(url_for('licensing.subscription'))

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


# Licensing Blueprint
licensing_bp = Blueprint('licensing', __name__, url_prefix='/licensing')


@licensing_bp.route('/subscription')
@login_required
def subscription():
    user = User.query.get(session['user_id'])
    license = user.license

    if not license and not user.is_admin:
        license = License(
            user_id=user.id,
            subscription_type='trial',
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
            is_active=True
        )
        db.session.add(license)
        db.session.commit()

    payments = Payment.query.filter_by(license_id=license.id).order_by(Payment.created_at.desc()).all() if license else []

    return render_template('licensing/subscription.html',
                         license=license,
                         payments=payments,
                         current_user=user)


@licensing_bp.route('/initiate-payment', methods=['POST'])
@login_required
def initiate_payment():
    user = User.query.get(session['user_id'])
    data = request.form

    phone_number = data.get('phone_number')
    subscription_type = data.get('subscription_type')

    prices = {
        'monthly': 2000,
        'yearly': 20000
    }

    amount = prices.get(subscription_type, 2000)

    payment = Payment(
        license_id=user.license.id if user.license else None,
        amount=amount,
        phone_number=phone_number,
        subscription_type=subscription_type,
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()

    result = mpesa_service.stk_push(
        phone_number=phone_number,
        amount=amount,
        account_reference=f'SUB-{user.id}',
        description=f'{subscription_type.capitalize()} Subscription'
    )

    if result.get('ResponseCode') == '0':
        payment.checkout_request_id = result.get('CheckoutRequestID')
        db.session.commit()

        flash('Payment request sent! Please enter your M-Pesa PIN.', 'success')
        return redirect(url_for('licensing.check_payment', payment_id=payment.id))
    else:
        payment.status = 'failed'
        db.session.commit()
        flash(f'Payment failed: {result.get("CustomerMessage", "Unknown error")}', 'error')
        return redirect(url_for('licensing.subscription'))


@licensing_bp.route('/check-payment/<int:payment_id>')
@login_required
def check_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    user = User.query.get(session['user_id'])

    if payment.license.user_id != user.id and not user.is_admin:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('licensing.subscription'))

    return render_template('licensing/check_payment.html', payment=payment)


@licensing_bp.route('/payment-status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    user = User.query.get(session['user_id'])

    if payment.license.user_id != user.id and not user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'status': payment.status,
        'mpesa_receipt': payment.mpesa_receipt,
        'completed_at': payment.completed_at.isoformat() if payment.completed_at else None
    })


@licensing_bp.route('/mpesa-callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()

    result_code = data['Body']['stkCallback']['ResultCode']
    checkout_request_id = data['Body']['stkCallback']['CheckoutRequestID']

    payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()

    if not payment:
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Payment not found'}), 404

    if result_code == 0:
        callback_metadata = data['Body']['stkCallback']['CallbackMetadata']['Item']
        mpesa_receipt = next((item['Value'] for item in callback_metadata if item['Name'] == 'MpesaReceiptNumber'), None)

        payment.status = 'completed'
        payment.mpesa_receipt = mpesa_receipt
        payment.completed_at = datetime.utcnow()

        license = payment.license
        if not license:
            license = License(user_id=payment.license.user_id)
            db.session.add(license)

        if payment.subscription_type == 'monthly':
            days = 30
        else:
            days = 365

        if license.end_date and license.end_date > datetime.utcnow():
            license.end_date += timedelta(days=days)
        else:
            license.start_date = datetime.utcnow()
            license.end_date = datetime.utcnow() + timedelta(days=days)

        license.subscription_type = payment.subscription_type
        license.is_active = True

        db.session.commit()

        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
    else:
        payment.status = 'failed'
        db.session.commit()

        return jsonify({'ResultCode': 1, 'ResultDesc': 'Payment failed'}), 200


# Main Routes
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
@license_required
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
    protected_admin_email = os.environ.get('ADMIN_EMAIL', 'admin@zearom.com').lower()

    if user.email.lower() == protected_admin_email:
        flash(f'The super admin account ({protected_admin_email}) cannot be modified.', 'error')
        return redirect(url_for('users'))

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

    existing_user = User.query.filter(User.email.ilike(email), User.id != user_id).first()
    if existing_user:
        flash('Email already in use by another user.', 'error')
        return redirect(url_for('users'))

    user.email = email
    user.full_name = full_name
    user.is_admin = is_admin
    user.updated_at = datetime.utcnow()

    if password:
        user.password_hash = generate_password_hash(password)

    db.session.commit()
    flash(f'User {email} updated successfully!', 'success')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    protected_admin_email = os.environ.get('ADMIN_EMAIL', 'admin@zearom.com').lower()

    if user.email.lower() == protected_admin_email:
        flash(f'The super admin account ({protected_admin_email}) cannot be deactivated.', 'error')
        return redirect(url_for('users'))

    if user.id == session['user_id']:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('users'))

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
    protected_admin_email = os.environ.get('ADMIN_EMAIL', 'admin@zearom.com').lower()

    if user.email.lower() == protected_admin_email:
        flash(f'The super admin account ({protected_admin_email}) cannot be deleted.', 'error')
        return redirect(url_for('users'))

    if user.id == session['user_id']:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('users'))

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

        fields = [
            'main_text', 'secondary_text', 'ticker_text', 'company_name',
            'bg_color', 'accent_color', 'text_color', 'font_family', 'layout_style',
            'secondary_transition_type', 'vertical_position', 'horizontal_position',
            'container_width', 'container_height', 'text_scale_mode'
        ]

        for field in fields:
            if field in data:
                setattr(settings, field, data[field])

        int_fields = [
            'main_font_size', 'secondary_font_size', 'ticker_font_size',
            'border_radius', 'ticker_speed', 'logo_size',
            'custom_top', 'custom_bottom', 'custom_left', 'custom_right',
            'custom_width', 'custom_height', 'container_max_width',
            'container_min_width', 'container_padding', 'text_max_lines'
        ]

        for field in int_fields:
            if field in data:
                setattr(settings, field, int(data[field]))

        float_fields = [
            'entrance_duration', 'entrance_delay', 'text_animation_speed',
            'image_animation_delay', 'logo_animation_delay', 'ticker_entrance_delay', 'opacity',
            'secondary_display_duration', 'secondary_transition_duration', 'text_line_height'
        ]

        for field in float_fields:
            if field in data:
                setattr(settings, field, float(data[field]))

        animation_fields = [
            'entrance_animation', 'text_animation', 'image_animation',
            'logo_animation', 'ticker_entrance'
        ]

        for field in animation_fields:
            if field in data:
                setattr(settings, field, data[field])

        if 'show_category_image' in data:
            settings.show_category_image = data['show_category_image'] == 'true'
        if 'show_decorative_elements' in data:
            settings.show_decorative_elements = data['show_decorative_elements'] == 'true'
        if 'secondary_rotation_enabled' in data:
            settings.secondary_rotation_enabled = data['secondary_rotation_enabled'] == 'true'
        if 'show_company_logo' in data:
            settings.show_company_logo = data['show_company_logo'] == 'true'
        if 'enable_text_truncation' in data:
            settings.enable_text_truncation = data['enable_text_truncation'] == 'true'

        settings.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'settings': settings_to_dict(settings)})

    return jsonify({'settings': settings_to_dict(settings)})


@app.route('/api/secondary-phrases/<category>', methods=['GET', 'POST'])
@login_required
def manage_secondary_phrases(category):
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        return jsonify({'error': 'Settings not found'}), 404

    if request.method == 'POST':
        data = request.get_json()
        phrases = data.get('phrases', [])
        phrases = [p.strip() for p in phrases if p.strip()]

        settings.set_secondary_phrases_list(phrases)
        settings.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'phrases': phrases})

    return jsonify({'phrases': settings.get_secondary_phrases_list()})


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

        settings.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'filename': relative_path})

    return jsonify({'error': 'Upload failed'}), 500


@app.route('/api/remove-logo/<category>', methods=['POST'])
@login_required
def remove_logo(category):
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        return jsonify({'error': 'Settings not found'}), 404

    settings.company_logo = None
    settings.show_company_logo = False
    settings.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': 'Logo removed successfully'})


@app.route('/api/visibility/<category>', methods=['POST'])
@login_required
def toggle_visibility(category):
    data = request.get_json()
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        return jsonify({'error': 'Settings not found'}), 404

    settings.is_visible = data.get('visible', True)
    settings.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'visible': settings.is_visible})


@app.route('/api/poll/<category>')
def poll_updates(category):
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        return jsonify({'error': 'Settings not found'}), 404

    return jsonify({
        'settings': settings_to_dict(settings),
        'timestamp': settings.updated_at.isoformat()
    })


def settings_to_dict(settings):
    return {
        'main_text': settings.main_text,
        'secondary_text': settings.secondary_text,
        'secondary_phrases': settings.get_secondary_phrases_list(),
        'secondary_rotation_enabled': settings.secondary_rotation_enabled,
        'secondary_display_duration': settings.secondary_display_duration,
        'secondary_transition_type': settings.secondary_transition_type,
        'secondary_transition_duration': settings.secondary_transition_duration,
        'ticker_text': settings.ticker_text,
        'company_name': settings.company_name,
        'company_logo': settings.company_logo,
        'category_image': settings.category_image,
        'show_category_image': settings.show_category_image,
        'show_company_logo': settings.show_company_logo,
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
        'ticker_entrance_delay': settings.ticker_entrance_delay,
        'vertical_position': settings.vertical_position,
        'horizontal_position': settings.horizontal_position,
        'custom_top': settings.custom_top,
        'custom_bottom': settings.custom_bottom,
        'custom_left': settings.custom_left,
        'custom_right': settings.custom_right,
        'container_width': settings.container_width,
        'custom_width': settings.custom_width,
        'container_max_width': settings.container_max_width,
        'container_min_width': settings.container_min_width,
        'container_height': settings.container_height,
        'custom_height': settings.custom_height,
        'container_padding': settings.container_padding,
        'text_scale_mode': settings.text_scale_mode,
        'text_line_height': settings.text_line_height,
        'text_max_lines': settings.text_max_lines,
        'enable_text_truncation': settings.enable_text_truncation
    }


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

        category_defaults = {
            'funeral': {
                'main_text': 'In Loving Memory',
                'secondary_phrases': json.dumps(['Forever in Our Hearts', 'Celebrating a Life Well Lived']),
                'vertical_position': 'bottom',
                'horizontal_position': 'left',
                'container_width': 'auto',
                'text_scale_mode': 'responsive'
            },
            'wedding': {
                'main_text': 'Together Forever',
                'secondary_phrases': json.dumps(['Celebrating Love & Unity', 'Two Hearts Become One']),
                'vertical_position': 'bottom',
                'horizontal_position': 'left',
                'container_width': 'auto',
                'text_scale_mode': 'responsive'
            },
            'ceremony': {
                'main_text': 'Special Ceremony',
                'secondary_phrases': json.dumps(['A Moment to Remember', 'Celebrating Excellence']),
                'vertical_position': 'bottom',
                'horizontal_position': 'left',
                'container_width': 'auto',
                'text_scale_mode': 'responsive'
            }
        }

        for category, defaults in category_defaults.items():
            settings = OverlaySettings.query.filter_by(category=category).first()
            if not settings:
                settings = OverlaySettings(category=category, is_visible=False, **defaults)
                db.session.add(settings)

        db.session.commit()
        print(f"Database initialized with admin user: {admin_email}")


# Register blueprint ONCE
app.register_blueprint(licensing_bp)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)