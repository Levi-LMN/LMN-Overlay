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

    # ── Content ────────────────────────────────────────────────────────────
    main_text = db.Column(db.String(200))
    secondary_text = db.Column(db.String(200))
    secondary_phrases = db.Column(db.Text)          # JSON list of rotation phrases
    ticker_text = db.Column(db.String(500))
    company_name = db.Column(db.String(100))
    company_logo = db.Column(db.String(200))        # relative path under static/
    category_image = db.Column(db.String(200))      # relative path under static/
    show_category_image = db.Column(db.Boolean, default=True)
    show_company_logo = db.Column(db.Boolean, default=True)
    show_ticker = db.Column(db.Boolean, default=True)
    show_secondary_text = db.Column(db.Boolean, default=True)
    show_company_name = db.Column(db.Boolean, default=True)

    # ── Secondary Text Rotation ────────────────────────────────────────────
    secondary_rotation_enabled = db.Column(db.Boolean, default=False)
    secondary_display_duration = db.Column(db.Float, default=3.0)
    secondary_transition_type = db.Column(db.String(50), default='fade')
    secondary_transition_duration = db.Column(db.Float, default=0.5)

    # ── Overlay Position & Size ────────────────────────────────────────────
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

    # ── Text Scaling ───────────────────────────────────────────────────────
    text_scale_mode = db.Column(db.String(20), default='responsive')
    text_line_height = db.Column(db.Float, default=1.2)
    text_max_lines = db.Column(db.Integer, default=2)
    enable_text_truncation = db.Column(db.Boolean, default=True)

    # ── Overlay Background ─────────────────────────────────────────────────
    overlay_bg_color = db.Column(db.String(7), default='#000000')
    overlay_bg_opacity = db.Column(db.Float, default=0.9)

    # ── Sectioned Background (top / middle / bottom strips) ────────────────
    overlay_bg_sections_enabled = db.Column(db.Boolean, default=False)
    overlay_bg_top_color        = db.Column(db.String(7),  default='#222222')
    overlay_bg_top_opacity      = db.Column(db.Float,      default=0.95)
    overlay_bg_top_height       = db.Column(db.Integer,    default=25)   # % of overlay height
    overlay_bg_bottom_color     = db.Column(db.String(7),  default='#222222')
    overlay_bg_bottom_opacity   = db.Column(db.Float,      default=0.95)
    overlay_bg_bottom_height    = db.Column(db.Integer,    default=25)   # % of overlay height

    # ── Clock / Time Display ────────────────────────────────────────────────
    show_clock          = db.Column(db.Boolean,     default=False)
    clock_format        = db.Column(db.String(5),   default='24h')   # 12h | 24h
    clock_show_time     = db.Column(db.Boolean,     default=True)    # renamed from clock_show_seconds
    clock_font_size     = db.Column(db.Integer,     default=13)
    clock_font_family   = db.Column(db.String(100), default=None)
    clock_color         = db.Column(db.String(7),   default='#FFFFFF')
    clock_bg_color      = db.Column(db.String(7),   default='#000000')
    clock_bg_opacity    = db.Column(db.Float,       default=0.0)
    clock_animation     = db.Column(db.String(50),  default='none')
    clock_position      = db.Column(db.String(20),  default='bottom')

    # ── Live Location Indicator ─────────────────────────────────────────────
    show_live_indicator              = db.Column(db.Boolean,     default=False)
    live_label                       = db.Column(db.String(50),  default='LIVE')
    live_location                    = db.Column(db.String(100), default='')
    live_indicator_color             = db.Column(db.String(7),   default='#FFFFFF')
    live_indicator_bg_color          = db.Column(db.String(7),   default='#CC0000')
    live_indicator_bg_opacity        = db.Column(db.Float,       default=0.9)
    live_indicator_font_size         = db.Column(db.Integer,     default=16)
    live_indicator_font_family       = db.Column(db.String(100), default=None)
    live_indicator_animation         = db.Column(db.String(50),  default='pulse')
    live_indicator_vertical_position   = db.Column(db.String(20), default='top')
    live_indicator_horizontal_position = db.Column(db.String(20), default='left')

    # ── Live Label & Location — per-part colours ───────────────────────────
    live_label_color         = db.Column(db.String(7),  default='#FFFFFF')
    live_label_bg_color      = db.Column(db.String(7),  default='#CC0000')
    live_label_bg_opacity    = db.Column(db.Float,      default=0.9)
    live_location_color      = db.Column(db.String(7),  default='#FFFFFF')
    live_location_bg_color   = db.Column(db.String(7),  default='#000000')
    live_location_bg_opacity = db.Column(db.Float,      default=0.0)

    # ── Main Text Colors ───────────────────────────────────────────────────
    main_text_color = db.Column(db.String(7), default='#FFFFFF')
    main_text_bg_color = db.Column(db.String(7), default='#000000')
    main_text_bg_opacity = db.Column(db.Float, default=0.0)

    # ── Secondary Text Colors ──────────────────────────────────────────────
    secondary_text_color = db.Column(db.String(7), default='#FFD700')
    secondary_text_bg_color = db.Column(db.String(7), default='#000000')
    secondary_text_bg_opacity = db.Column(db.Float, default=0.0)

    # ── Ticker Colors ──────────────────────────────────────────────────────
    ticker_text_color = db.Column(db.String(7), default='#FFFFFF')
    ticker_bg_color = db.Column(db.String(7), default='#1a1a1a')
    ticker_bg_opacity = db.Column(db.Float, default=0.8)

    # ── Company Name Colors ────────────────────────────────────────────────
    company_name_color = db.Column(db.String(7), default='#FFD700')
    company_name_bg_color = db.Column(db.String(7), default='#000000')
    company_name_bg_opacity = db.Column(db.Float, default=0.0)

    # ── Footer Colors ──────────────────────────────────────────────────────
    footer_text_color = db.Column(db.String(7), default='#CCCCCC')
    footer_bg_color = db.Column(db.String(7), default='#1a1a1a')
    footer_bg_opacity = db.Column(db.Float, default=0.7)

    # ── Accent / Border ────────────────────────────────────────────────────
    accent_color = db.Column(db.String(7), default='#FFD700')
    border_color = db.Column(db.String(7), default='#FFD700')
    border_width = db.Column(db.Integer, default=0)

    # ── Legacy color fields (backwards compatibility) ──────────────────────
    bg_color = db.Column(db.String(7), default='#000000')
    text_color = db.Column(db.String(7), default='#FFFFFF')

    # ── Font Sizes ─────────────────────────────────────────────────────────
    main_font_size = db.Column(db.Integer, default=32)
    secondary_font_size = db.Column(db.Integer, default=24)
    ticker_font_size = db.Column(db.Integer, default=18)
    company_name_font_size = db.Column(db.Integer, default=20)
    footer_font_size = db.Column(db.Integer, default=14)

    border_radius = db.Column(db.Integer, default=10)

    # ── Font Families ──────────────────────────────────────────────────────
    font_family = db.Column(db.String(100), default='Arial, sans-serif')
    # Per-section overrides — NULL means fall back to the global font_family
    main_font_family = db.Column(db.String(100), default=None)
    secondary_font_family = db.Column(db.String(100), default=None)
    ticker_font_family = db.Column(db.String(100), default=None)
    company_name_font_family = db.Column(db.String(100), default=None)

    company_name_italic = db.Column(db.Boolean, default=True)
    ticker_speed = db.Column(db.Integer, default=50)

    # ── Logo Appearance ────────────────────────────────────────────────────
    logo_size = db.Column(db.Integer, default=80)
    logo_opacity = db.Column(db.Float, default=1.0)
    logo_border_radius = db.Column(db.Integer, default=0)
    logo_shadow = db.Column(db.Boolean, default=False)

    # ── Logo Position ──────────────────────────────────────────────────────
    # Preset positions: top | middle | bottom  ×  left | center | right
    # Set either axis to 'custom' and supply logo_custom_* px values below.
    logo_vertical_position = db.Column(db.String(20), default='top')
    logo_horizontal_position = db.Column(db.String(20), default='right')
    # Custom pixel offsets (used when the corresponding axis is 'custom')
    logo_custom_top = db.Column(db.Integer, default=None)
    logo_custom_bottom = db.Column(db.Integer, default=None)
    logo_custom_left = db.Column(db.Integer, default=None)
    logo_custom_right = db.Column(db.Integer, default=None)

    # ── Category Image / Photo Container ──────────────────────────────────
    image_size = db.Column(db.Integer, default=128)
    image_shape = db.Column(db.String(20), default='circle')   # circle | square | rounded
    image_border_width = db.Column(db.Integer, default=3)
    image_border_color = db.Column(db.String(7), default='#FFFFFF')
    image_position = db.Column(db.String(12), default='left')  # left | right | top | bottom | top-left | top-right
    image_fit = db.Column(db.String(10), default='cover')      # cover | contain | fill
    image_object_position = db.Column(db.String(20), default='center center')  # CSS object-position from cropper
    image_zoom = db.Column(db.Integer, default=100)            # zoom % from cropper (100 = no zoom)

    # ── Layout ────────────────────────────────────────────────────────────
    layout_style = db.Column(db.String(50), default='default')
    show_decorative_elements = db.Column(db.Boolean, default=True)
    opacity = db.Column(db.Float, default=0.9)

    # ── Entrance Animations ────────────────────────────────────────────────
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

    # ── Continuous Display Animations ─────────────────────────────────────
    logo_display_animation = db.Column(db.String(50), default='none')
    logo_display_animation_enabled = db.Column(db.Boolean, default=False)
    logo_display_animation_duration = db.Column(db.Float, default=3.0)
    logo_display_animation_frequency = db.Column(db.Float, default=5.0)

    image_display_animation = db.Column(db.String(50), default='none')
    image_display_animation_enabled = db.Column(db.Boolean, default=False)
    image_display_animation_duration = db.Column(db.Float, default=3.0)
    image_display_animation_frequency = db.Column(db.Float, default=5.0)

    # ── Per-section Text Animations ────────────────────────────────────────
    # NULL on any of these means "use the global text_animation value"
    main_text_animation = db.Column(db.String(50), default=None)
    secondary_text_animation = db.Column(db.String(50), default=None)
    company_name_animation = db.Column(db.String(50), default=None)
    # 0 = play once, no repeat; >0 = replay every N seconds
    text_animation_repeat_interval = db.Column(db.Float, default=0.0)

    # ── Overlay Auto-Cycle ─────────────────────────────────────────────────
    # Show overlay for overlay_visible_duration secs, hide for
    # overlay_hidden_duration secs, then repeat indefinitely.
    overlay_cycle_enabled = db.Column(db.Boolean, default=False)
    overlay_visible_duration = db.Column(db.Float, default=10.0)
    overlay_hidden_duration = db.Column(db.Float, default=5.0)
    cycle_entry_animation = db.Column(db.String(50), default='fade')
    cycle_exit_animation = db.Column(db.String(50), default='fade')
    cycle_transition_duration = db.Column(db.Float, default=0.6)

    # ── Staggered Element Entry / Exit ────────────────────────────────────
    stagger_enabled = db.Column(db.Boolean, default=False)
    stagger_order = db.Column(db.String(100), default='main,secondary,company')
    stagger_delay = db.Column(db.Float, default=0.3)
    stagger_element_exit = db.Column(db.String(50), default='fade')
    stagger_element_entry = db.Column(db.String(50), default='fade')

    # ── Visibility & Timestamps ────────────────────────────────────────────
    is_visible = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<OverlaySettings {self.category}>'

    # ── Helper methods ─────────────────────────────────────────────────────

    def get_secondary_phrases_list(self):
        if self.secondary_phrases:
            try:
                return json.loads(self.secondary_phrases)
            except Exception:
                return []
        return []

    def set_secondary_phrases_list(self, phrases_list):
        self.secondary_phrases = json.dumps(phrases_list)

    @staticmethod
    def get_defaults(category='funeral'):
        """Return a flat dict of sensible defaults for each built-in category.
        Used by the reset endpoint and by app.py on first-run initialisation.
        Every column on OverlaySettings (except id, category, created_at,
        updated_at, and the file-path fields company_logo / category_image)
        must appear here so that a full reset actually resets everything."""

        # ── Shared blocks (same across all categories unless overridden) ──────

        _shared_content = {
            'secondary_text':          '',
            'ticker_text':             '',
            'company_name':            '',
            'secondary_phrases':       '[]',
            'show_category_image':     True,
            'show_company_logo':       True,
            'show_ticker':             True,
        }

        _shared_secondary_rotation = {
            'secondary_rotation_enabled':   False,
            'secondary_display_duration':   3.0,
            'secondary_transition_type':    'fade',
            'secondary_transition_duration': 0.5,
        }

        _shared_position = {
            'vertical_position':    'bottom',
            'horizontal_position':  'left',
            'custom_top':           0,
            'custom_bottom':        0,
            'custom_left':          0,
            'custom_right':         0,
            'container_width':      'auto',
            'custom_width':         800,
            'container_max_width':  1200,
            'container_min_width':  600,
            'container_height':     'auto',
            'custom_height':        200,
            'container_padding':    25,
        }

        _shared_text_scale = {
            'text_scale_mode':        'responsive',
            'text_line_height':       1.2,
            'text_max_lines':         2,
            'enable_text_truncation': True,
        }

        _shared_layout = {
            'layout_style':             'default',
            'show_decorative_elements': True,
            'opacity':                  0.9,
            'border_radius':            10,
        }

        _shared_fonts = {
            'font_family':              'Arial, sans-serif',
            'main_font_family':         None,
            'secondary_font_family':    None,
            'ticker_font_family':       None,
            'company_name_font_family': None,
            'company_name_italic':      True,
            'ticker_speed':             50,
            'main_font_size':           32,
            'secondary_font_size':      24,
            'ticker_font_size':         18,
            'company_name_font_size':   20,
            'footer_font_size':         14,
        }

        _shared_logo_pos = {
            'logo_vertical_position':   'top',
            'logo_horizontal_position': 'right',
            'logo_custom_top':          None,
            'logo_custom_bottom':       None,
            'logo_custom_left':         None,
            'logo_custom_right':        None,
        }

        _shared_logo_appearance = {
            'logo_size':           80,
            'logo_opacity':        1.0,
            'logo_border_radius':  0,
            'logo_shadow':         False,
        }

        _shared_image = {
            'image_size':            128,
            'image_shape':           'circle',
            'image_border_width':    3,
            'image_border_color':    '#FFFFFF',
            'image_position':        'left',
            'image_fit':             'cover',
            'image_object_position': 'center center',
            'image_zoom':            100,
        }

        _shared_entrance_anim = {
            'entrance_animation':   'slide-left',
            'entrance_duration':    1.0,
            'entrance_delay':       0.0,
            'text_animation':       'none',
            'text_animation_speed': 1.0,
            'image_animation':      'none',
            'image_animation_delay': 0.0,
            'logo_animation':       'fade-in',
            'logo_animation_delay': 0.0,
            'ticker_entrance':      'slide-left',
            'ticker_entrance_delay': 0.5,
        }

        _shared_display_anim = {
            'logo_display_animation':           'none',
            'logo_display_animation_enabled':   False,
            'logo_display_animation_duration':  3.0,
            'logo_display_animation_frequency': 5.0,
            'image_display_animation':          'none',
            'image_display_animation_enabled':  False,
            'image_display_animation_duration': 3.0,
            'image_display_animation_frequency': 5.0,
        }

        _shared_text_anim = {
            'main_text_animation':          None,
            'secondary_text_animation':     None,
            'company_name_animation':       None,
            'text_animation_repeat_interval': 0.0,
        }

        _shared_cycle = {
            'overlay_cycle_enabled':     False,
            'overlay_visible_duration':  10.0,
            'overlay_hidden_duration':   5.0,
            'cycle_entry_animation':     'fade',
            'cycle_exit_animation':      'fade',
            'cycle_transition_duration': 0.6,
        }

        _shared_stagger = {
            'stagger_enabled':       False,
            'stagger_order':         'main,secondary,company',
            'stagger_delay':         0.3,
            'stagger_element_exit':  'fade',
            'stagger_element_entry': 'fade',
        }

        _shared_sectioned_bg = {
            'overlay_bg_sections_enabled': False,
            'overlay_bg_top_color':        '#222222',
            'overlay_bg_top_opacity':      0.95,
            'overlay_bg_top_height':       25,
            'overlay_bg_bottom_color':     '#222222',
            'overlay_bg_bottom_opacity':   0.95,
            'overlay_bg_bottom_height':    25,
        }

        _shared_clock = {
            'show_clock':        False,
            'clock_format':      '24h',
            'clock_show_time':   True,
            'clock_font_size':   13,
            'clock_font_family': None,
            'clock_color':       '#FFFFFF',
            'clock_bg_color':    '#000000',
            'clock_bg_opacity':  0.0,
            'clock_animation':   'none',
            'clock_position':    'bottom',
        }

        _shared_live = {
            'show_live_indicator':                False,
            'live_label':                         'LIVE',
            'live_location':                      '',
            'live_indicator_color':               '#FFFFFF',
            'live_indicator_bg_color':            '#CC0000',
            'live_indicator_bg_opacity':          0.9,
            'live_indicator_font_size':           16,
            'live_indicator_font_family':         None,
            'live_indicator_animation':           'pulse',
            'live_indicator_vertical_position':   'top',
            'live_indicator_horizontal_position': 'left',
            # per-part colours
            'live_label_color':         '#FFFFFF',
            'live_label_bg_color':      '#CC0000',
            'live_label_bg_opacity':    0.9,
            'live_location_color':      '#FFFFFF',
            'live_location_bg_color':   '#000000',
            'live_location_bg_opacity': 0.0,
        }

        _shared_legacy = {
            'bg_color':   '#000000',
            'text_color': '#FFFFFF',
        }

        # Merge all shared blocks into a single base that every category starts from
        _base = {
            **_shared_content,
            **_shared_secondary_rotation,
            **_shared_position,
            **_shared_text_scale,
            **_shared_layout,
            **_shared_fonts,
            **_shared_logo_pos,
            **_shared_logo_appearance,
            **_shared_image,
            **_shared_entrance_anim,
            **_shared_display_anim,
            **_shared_text_anim,
            **_shared_cycle,
            **_shared_stagger,
            **_shared_sectioned_bg,
            **_shared_clock,
            **_shared_live,
            **_shared_legacy,
            'is_visible': False,
        }

        # ── Per-category overrides ────────────────────────────────────────────
        _category_overrides = {
            'funeral': {
                'main_text':              'In Loving Memory',
                'secondary_phrases':      '["Forever in Our Hearts", "Celebrating a Life Well Lived"]',
                # Colors
                'overlay_bg_color':       '#000000',
                'overlay_bg_opacity':     0.9,
                'main_text_color':        '#FFFFFF',
                'main_text_bg_color':     '#000000',
                'main_text_bg_opacity':   1.0,
                'secondary_text_color':   '#FFD700',
                'secondary_text_bg_color':  '#000000',
                'secondary_text_bg_opacity': 1.0,
                'ticker_text_color':      '#FFFFFF',
                'ticker_bg_color':        '#1a1a1a',
                'ticker_bg_opacity':      0.8,
                'company_name_color':     '#FFD700',
                'company_name_bg_color':  '#000000',
                'company_name_bg_opacity': 1.0,
                'footer_text_color':      '#CCCCCC',
                'footer_bg_color':        '#1a1a1a',
                'footer_bg_opacity':      0.7,
                'accent_color':           '#FFD700',
                'border_color':           '#FFD700',
                'border_width':           0,
                # Logo
                'logo_animation':         'scale-in',
                'logo_display_animation': 'pulse',
                # Image
                'image_display_animation': 'zoom-slow',
            },
            'wedding': {
                'main_text':              'Together Forever',
                'secondary_phrases':      '["Celebrating Love & Unity", "Two Hearts Become One"]',
                # Colors
                'overlay_bg_color':       '#FFFFFF',
                'overlay_bg_opacity':     0.95,
                'main_text_color':        '#D4AF37',
                'main_text_bg_color':     '#000000',
                'main_text_bg_opacity':   1.0,
                'secondary_text_color':   '#8B7355',
                'secondary_text_bg_color':  '#000000',
                'secondary_text_bg_opacity': 1.0,
                'ticker_text_color':      '#333333',
                'ticker_bg_color':        '#F5F5DC',
                'ticker_bg_opacity':      0.9,
                'company_name_color':     '#D4AF37',
                'company_name_bg_color':  '#000000',
                'company_name_bg_opacity': 1.0,
                'footer_text_color':      '#666666',
                'footer_bg_color':        '#F5F5DC',
                'footer_bg_opacity':      0.8,
                'accent_color':           '#D4AF37',
                'border_color':           '#D4AF37',
                'border_width':           2,
                # Logo
                'logo_animation':         'fade-in',
                'logo_border_radius':     50,
                'logo_shadow':            True,
                'logo_display_animation': 'float',
                # Image
                'image_border_color':     '#D4AF37',
                'image_position':         'right',
                'image_display_animation': 'pan',
            },
            'ceremony': {
                'main_text':              'Special Ceremony',
                'secondary_phrases':      '["A Moment to Remember", "Celebrating Excellence"]',
                # Colors
                'overlay_bg_color':       '#1a237e',
                'overlay_bg_opacity':     0.9,
                'main_text_color':        '#FFFFFF',
                'main_text_bg_color':     '#000000',
                'main_text_bg_opacity':   1.0,
                'secondary_text_color':   '#FFD700',
                'secondary_text_bg_color':  '#000000',
                'secondary_text_bg_opacity': 1.0,
                'ticker_text_color':      '#FFFFFF',
                'ticker_bg_color':        '#0d47a1',
                'ticker_bg_opacity':      0.8,
                'company_name_color':     '#FFD700',
                'company_name_bg_color':  '#000000',
                'company_name_bg_opacity': 1.0,
                'footer_text_color':      '#DDDDDD',
                'footer_bg_color':        '#0d47a1',
                'footer_bg_opacity':      0.7,
                'accent_color':           '#FFD700',
                'border_color':           '#FFD700',
                'border_width':           1,
                # Logo
                'logo_animation':         'rotate-in',
                'logo_border_radius':     10,
                'logo_display_animation': 'rotate-slow',
                # Image
                'image_size':             120,
                'image_border_color':     '#FFD700',
                'image_shape':            'rounded',
                'image_border_width':     2,
                'image_position':         'top',
                'image_display_animation': 'zoom-slow',
            },
        }

        overrides = _category_overrides.get(category, _category_overrides['funeral'])
        return {**_base, **overrides}


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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }