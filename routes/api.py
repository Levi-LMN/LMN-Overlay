from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, OverlaySettings
from utils.decorators import login_required
import os

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/settings/<category>', methods=['GET', 'POST'])
@login_required
def manage_settings(category):
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        settings = OverlaySettings(category=category)
        db.session.add(settings)

    if request.method == 'POST':
        data = request.form

        # Text fields
        fields = [
            'main_text', 'secondary_text', 'ticker_text', 'company_name',
            'font_family', 'layout_style',
            'secondary_transition_type', 'vertical_position', 'horizontal_position',
            'container_width', 'container_height', 'text_scale_mode',
            'logo_display_animation', 'image_display_animation',
            'image_shape', 'image_position', 'image_fit', 'image_object_position',
            'main_font_family', 'secondary_font_family',
            'ticker_font_family', 'company_name_font_family',
            'logo_vertical_position', 'logo_horizontal_position',
            # clock
            'clock_format', 'clock_animation', 'clock_position', 'clock_font_family',
            # live indicator
            'live_label', 'live_location', 'live_indicator_animation',
            'live_indicator_font_family',
            'live_indicator_vertical_position', 'live_indicator_horizontal_position',
        ]

        for field in fields:
            if field in data:
                setattr(settings, field, data[field])

        # Per-section fonts: treat empty string as NULL (= use global font)
        for font_field in ['main_font_family', 'secondary_font_family',
                           'ticker_font_family', 'company_name_font_family']:
            if font_field in data:
                val = data[font_field].strip()
                setattr(settings, font_field, val if val else None)

        # Color fields - Overlay
        color_fields = [
            'overlay_bg_color', 'main_text_color', 'main_text_bg_color',
            'secondary_text_color', 'secondary_text_bg_color',
            'ticker_text_color', 'ticker_bg_color',
            'company_name_color', 'company_name_bg_color',
            'footer_text_color', 'footer_bg_color',
            'accent_color', 'border_color',
            'bg_color', 'text_color',
            'image_border_color',
            # sectioned bg
            'overlay_bg_top_color', 'overlay_bg_bottom_color',
            # clock
            'clock_color', 'clock_bg_color',
            # live indicator
            'live_indicator_color', 'live_indicator_bg_color',
        ]

        for field in color_fields:
            if field in data:
                setattr(settings, field, data[field])

        # Integer fields - with validation for empty strings
        int_fields = [
            'main_font_size', 'secondary_font_size', 'ticker_font_size',
            'company_name_font_size', 'footer_font_size',
            'border_radius', 'ticker_speed', 'logo_size',
            'custom_top', 'custom_bottom', 'custom_left', 'custom_right',
            'custom_width', 'custom_height', 'container_max_width',
            'container_min_width', 'container_padding', 'text_max_lines',
            'border_width', 'logo_border_radius',
            'image_size', 'image_border_width', 'image_zoom',
            'logo_custom_top', 'logo_custom_bottom', 'logo_custom_left', 'logo_custom_right',
            # sectioned bg
            'overlay_bg_top_height', 'overlay_bg_bottom_height',
            # clock
            'clock_font_size',
            # live indicator
            'live_indicator_font_size',
        ]

        for field in int_fields:
            if field in data and data[field] and data[field].strip():
                try:
                    setattr(settings, field, int(data[field]))
                except ValueError:
                    # Skip if conversion fails
                    pass

        # Float fields - with validation for empty strings
        float_fields = [
            'entrance_duration', 'entrance_delay', 'text_animation_speed',
            'image_animation_delay', 'logo_animation_delay', 'ticker_entrance_delay',
            'opacity', 'secondary_display_duration', 'secondary_transition_duration',
            'text_line_height', 'overlay_bg_opacity', 'main_text_bg_opacity',
            'secondary_text_bg_opacity', 'ticker_bg_opacity',
            'company_name_bg_opacity', 'footer_bg_opacity', 'logo_opacity',
            'logo_display_animation_duration', 'logo_display_animation_frequency',
            'image_display_animation_duration', 'image_display_animation_frequency',
            'text_animation_repeat_interval',
            'overlay_visible_duration', 'overlay_hidden_duration',
            'cycle_transition_duration', 'stagger_delay',
            # sectioned bg
            'overlay_bg_top_opacity', 'overlay_bg_bottom_opacity',
            # clock
            'clock_bg_opacity',
            # live indicator
            'live_indicator_bg_opacity',
        ]

        for field in float_fields:
            if field in data and data[field] and data[field].strip():
                try:
                    setattr(settings, field, float(data[field]))
                except ValueError:
                    # Skip if conversion fails
                    pass

        # Animation fields
        animation_fields = [
            'entrance_animation', 'text_animation', 'image_animation',
            'logo_animation', 'ticker_entrance',
            'main_text_animation', 'secondary_text_animation', 'company_name_animation',
            'cycle_entry_animation', 'cycle_exit_animation',
            'stagger_order', 'stagger_element_exit', 'stagger_element_entry'
        ]

        for field in animation_fields:
            if field in data:
                setattr(settings, field, data[field])

        # Boolean fields
        boolean_fields = [
            ('show_category_image', 'show_category_image'),
            ('show_decorative_elements', 'show_decorative_elements'),
            ('secondary_rotation_enabled', 'secondary_rotation_enabled'),
            ('show_company_logo', 'show_company_logo'),
            ('enable_text_truncation', 'enable_text_truncation'),
            ('logo_shadow', 'logo_shadow'),
            ('show_ticker', 'show_ticker'),
            ('logo_display_animation_enabled', 'logo_display_animation_enabled'),
            ('image_display_animation_enabled', 'image_display_animation_enabled'),
            ('company_name_italic', 'company_name_italic'),
            ('overlay_cycle_enabled', 'overlay_cycle_enabled'),
            ('stagger_enabled', 'stagger_enabled'),
            # sectioned bg
            ('overlay_bg_sections_enabled', 'overlay_bg_sections_enabled'),
            # clock
            ('show_clock', 'show_clock'),
            ('clock_show_time', 'clock_show_time'),
            # live indicator
            ('show_live_indicator', 'show_live_indicator'),
        ]

        for field_name, db_field in boolean_fields:
            if field_name in data:
                setattr(settings, db_field, data[field_name] == 'true')

        settings.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'settings': settings_to_dict(settings)})

    return jsonify({'settings': settings_to_dict(settings)})


