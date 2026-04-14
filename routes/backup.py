"""
Backup & Restore routes for OverlaySettings.

Export  →  GET  /backup/export?categories=funeral,wedding,ceremony
              Downloads a JSON file with all customisation fields.

Import  →  POST /backup/import
              Accepts a JSON file upload and restores settings.
              Skips file-path fields (company_logo, category_image) —
              those files must be re-uploaded manually.
"""

from flask import (
    Blueprint, request, jsonify, render_template,
    session, Response, flash, redirect, url_for
)
from datetime import datetime
from models import db, OverlaySettings
from utils.decorators import login_required, admin_required
import json

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

# Fields that are file paths on disk — we export them for reference
# but skip writing them back on import (files must be re-uploaded separately).
_FILE_PATH_FIELDS = {'company_logo', 'category_image'}

# All scalar fields on OverlaySettings that are safe to serialise / restore.
# Keeps the order readable; mirrors the model definition.
_EXPORTABLE_FIELDS = [
    # Content
    'category', 'main_text', 'secondary_text', 'secondary_phrases',
    'ticker_text', 'company_name', 'company_logo', 'category_image',
    'show_category_image', 'show_company_logo', 'show_ticker',

    # Secondary text rotation
    'secondary_rotation_enabled', 'secondary_display_duration',
    'secondary_transition_type', 'secondary_transition_duration',

    # Overlay position & size
    'vertical_position', 'horizontal_position',
    'custom_top', 'custom_bottom', 'custom_left', 'custom_right',
    'container_width', 'custom_width', 'container_max_width',
    'container_min_width', 'container_height', 'custom_height',
    'container_padding',

    # Text scaling
    'text_scale_mode', 'text_line_height', 'text_max_lines',
    'enable_text_truncation',

    # Overlay background
    'overlay_bg_color', 'overlay_bg_opacity',

    # Sectioned background
    'overlay_bg_sections_enabled',
    'overlay_bg_top_color', 'overlay_bg_top_opacity', 'overlay_bg_top_height',
    'overlay_bg_bottom_color', 'overlay_bg_bottom_opacity', 'overlay_bg_bottom_height',

    # Clock
    'show_clock', 'clock_format', 'clock_show_time', 'clock_font_size',
    'clock_font_family', 'clock_color', 'clock_bg_color', 'clock_bg_opacity',
    'clock_animation', 'clock_position',

    # Live indicator
    'show_live_indicator', 'live_label', 'live_location',
    'live_indicator_color', 'live_indicator_bg_color', 'live_indicator_bg_opacity',
    'live_indicator_font_size', 'live_indicator_font_family',
    'live_indicator_animation', 'live_indicator_vertical_position',
    'live_indicator_horizontal_position',

    # Live label & location — per-part colours
    'live_label_color', 'live_label_bg_color', 'live_label_bg_opacity',
    'live_location_color', 'live_location_bg_color', 'live_location_bg_opacity',

    # Colors — main text
    'main_text_color', 'main_text_bg_color', 'main_text_bg_opacity',

    # Colors — secondary text
    'secondary_text_color', 'secondary_text_bg_color', 'secondary_text_bg_opacity',

    # Colors — ticker
    'ticker_text_color', 'ticker_bg_color', 'ticker_bg_opacity',

    # Colors — company name
    'company_name_color', 'company_name_bg_color', 'company_name_bg_opacity',

    # Colors — footer
    'footer_text_color', 'footer_bg_color', 'footer_bg_opacity',

    # Accent / border
    'accent_color', 'border_color', 'border_width',

    # Legacy colors
    'bg_color', 'text_color',

    # Font sizes
    'main_font_size', 'secondary_font_size', 'ticker_font_size',
    'company_name_font_size', 'footer_font_size', 'border_radius',

    # Font families
    'font_family', 'main_font_family', 'secondary_font_family',
    'ticker_font_family', 'company_name_font_family',
    'company_name_italic', 'ticker_speed',

    # Logo appearance
    'logo_size', 'logo_opacity', 'logo_border_radius', 'logo_shadow',

    # Logo position
    'logo_vertical_position', 'logo_horizontal_position',
    'logo_custom_top', 'logo_custom_bottom',
    'logo_custom_left', 'logo_custom_right',

    # Category image
    'image_size', 'image_shape', 'image_border_width', 'image_border_color',
    'image_position', 'image_fit', 'image_object_position', 'image_zoom',

    # Layout
    'layout_style', 'show_decorative_elements', 'opacity',

    # Entrance animations
    'entrance_animation', 'entrance_duration', 'entrance_delay',
    'text_animation', 'text_animation_speed',
    'image_animation', 'image_animation_delay',
    'logo_animation', 'logo_animation_delay',
    'ticker_entrance', 'ticker_entrance_delay',

    # Display animations
    'logo_display_animation', 'logo_display_animation_enabled',
    'logo_display_animation_duration', 'logo_display_animation_frequency',
    'image_display_animation', 'image_display_animation_enabled',
    'image_display_animation_duration', 'image_display_animation_frequency',

    # Per-section text animations
    'main_text_animation', 'secondary_text_animation', 'company_name_animation',
    'text_animation_repeat_interval',

    # Overlay auto-cycle
    'overlay_cycle_enabled', 'overlay_visible_duration', 'overlay_hidden_duration',
    'cycle_entry_animation', 'cycle_exit_animation', 'cycle_transition_duration',

    # Stagger
    'stagger_enabled', 'stagger_order', 'stagger_delay',
    'stagger_element_exit', 'stagger_element_entry',

    # Visibility
    'is_visible',
]


def _settings_to_dict(settings: OverlaySettings) -> dict:
    """Serialise a single OverlaySettings row to a plain dict."""
    out = {}
    for field in _EXPORTABLE_FIELDS:
        out[field] = getattr(settings, field, None)
    return out


def _restore_settings(settings: OverlaySettings, data: dict, skip_files: bool = True) -> list[str]:
    """
    Write values from *data* back onto *settings*.

    Returns a list of warning strings (e.g. skipped file paths).
    """
    warnings = []
    for field in _EXPORTABLE_FIELDS:
        if field == 'category':       # never overwrite the category key
            continue
        if field not in data:
            continue

        if skip_files and field in _FILE_PATH_FIELDS:
            existing = getattr(settings, field, None)
            imported = data[field]
            if imported and imported != existing:
                warnings.append(
                    f"'{field}' was not restored (had value: {imported!r}). "
                    f"Please re-upload the file manually."
                )
            continue

        setattr(settings, field, data[field])

    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@backup_bp.route('/')
@login_required
def index():
    """Render the backup / restore page."""
    all_categories = OverlaySettings.query.with_entities(
        OverlaySettings.category
    ).distinct().order_by(OverlaySettings.category).all()
    categories = [row.category for row in all_categories]
    if not categories:
        categories = ['funeral', 'wedding', 'ceremony']
    return render_template('backup.html', categories=categories)


@backup_bp.route('/export')
@login_required
def export_settings():
    """
    Export one or more categories as a downloadable JSON file.

    Query params:
        categories  – comma-separated list, e.g. funeral,wedding
                      Omit (or use 'all') to export everything.
    """
    raw = request.args.get('categories', 'all').strip()
    if raw == 'all' or not raw:
        settings_rows = OverlaySettings.query.all()
    else:
        requested = [c.strip() for c in raw.split(',') if c.strip()]
        settings_rows = OverlaySettings.query.filter(
            OverlaySettings.category.in_(requested)
        ).all()

    if not settings_rows:
        return jsonify({'error': 'No matching categories found.'}), 404

    payload = {
        'exported_at': datetime.utcnow().isoformat() + 'Z',
        'version': '1.0',
        'categories': [_settings_to_dict(s) for s in settings_rows],
    }

    json_bytes = json.dumps(payload, indent=2, default=str).encode('utf-8')

    filename_parts = [s.category for s in settings_rows]
    filename = (
        f"overlay_backup_{'_'.join(filename_parts)}"
        f"_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    )

    # Use Response directly — avoids io.UnsupportedOperation: fileno
    # which occurs when send_file() calls .fileno() on a BytesIO object
    # under Passenger/WSGI environments.
    return Response(
        json_bytes,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': str(len(json_bytes)),
        }
    )


@backup_bp.route('/import', methods=['POST'])
@login_required
def import_settings():
    """
    Restore settings from an uploaded JSON backup file.

    Form fields:
        file            – the .json backup file
        overwrite_mode  – 'merge' (default) or 'replace'
                          merge  → only imported fields overwrite existing ones
                          replace → full replacement (same as merge for us; kept for UX clarity)
        categories      – optional comma-separated list to limit which categories to restore
    """
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({'success': False, 'error': 'No file uploaded.'}), 400

    f = request.files['file']
    try:
        raw_json = f.read().decode('utf-8')
        payload = json.loads(raw_json)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Invalid JSON file: {e}'}), 400

    # Validate structure
    if 'categories' not in payload or not isinstance(payload['categories'], list):
        return jsonify({
            'success': False,
            'error': 'Unrecognised backup format — missing "categories" array.'
        }), 400

    # Optional category filter
    filter_raw = request.form.get('categories', '').strip()
    filter_cats = set(c.strip() for c in filter_raw.split(',') if c.strip()) if filter_raw else set()

    restored = []
    skipped = []
    all_warnings = []

    for cat_data in payload['categories']:
        category = cat_data.get('category')
        if not category:
            skipped.append('(unknown — missing category field)')
            continue

        if filter_cats and category not in filter_cats:
            skipped.append(category)
            continue

        settings = OverlaySettings.query.filter_by(category=category).first()
        if not settings:
            settings = OverlaySettings(category=category)
            db.session.add(settings)

        warnings = _restore_settings(settings, cat_data, skip_files=True)
        settings.updated_at = datetime.utcnow()
        all_warnings.extend([f'[{category}] {w}' for w in warnings])
        restored.append(category)

    db.session.commit()

    return jsonify({
        'success': True,
        'restored': restored,
        'skipped': skipped,
        'warnings': all_warnings,
        'message': (
            f"Restored {len(restored)} categor{'y' if len(restored)==1 else 'ies'}: "
            f"{', '.join(restored)}."
            + (f" Skipped: {', '.join(skipped)}." if skipped else '')
        )
    })


@backup_bp.route('/export/single/<category>')
@login_required
def export_single(category):
    """Convenience shortcut — export a single category."""
    return redirect(url_for('backup.export_settings', categories=category))