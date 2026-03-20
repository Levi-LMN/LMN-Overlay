"""
File Manager routes.

GET  /files/             → render the file manager page
GET  /files/list         → JSON list of all files in static/uploads/
POST /files/upload       → upload one or more files (no category assignment yet)
POST /files/delete       → delete a file from disk + clear any DB references
POST /files/assign       → assign an existing file to a category as logo or image
"""

from flask import (
    Blueprint, request, jsonify, render_template,
    current_app, url_for
)
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, OverlaySettings
from utils.decorators import login_required
from PIL import Image as PILImage
import os

files_bp = Blueprint('files', __name__, url_prefix='/files')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'}


THUMB_SUFFIX   = '_thumb'
THUMB_SIZE     = (400, 260)   # max dimensions — fast to load, still looks sharp on retina
THUMB_QUALITY  = 72           # JPEG quality for thumbnails


def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _make_thumbnail(src_path: str, thumb_path: str) -> bool:
    """
    Generate a JPEG thumbnail from *src_path* and save to *thumb_path*.
    Returns True on success, False if anything goes wrong (caller falls back
    to serving the original).
    """
    try:
        with PILImage.open(src_path) as img:
            # Preserve orientation from EXIF if present
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            elif img.mode == 'RGBA':
                # Flatten alpha onto white background so JPEG is clean
                bg = PILImage.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            else:
                img = img.convert('RGB')

            img.thumbnail(THUMB_SIZE, PILImage.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=THUMB_QUALITY, optimize=True)
        return True
    except Exception:
        return False


def _upload_dir():
    return os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])


def _build_file_list():
    """
    Scan static/uploads/ and return metadata for every image file.
    Also annotates each file with which category / slot it is currently
    assigned to (logo, image, or none).
    """
    upload_dir = _upload_dir()
    os.makedirs(upload_dir, exist_ok=True)

    # Build a lookup: relative_path → {category, slot}
    assignments = {}
    for settings in OverlaySettings.query.all():
        if settings.company_logo:
            assignments[settings.company_logo] = {
                'category': settings.category,
                'slot': 'logo'
            }
        if settings.category_image:
            assignments[settings.category_image] = {
                'category': settings.category,
                'slot': 'image'
            }

    files = []
    try:
        entries = sorted(os.scandir(upload_dir), key=lambda e: e.stat().st_mtime, reverse=True)
    except FileNotFoundError:
        entries = []

    for entry in entries:
        if not entry.is_file():
            continue
        ext = entry.name.rsplit('.', 1)[-1].lower() if '.' in entry.name else ''
        if ext not in ALLOWED_EXTENSIONS:
            continue
        # Skip thumbnail files — they're internal, not user files
        name_stem = entry.name.rsplit('.', 1)[0]
        if name_stem.endswith(THUMB_SUFFIX):
            continue

        stat       = entry.stat()
        rel_path   = f"uploads/{entry.name}"
        assignment = assignments.get(rel_path)

        # Derive thumbnail path — thumb lives alongside the original with _thumb suffix
        name_no_ext  = entry.name.rsplit('.', 1)[0]
        thumb_name   = name_no_ext + THUMB_SUFFIX + '.jpg'
        thumb_path   = os.path.join(upload_dir, thumb_name)
        thumb_rel    = f"uploads/{thumb_name}"

        # Generate thumbnail on-the-fly if it doesn't exist yet
        if not os.path.isfile(thumb_path):
            _make_thumbnail(entry.path, thumb_path)

        thumb_url = (
            url_for('static', filename=thumb_rel)
            if os.path.isfile(thumb_path)
            else url_for('static', filename=rel_path)   # fallback to original
        )

        files.append({
            'filename':    entry.name,
            'rel_path':    rel_path,
            'url':         url_for('static', filename=rel_path),
            'thumb_url':   thumb_url,
            'size_kb':     round(stat.st_size / 1024, 1),
            'modified':    datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
            'ext':         ext,
            'assigned_to': assignment,
        })

    return files


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@files_bp.route('/')
@login_required
def index():
    categories = ['funeral', 'wedding', 'ceremony']
    return render_template('files.html', categories=categories)


@files_bp.route('/list')
@login_required
def list_files():
    files = _build_file_list()
    total_bytes = sum(
        os.path.getsize(os.path.join(_upload_dir(), f['filename']))
        for f in files
        if os.path.isfile(os.path.join(_upload_dir(), f['filename']))
        and not f['filename'].rsplit('.', 1)[0].endswith(THUMB_SUFFIX)
    )
    return jsonify({
        'success':     True,
        'files':       files,
        'total_bytes': total_bytes,
        'total_kb':    round(total_bytes / 1024, 1),
        'total_mb':    round(total_bytes / (1024 * 1024), 2),
    })


@files_bp.route('/delete-bulk', methods=['POST'])
@login_required
def delete_bulk():
    """
    Delete multiple files in one request.

    Body JSON: { "filenames": ["a.jpg", "b.png", ...] }
    """
    data      = request.get_json(silent=True) or {}
    filenames = data.get('filenames', [])

    if not filenames or not isinstance(filenames, list):
        return jsonify({'success': False, 'error': 'Provide a list of filenames'}), 400

    upload_dir  = _upload_dir()
    deleted     = []
    failed      = []
    all_cleared = []

    for filename in filenames:
        filename = str(filename).strip()
        if not filename or '/' in filename or '..' in filename:
            failed.append({'filename': filename, 'error': 'Invalid filename'})
            continue

        full_path = os.path.join(upload_dir, filename)
        rel_path  = f"uploads/{filename}"

        if not os.path.isfile(full_path):
            failed.append({'filename': filename, 'error': 'Not found'})
            continue

        # Clear DB assignments
        for settings in OverlaySettings.query.all():
            changed = False
            if settings.company_logo == rel_path:
                settings.company_logo      = None
                settings.show_company_logo = False
                changed = True
                all_cleared.append(f"{settings.category} logo")
            if settings.category_image == rel_path:
                settings.category_image      = None
                settings.show_category_image = False
                changed = True
                all_cleared.append(f"{settings.category} image")
            if changed:
                settings.updated_at = datetime.utcnow()

        try:
            os.remove(full_path)
            # Also remove thumbnail
            name_no_ext = filename.rsplit('.', 1)[0]
            thumb_path  = os.path.join(upload_dir, name_no_ext + THUMB_SUFFIX + '.jpg')
            if os.path.isfile(thumb_path):
                os.remove(thumb_path)
            deleted.append(filename)
        except OSError as e:
            failed.append({'filename': filename, 'error': str(e)})

    db.session.commit()

    msg = f"{len(deleted)} file(s) deleted."
    if all_cleared:
        msg += f" Cleared assignments: {', '.join(all_cleared)}."
    if failed:
        msg += f" {len(failed)} could not be deleted."

    return jsonify({
        'success': True,
        'deleted': deleted,
        'failed':  failed,
        'cleared': all_cleared,
        'message': msg,
    })


@files_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """Upload one or more image files — no category assignment."""
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'No files provided'}), 400

    upload_dir = _upload_dir()
    os.makedirs(upload_dir, exist_ok=True)

    saved = []
    errors = []

    for file in request.files.getlist('files'):
        if file.filename == '':
            continue
        if not _allowed(file.filename):
            errors.append(f"{file.filename}: unsupported type")
            continue

        original = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]
        filename  = f"fm_{timestamp}_{original}"
        filepath  = os.path.join(upload_dir, filename)
        file.save(filepath)
        # Generate thumbnail immediately so the grid loads fast
        thumb_name = f"fm_{timestamp}_{original.rsplit('.',1)[0]}{THUMB_SUFFIX}.jpg"
        thumb_path = os.path.join(upload_dir, thumb_name)
        _make_thumbnail(filepath, thumb_path)
        saved.append(filename)

    return jsonify({
        'success': True,
        'saved':  saved,
        'errors': errors,
        'message': f"{len(saved)} file(s) uploaded."
                   + (f" {len(errors)} skipped." if errors else '')
    })


@files_bp.route('/delete', methods=['POST'])
@login_required
def delete_file():
    """
    Delete a file from disk and clear any category assignments that
    point to it.

    Body JSON: { "filename": "the_file.jpg" }
    """
    data     = request.get_json(silent=True) or {}
    filename = data.get('filename', '').strip()

    if not filename or '/' in filename or '..' in filename:
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400

    upload_dir = _upload_dir()
    full_path  = os.path.join(upload_dir, filename)
    rel_path   = f"uploads/{filename}"

    if not os.path.isfile(full_path):
        return jsonify({'success': False, 'error': 'File not found'}), 404

    # Clear any DB assignments before deleting from disk
    cleared = []
    for settings in OverlaySettings.query.all():
        changed = False
        if settings.company_logo == rel_path:
            settings.company_logo     = None
            settings.show_company_logo = False
            changed = True
            cleared.append(f"{settings.category} logo")
        if settings.category_image == rel_path:
            settings.category_image     = None
            settings.show_category_image = False
            changed = True
            cleared.append(f"{settings.category} image")
        if changed:
            settings.updated_at = datetime.utcnow()

    db.session.commit()

    try:
        os.remove(full_path)
        # Also remove the thumbnail if it exists
        name_no_ext = filename.rsplit('.', 1)[0]
        thumb_path  = os.path.join(upload_dir, name_no_ext + THUMB_SUFFIX + '.jpg')
        if os.path.isfile(thumb_path):
            os.remove(thumb_path)
    except OSError as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    msg = f"'{filename}' deleted."
    if cleared:
        msg += f" Cleared assignments: {', '.join(cleared)}."

    return jsonify({'success': True, 'message': msg, 'cleared': cleared})


@files_bp.route('/assign', methods=['POST'])
@login_required
def assign_file():
    """
    Point a category's logo or image slot at an already-uploaded file.

    Body JSON:
        {
            "filename":  "the_file.jpg",
            "category":  "funeral",
            "slot":      "logo"   |  "image"
        }
    """
    data     = request.get_json(silent=True) or {}
    filename = data.get('filename', '').strip()
    category = data.get('category', '').strip()
    slot     = data.get('slot', '').strip()

    if not filename or not category or slot not in ('logo', 'image'):
        return jsonify({'success': False, 'error': 'filename, category and slot (logo|image) required'}), 400

    if '/' in filename or '..' in filename:
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400

    upload_dir = _upload_dir()
    full_path  = os.path.join(upload_dir, filename)
    if not os.path.isfile(full_path):
        return jsonify({'success': False, 'error': 'File not found on disk'}), 404

    settings = OverlaySettings.query.filter_by(category=category).first()
    if not settings:
        settings = OverlaySettings(category=category)
        db.session.add(settings)

    rel_path = f"uploads/{filename}"

    if slot == 'logo':
        settings.company_logo      = rel_path
        settings.show_company_logo = True
    else:
        settings.category_image      = rel_path
        settings.show_category_image = True

    settings.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success':  True,
        'message':  f"'{filename}' assigned as {slot} for {category}.",
        'rel_path': rel_path,
    })