from flask import Blueprint, request, jsonify, render_template, current_app, session
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, OCRImage, OCRSession, OverlaySettings
from services.ocr_service import OCRService
from utils.decorators import login_required
import os

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')
ocr_service = OCRService()


@ocr_bp.route('/')
@login_required
def index():
    """OCR management page"""
    sessions = OCRSession.query.order_by(OCRSession.created_at.desc()).all()
    categories = ['funeral', 'wedding', 'ceremony', 'general']
    return render_template('ocr/index.html', sessions=sessions, categories=categories)


@ocr_bp.route('/session/create', methods=['POST'])
@login_required
def create_session():
    """Create a new OCR session"""
    data = request.form
    name = data.get('name', f'OCR Session {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    category = data.get('category', 'general')

    session_obj = OCRSession(
        name=name,
        category=category,
        status='active'
    )

    db.session.add(session_obj)
    db.session.commit()

    return jsonify({
        'success': True,
        'session': session_obj.to_dict()
    })


@ocr_bp.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """View OCR session details"""
    session_obj = OCRSession.query.get_or_404(session_id)
    images = OCRImage.query.filter_by(session_id=session_id).order_by(OCRImage.order_index).all()
    categories = ['funeral', 'wedding', 'ceremony', 'general']

    return render_template('ocr/session.html',
                           session=session_obj,
                           images=images,
                           categories=categories)


@ocr_bp.route('/upload/<int:session_id>', methods=['POST'])
@login_required
def upload_images(session_id):
    """Upload images to an OCR session"""
    session_obj = OCRSession.query.get_or_404(session_id)

    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    uploaded_images = []

    # Get current max order index
    max_order = db.session.query(db.func.max(OCRImage.order_index)) \
                    .filter_by(session_id=session_id).scalar() or -1

    for idx, file in enumerate(files):
        if file.filename == '':
            continue

        if file:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"ocr_{session_id}_{timestamp}_{idx}_{filename}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            ocr_image = OCRImage(
                filename=filename,
                filepath=f"uploads/{filename}",
                order_index=max_order + idx + 1,
                session_id=session_id,
                category=session_obj.category,
                status='pending'
            )

            db.session.add(ocr_image)
            uploaded_images.append(ocr_image)

    session_obj.image_count = OCRImage.query.filter_by(session_id=session_id).count()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{len(uploaded_images)} images uploaded',
        'images': [img.to_dict() for img in uploaded_images]
    })


@ocr_bp.route('/process/<int:session_id>', methods=['POST'])
@login_required
def process_session(session_id):
    """Process all images in a session with enhanced OCR"""
    session_obj = OCRSession.query.get_or_404(session_id)
    images = OCRImage.query.filter_by(session_id=session_id) \
        .order_by(OCRImage.order_index).all()

    if not images:
        return jsonify({'error': 'No images to process'}), 400

    # Get processing options
    data = request.get_json() if request.is_json else {}
    lang = data.get('language', 'en')  # Changed from 'eng' to 'en' for Google Vision
    use_multiple_strategies = data.get('use_multiple_strategies', True)

    results = []
    combined_text_parts = []

    for image in images:
        image.status = 'processing'
        db.session.commit()

        # Construct full path
        full_path = os.path.join(current_app.root_path, 'static', image.filepath)

        try:
            # Perform OCR with enhanced processing
            if use_multiple_strategies:
                result = ocr_service.extract_text_with_multiple_strategies(full_path, lang=lang)
            else:
                result = ocr_service.extract_text_from_image(full_path, lang=lang, preprocessing='basic')

            # Check if result has the expected structure
            if not isinstance(result, dict):
                result = {
                    'success': False,
                    'text': '',
                    'confidence': 0,
                    'error': 'Invalid result format'
                }

            if result.get('success') and result.get('text'):
                image.extracted_text = ocr_service.clean_text(result['text'])
                image.status = 'completed'
                combined_text_parts.append(image.extracted_text)
            else:
                image.status = 'failed'
                image.error_message = result.get('error', 'No text extracted')

            image.updated_at = datetime.utcnow()
            db.session.commit()

            results.append({
                'image_id': image.id,
                'filename': image.filename,
                'status': image.status,
                'text': image.extracted_text,
                'confidence': result.get('confidence', 0),
                'strategy': result.get('strategy', 'unknown'),
                'error': result.get('error', None)
            })

        except Exception as e:
            # Handle any unexpected errors
            image.status = 'failed'
            image.error_message = str(e)
            image.updated_at = datetime.utcnow()
            db.session.commit()

            results.append({
                'image_id': image.id,
                'filename': image.filename,
                'status': 'failed',
                'text': '',
                'confidence': 0,
                'strategy': 'error',
                'error': str(e)
            })

    # Combine all text
    session_obj.combined_text = '\n\n'.join(combined_text_parts)
    session_obj.status = 'completed'
    session_obj.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'OCR processing completed',
        'combined_text': session_obj.combined_text,
        'results': results
    })


@ocr_bp.route('/reorder/<int:session_id>', methods=['POST'])
@login_required
def reorder_images(session_id):
    """Reorder images in a session"""
    session_obj = OCRSession.query.get_or_404(session_id)
    data = request.get_json()

    image_order = data.get('order', [])  # List of image IDs in new order

    for idx, image_id in enumerate(image_order):
        image = OCRImage.query.get(image_id)
        if image and image.session_id == session_id:
            image.order_index = idx
            image.updated_at = datetime.utcnow()

    db.session.commit()

    # Reprocess combined text with new order
    images = OCRImage.query.filter_by(session_id=session_id) \
        .order_by(OCRImage.order_index).all()

    combined_text_parts = [img.extracted_text for img in images
                           if img.extracted_text and img.status == 'completed']
    session_obj.combined_text = '\n\n'.join(combined_text_parts)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Images reordered successfully',
        'combined_text': session_obj.combined_text
    })


@ocr_bp.route('/image/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_image(image_id):
    """Delete an image from OCR session"""
    image = OCRImage.query.get_or_404(image_id)
    session_id = image.session_id

    # Delete file from disk
    try:
        full_path = os.path.join(current_app.root_path, 'static', image.filepath)
        if os.path.exists(full_path):
            os.remove(full_path)
    except Exception as e:
        current_app.logger.error(f"Error deleting file: {str(e)}")

    db.session.delete(image)

    # Update session image count
    session_obj = OCRSession.query.get(session_id)
    if session_obj:
        session_obj.image_count = OCRImage.query.filter_by(session_id=session_id).count()

    db.session.commit()

    return jsonify({'success': True, 'message': 'Image deleted'})


@ocr_bp.route('/session/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    """Delete an entire OCR session"""
    session_obj = OCRSession.query.get_or_404(session_id)

    # Delete all associated images
    images = OCRImage.query.filter_by(session_id=session_id).all()
    for image in images:
        try:
            full_path = os.path.join(current_app.root_path, 'static', image.filepath)
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception as e:
            current_app.logger.error(f"Error deleting file: {str(e)}")

        db.session.delete(image)

    db.session.delete(session_obj)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Session deleted'})


@ocr_bp.route('/session/<int:session_id>/apply-to-ticker', methods=['POST'])
@login_required
def apply_to_ticker(session_id):
    """Apply extracted text to ticker for a category"""
    session_obj = OCRSession.query.get_or_404(session_id)
    data = request.get_json()

    category = data.get('category', session_obj.category)

    if not session_obj.combined_text:
        return jsonify({'error': 'No text to apply'}), 400

    # Get overlay settings for category
    settings = OverlaySettings.query.filter_by(category=category).first()
    if not settings:
        settings = OverlaySettings(category=category)
        db.session.add(settings)

    # Apply text to ticker
    settings.ticker_text = session_obj.combined_text
    settings.updated_at = datetime.utcnow()

    # Mark session as used
    session_obj.used_in_ticker = True
    session_obj.updated_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Text applied to {category} ticker',
        'ticker_text': settings.ticker_text
    })


@ocr_bp.route('/session/<int:session_id>/edit-text', methods=['POST'])
@login_required
def edit_combined_text(session_id):
    """Edit the combined text of a session"""
    session_obj = OCRSession.query.get_or_404(session_id)
    data = request.get_json()

    session_obj.combined_text = data.get('text', '')
    session_obj.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Text updated successfully',
        'text': session_obj.combined_text
    })


@ocr_bp.route('/languages')
@login_required
def get_languages():
    """Get available OCR languages"""
    languages = ocr_service.get_supported_languages()
    return jsonify({'languages': languages})


@ocr_bp.route('/image/<int:image_id>/reprocess', methods=['POST'])
@login_required
def reprocess_single_image(image_id):
    """Reprocess a single image with different settings"""
    image = OCRImage.query.get_or_404(image_id)
    data = request.get_json() if request.is_json else {}

    lang = data.get('language', 'en')
    preprocessing = data.get('preprocessing', 'basic')

    # Construct full path
    full_path = os.path.join(current_app.root_path, 'static', image.filepath)

    try:
        # Perform OCR
        result = ocr_service.extract_text_from_image(full_path, lang=lang, preprocessing=preprocessing)

        if not isinstance(result, dict):
            result = {
                'success': False,
                'text': '',
                'confidence': 0,
                'error': 'Invalid result format'
            }

        if result.get('success') and result.get('text'):
            image.extracted_text = ocr_service.clean_text(result['text'])
            image.status = 'completed'
        else:
            image.status = 'failed'
            image.error_message = result.get('error', 'No text extracted')

        image.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': result.get('success', False),
            'text': image.extracted_text,
            'confidence': result.get('confidence', 0),
            'message': 'Image reprocessed'
        })

    except Exception as e:
        image.status = 'failed'
        image.error_message = str(e)
        image.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': False,
            'text': '',
            'confidence': 0,
            'error': str(e)
        }), 500