@api_bp.route('/settings/<category>/reset', methods=['POST'])
@login_required
def reset_settings(category):
    """Reset settings to defaults for the category"""
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        return jsonify({'error': 'Settings not found'}), 404

    # Get default settings for this category
    defaults = OverlaySettings.get_defaults(category)

    # Apply defaults
    for key, value in defaults.items():
        if hasattr(settings, key):
            setattr(settings, key, value)

    settings.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'settings': settings_to_dict(settings), 'message': 'Settings reset to defaults'})


@api_bp.route('/secondary-phrases/<category>', methods=['GET', 'POST'])
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


@api_bp.route('/upload/<category>/<file_type>', methods=['POST'])
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
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
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


@api_bp.route('/remove-logo/<category>', methods=['POST'])
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


@api_bp.route('/remove-image/<category>', methods=['POST'])
@login_required
def remove_image(category):
    """Remove category background image"""
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        return jsonify({'error': 'Settings not found'}), 404

    settings.category_image = None
    settings.show_category_image = False
    settings.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': 'Image removed successfully'})


@api_bp.route('/visibility/<category>', methods=['POST'])
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


@api_bp.route('/poll/<category>')
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
        'show_ticker': settings.show_ticker,

        # Granular Color Controls
        'overlay_bg_color': settings.overlay_bg_color,
        'overlay_bg_opacity': settings.overlay_bg_opacity,

        # Sectioned background
        'overlay_bg_sections_enabled': settings.overlay_bg_sections_enabled or False,
        'overlay_bg_top_color':        settings.overlay_bg_top_color    or '#222222',
        'overlay_bg_top_opacity':      settings.overlay_bg_top_opacity  if settings.overlay_bg_top_opacity  is not None else 0.95,
        'overlay_bg_top_height':       settings.overlay_bg_top_height   if settings.overlay_bg_top_height   is not None else 25,
        'overlay_bg_bottom_color':     settings.overlay_bg_bottom_color or '#222222',
        'overlay_bg_bottom_opacity':   settings.overlay_bg_bottom_opacity if settings.overlay_bg_bottom_opacity is not None else 0.95,
        'overlay_bg_bottom_height':    settings.overlay_bg_bottom_height   if settings.overlay_bg_bottom_height  is not None else 25,

        # Day & Time Bar
        'show_clock':        settings.show_clock         or False,
        'clock_format':      settings.clock_format       or '24h',
        'clock_show_time':   settings.clock_show_time    if settings.clock_show_time    is not None else True,
        'clock_font_size':   settings.clock_font_size    or 13,
        'clock_font_family': settings.clock_font_family,
        'clock_color':       settings.clock_color        or '#FFFFFF',
        'clock_bg_color':    settings.clock_bg_color     or '#000000',
        'clock_bg_opacity':  settings.clock_bg_opacity   if settings.clock_bg_opacity   is not None else 0.0,
        'clock_animation':   settings.clock_animation    or 'none',
        'clock_position':    settings.clock_position     or 'bottom',

        # Live indicator
        'show_live_indicator':               settings.show_live_indicator              or False,
        'live_label':                        settings.live_label                       or 'LIVE',
        'live_location':                     settings.live_location                    or '',
        'live_indicator_color':              settings.live_indicator_color             or '#FFFFFF',
        'live_indicator_bg_color':           settings.live_indicator_bg_color          or '#CC0000',
        'live_indicator_bg_opacity':         settings.live_indicator_bg_opacity        if settings.live_indicator_bg_opacity is not None else 0.9,
        'live_indicator_font_size':          settings.live_indicator_font_size         or 16,
        'live_indicator_font_family':        settings.live_indicator_font_family,
        'live_indicator_animation':          settings.live_indicator_animation         or 'pulse',
        'live_indicator_vertical_position':  settings.live_indicator_vertical_position or 'top',
        'live_indicator_horizontal_position':settings.live_indicator_horizontal_position or 'left',
        'main_text_color':       settings.main_text_color,
        'main_text_bg_color':    settings.main_text_bg_color    or '#000000',
        'main_text_bg_opacity':  settings.main_text_bg_opacity  if settings.main_text_bg_opacity  is not None else 0.0,
        'secondary_text_color':       settings.secondary_text_color,
        'secondary_text_bg_color':    settings.secondary_text_bg_color    or '#000000',
        'secondary_text_bg_opacity':  settings.secondary_text_bg_opacity  if settings.secondary_text_bg_opacity  is not None else 0.0,
        'ticker_text_color':  settings.ticker_text_color,
        'ticker_bg_color':    settings.ticker_bg_color,
        'ticker_bg_opacity':  settings.ticker_bg_opacity,
        'company_name_color':      settings.company_name_color,
        'company_name_bg_color':   settings.company_name_bg_color   or '#000000',
        'company_name_bg_opacity': settings.company_name_bg_opacity if settings.company_name_bg_opacity is not None else 0.0,
        'footer_text_color': settings.footer_text_color,
        'footer_bg_color': settings.footer_bg_color,
        'footer_bg_opacity': settings.footer_bg_opacity,
        'accent_color': settings.accent_color,
        'border_color': settings.border_color,
        'border_width': settings.border_width,

        # Legacy
        'bg_color': settings.bg_color,
        'text_color': settings.text_color,

        # Font Sizes
        'main_font_size': settings.main_font_size,
        'secondary_font_size': settings.secondary_font_size,
        'ticker_font_size': settings.ticker_font_size or 13,
        'company_name_font_size': settings.company_name_font_size,
        'footer_font_size': settings.footer_font_size,

        'border_radius': settings.border_radius,
        'font_family': settings.font_family,
        'main_font_family': settings.main_font_family,
        'secondary_font_family': settings.secondary_font_family,
        'ticker_font_family': settings.ticker_font_family,
        'company_name_font_family': settings.company_name_font_family,
        'company_name_italic': settings.company_name_italic if settings.company_name_italic is not None else True,
        'ticker_speed': settings.ticker_speed,

        # Logo Settings
        'logo_size': settings.logo_size,
        'logo_opacity': settings.logo_opacity,
        'logo_border_radius': settings.logo_border_radius,
        'logo_shadow': settings.logo_shadow,
        'logo_vertical_position': settings.logo_vertical_position if hasattr(settings, 'logo_vertical_position') else 'top',
        'logo_horizontal_position': settings.logo_horizontal_position if hasattr(settings, 'logo_horizontal_position') else 'right',
        'logo_custom_top': settings.logo_custom_top if hasattr(settings, 'logo_custom_top') else None,
        'logo_custom_bottom': settings.logo_custom_bottom if hasattr(settings, 'logo_custom_bottom') else None,
        'logo_custom_left': settings.logo_custom_left if hasattr(settings, 'logo_custom_left') else None,
        'logo_custom_right': settings.logo_custom_right if hasattr(settings, 'logo_custom_right') else None,

        # Photo / Category Image Container Settings
        'image_size': settings.image_size,
        'image_shape': settings.image_shape,
        'image_border_width': settings.image_border_width,
        'image_border_color': settings.image_border_color,
        'image_position': settings.image_position,
        'image_fit': settings.image_fit,
        'image_object_position': settings.image_object_position or 'center center',
        'image_zoom': settings.image_zoom or 100,

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

        # Display Animations
        'logo_display_animation': settings.logo_display_animation,
        'logo_display_animation_enabled': settings.logo_display_animation_enabled,
        'logo_display_animation_duration': settings.logo_display_animation_duration,
        'logo_display_animation_frequency': settings.logo_display_animation_frequency,
        'image_display_animation': settings.image_display_animation,
        'image_display_animation_enabled': settings.image_display_animation_enabled,
        'image_display_animation_duration': settings.image_display_animation_duration,
        'image_display_animation_frequency': settings.image_display_animation_frequency,

        # Per-section text animations
        'main_text_animation': settings.main_text_animation,
        'secondary_text_animation': settings.secondary_text_animation,
        'company_name_animation': settings.company_name_animation,
        'text_animation_repeat_interval': settings.text_animation_repeat_interval or 0.0,

        # Overlay auto-cycle
        'overlay_cycle_enabled': settings.overlay_cycle_enabled or False,
        'overlay_visible_duration': settings.overlay_visible_duration or 10.0,
        'overlay_hidden_duration': settings.overlay_hidden_duration or 5.0,
        'cycle_entry_animation': settings.cycle_entry_animation or 'fade',
        'cycle_exit_animation':  settings.cycle_exit_animation  or 'fade',
        'cycle_transition_duration': settings.cycle_transition_duration or 0.6,
        # Staggered element entry/exit
        'stagger_enabled':       settings.stagger_enabled or False,
        'stagger_order':         settings.stagger_order or 'main,secondary,company',
        'stagger_delay':         settings.stagger_delay or 0.3,
        'stagger_element_exit':  settings.stagger_element_exit  or 'fade',
        'stagger_element_entry': settings.stagger_element_entry or 'fade',

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