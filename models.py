from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


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

    license = db.relationship('License', backref='user', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'

    def to_dict(self):
        """Convert User object to dictionary for JSON serialization"""
        license_data = None
        if self.license:
            license_data = {
                'id': self.license.id,
                'subscription_type': self.license.subscription_type,
                'start_date': self.license.start_date.isoformat() if self.license.start_date else None,
                'end_date': self.license.end_date.isoformat() if self.license.end_date else None,
                'is_active': self.license.is_active,
                'is_valid': self.license.is_valid(),
                'days_remaining': self.license.days_remaining()
            }

        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'license': license_data
        }


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

    # NEW: Ticker visibility toggle
    show_ticker = db.Column(db.Boolean, default=True)

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

    # GRANULAR COLOR CONTROLS - Overlay Container
    overlay_bg_color = db.Column(db.String(7), default='#000000')
    overlay_bg_opacity = db.Column(db.Float, default=0.9)

    # Main Text Colors
    main_text_color = db.Column(db.String(7), default='#FFFFFF')
    main_text_bg_color = db.Column(db.String(7), default='transparent')
    main_text_bg_opacity = db.Column(db.Float, default=1.0)

    # Secondary Text Colors
    secondary_text_color = db.Column(db.String(7), default='#FFD700')
    secondary_text_bg_color = db.Column(db.String(7), default='transparent')
    secondary_text_bg_opacity = db.Column(db.Float, default=1.0)

    # Ticker Colors
    ticker_text_color = db.Column(db.String(7), default='#FFFFFF')
    ticker_bg_color = db.Column(db.String(7), default='#1a1a1a')
    ticker_bg_opacity = db.Column(db.Float, default=0.8)

    # Company Name Colors
    company_name_color = db.Column(db.String(7), default='#FFD700')
    company_name_bg_color = db.Column(db.String(7), default='transparent')
    company_name_bg_opacity = db.Column(db.Float, default=1.0)

    # Footer Colors
    footer_text_color = db.Column(db.String(7), default='#CCCCCC')
    footer_bg_color = db.Column(db.String(7), default='#1a1a1a')
    footer_bg_opacity = db.Column(db.Float, default=0.7)

    # Accent Color (for borders, decorations, etc)
    accent_color = db.Column(db.String(7), default='#FFD700')

    # Border Colors
    border_color = db.Column(db.String(7), default='#FFD700')
    border_width = db.Column(db.Integer, default=0)

    # Legacy color fields (kept for backwards compatibility)
    bg_color = db.Column(db.String(7), default='#000000')
    text_color = db.Column(db.String(7), default='#FFFFFF')

    # Font Sizes
    main_font_size = db.Column(db.Integer, default=32)
    secondary_font_size = db.Column(db.Integer, default=24)
    ticker_font_size = db.Column(db.Integer, default=18)
    company_name_font_size = db.Column(db.Integer, default=20)
    footer_font_size = db.Column(db.Integer, default=14)

    border_radius = db.Column(db.Integer, default=10)
    font_family = db.Column(db.String(100), default='Arial, sans-serif')
    ticker_speed = db.Column(db.Integer, default=50)

    # Logo Settings
    logo_size = db.Column(db.Integer, default=80)
    logo_opacity = db.Column(db.Float, default=1.0)
    logo_border_radius = db.Column(db.Integer, default=0)
    logo_shadow = db.Column(db.Boolean, default=False)

    # Layout specific settings
    layout_style = db.Column(db.String(50), default='default')
    show_decorative_elements = db.Column(db.Boolean, default=True)
    opacity = db.Column(db.Float, default=0.9)

    # Animation Settings
    entrance_animation = db.Column(db.String(50), default='slide-left')
    entrance_duration = db.Column(db.Float, default=1.0)
    entrance_delay = db.Column(db.Float, default=0.0)
    text_animation = db.Column(db.String(50), default='none')
    text_animation_speed = db.Column(db.Float, default=1.0)
    image_animation = db.Column(db.String(50), default='none')
    image_animation_delay = db.Column(db.Float, default=0.0)
    logo_animation = db.Column(db.String(50), default='fade-in')
    logo_animation_delay = db.Column(db.Float, default=0.0)
    ticker_entrance = db.Column(db.String(50), default='slide-left')
    ticker_entrance_delay = db.Column(db.Float, default=0.5)

    # Display Animation Settings (New)
    logo_display_animation = db.Column(db.String(50), default='none')
    logo_display_animation_enabled = db.Column(db.Boolean, default=False)
    logo_display_animation_duration = db.Column(db.Float, default=3.0)
    logo_display_animation_frequency = db.Column(db.Float, default=5.0)

    image_display_animation = db.Column(db.String(50), default='none')
    image_display_animation_enabled = db.Column(db.Boolean, default=False)
    image_display_animation_duration = db.Column(db.Float, default=3.0)
    image_display_animation_frequency = db.Column(db.Float, default=5.0)

    # Visibility
    is_visible = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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

    @staticmethod
    def get_defaults(category='funeral'):
        """Get default settings for a category"""
        defaults = {
            'funeral': {
                'overlay_bg_color': '#000000',
                'overlay_bg_opacity': 0.9,
                'main_text_color': '#FFFFFF',
                'main_text_bg_color': 'transparent',
                'main_text_bg_opacity': 1.0,
                'secondary_text_color': '#FFD700',
                'secondary_text_bg_color': 'transparent',
                'secondary_text_bg_opacity': 1.0,
                'ticker_text_color': '#FFFFFF',
                'ticker_bg_color': '#1a1a1a',
                'ticker_bg_opacity': 0.8,
                'company_name_color': '#FFD700',
                'company_name_bg_color': 'transparent',
                'company_name_bg_opacity': 1.0,
                'footer_text_color': '#CCCCCC',
                'footer_bg_color': '#1a1a1a',
                'footer_bg_opacity': 0.7,
                'accent_color': '#FFD700',
                'border_color': '#FFD700',
                'border_width': 0,
                'logo_animation': 'scale-in',
                'logo_opacity': 1.0,
                'logo_border_radius': 0,
                'logo_shadow': False,
                'show_ticker': True,
                'logo_display_animation': 'pulse',
                'logo_display_animation_enabled': False,
                'logo_display_animation_duration': 3.0,
                'logo_display_animation_frequency': 5.0,
                'image_display_animation': 'zoom-slow',
                'image_display_animation_enabled': False,
                'image_display_animation_duration': 3.0,
                'image_display_animation_frequency': 5.0
            },
            'wedding': {
                'overlay_bg_color': '#FFFFFF',
                'overlay_bg_opacity': 0.95,
                'main_text_color': '#D4AF37',
                'main_text_bg_color': 'transparent',
                'main_text_bg_opacity': 1.0,
                'secondary_text_color': '#8B7355',
                'secondary_text_bg_color': 'transparent',
                'secondary_text_bg_opacity': 1.0,
                'ticker_text_color': '#333333',
                'ticker_bg_color': '#F5F5DC',
                'ticker_bg_opacity': 0.9,
                'company_name_color': '#D4AF37',
                'company_name_bg_color': 'transparent',
                'company_name_bg_opacity': 1.0,
                'footer_text_color': '#666666',
                'footer_bg_color': '#F5F5DC',
                'footer_bg_opacity': 0.8,
                'accent_color': '#D4AF37',
                'border_color': '#D4AF37',
                'border_width': 2,
                'logo_animation': 'fade-in',
                'logo_opacity': 1.0,
                'logo_border_radius': 50,
                'logo_shadow': True,
                'show_ticker': True,
                'logo_display_animation': 'float',
                'logo_display_animation_enabled': False,
                'logo_display_animation_duration': 3.0,
                'logo_display_animation_frequency': 5.0,
                'image_display_animation': 'pan',
                'image_display_animation_enabled': False,
                'image_display_animation_duration': 3.0,
                'image_display_animation_frequency': 5.0
            },
            'ceremony': {
                'overlay_bg_color': '#1a237e',
                'overlay_bg_opacity': 0.9,
                'main_text_color': '#FFFFFF',
                'main_text_bg_color': 'transparent',
                'main_text_bg_opacity': 1.0,
                'secondary_text_color': '#FFD700',
                'secondary_text_bg_color': 'transparent',
                'secondary_text_bg_opacity': 1.0,
                'ticker_text_color': '#FFFFFF',
                'ticker_bg_color': '#0d47a1',
                'ticker_bg_opacity': 0.8,
                'company_name_color': '#FFD700',
                'company_name_bg_color': 'transparent',
                'company_name_bg_opacity': 1.0,
                'footer_text_color': '#DDDDDD',
                'footer_bg_color': '#0d47a1',
                'footer_bg_opacity': 0.7,
                'accent_color': '#FFD700',
                'border_color': '#FFD700',
                'border_width': 1,
                'logo_animation': 'rotate-in',
                'logo_opacity': 1.0,
                'logo_border_radius': 10,
                'logo_shadow': False,
                'show_ticker': True,
                'logo_display_animation': 'rotate-slow',
                'logo_display_animation_enabled': False,
                'logo_display_animation_duration': 3.0,
                'logo_display_animation_frequency': 5.0,
                'image_display_animation': 'zoom-slow',
                'image_display_animation_enabled': False,
                'image_display_animation_duration': 3.0,
                'image_display_animation_frequency': 5.0
            }
        }
        return defaults.get(category, defaults['funeral'])


class OCRSession(db.Model):
    __tablename__ = 'ocr_sessions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='general')
    combined_text = db.Column(db.Text)
    image_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')
    used_in_ticker = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship('OCRImage', backref='session', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<OCRSession {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'combined_text': self.combined_text,
            'image_count': self.image_count,
            'status': self.status,
            'used_in_ticker': self.used_in_ticker,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class OCRImage(db.Model):
    __tablename__ = 'ocr_images'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(300), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    extracted_text = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')
    session_id = db.Column(db.Integer, db.ForeignKey('ocr_sessions.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<OCRImage {self.filename} - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': self.filepath,
            'order_index': self.order_index,
            'extracted_text': self.extracted_text,
            'status': self.status,
            'error_message': self.error_message,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }