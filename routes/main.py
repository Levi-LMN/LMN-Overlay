from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from datetime import datetime
from models import db, User, OverlaySettings
from utils.decorators import login_required, license_required, admin_required
import os

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('main.control'))
    return redirect(url_for('auth.login'))


@main_bp.route('/control')
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


@main_bp.route('/customize/<category>')
@login_required
@license_required
def customize(category):
    """Detailed customization page for a specific category"""
    if category not in ['funeral', 'wedding', 'ceremony']:
        flash('Invalid category', 'error')
        return redirect(url_for('main.control'))

    settings = OverlaySettings.query.filter_by(category=category).first()
    if not settings:
        settings = OverlaySettings(category=category)
        db.session.add(settings)
        db.session.commit()

    current_user = User.query.get(session['user_id'])

    # Category display names
    category_names = {
        'funeral': 'Funeral',
        'wedding': 'Wedding',
        'ceremony': 'Ceremony'
    }

    return render_template('customize.html',
                           settings=settings,
                           category=category,
                           category_name=category_names.get(category, category.capitalize()),
                           current_user=current_user)


@main_bp.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    current_user = User.query.get(session['user_id'])

    # Convert users to dictionaries for JSON serialization
    users_dict = [user.to_dict() for user in all_users]

    return render_template('users.html', users=all_users, users_json=users_dict, current_user=current_user)


@main_bp.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    data = request.form
    email = data.get('email', '').lower().strip()
    password = data.get('password')
    full_name = data.get('full_name', '').strip()
    is_admin = data.get('is_admin') == 'on'

    if not email or not password:
        flash('Email and password are required.', 'error')
        return redirect(url_for('main.users'))

    existing_user = User.query.filter(User.email.ilike(email)).first()
    if existing_user:
        flash('A user with this email already exists.', 'error')
        return redirect(url_for('main.users'))

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
    return redirect(url_for('main.users'))


@main_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.form

    from flask import current_app
    protected_admin_email = current_app.config['ADMIN_EMAIL'].lower()

    if user.email.lower() == protected_admin_email:
        flash(f'The super admin account ({protected_admin_email}) cannot be modified.', 'error')
        return redirect(url_for('main.users'))

    if user.is_admin and data.get('is_admin') != 'on':
        admin_count = User.query.filter_by(is_admin=True, is_active=True).count()
        if admin_count <= 1:
            flash('Cannot remove admin privileges from the last active administrator.', 'error')
            return redirect(url_for('main.users'))

    email = data.get('email', '').lower().strip()
    full_name = data.get('full_name', '').strip()
    is_admin = data.get('is_admin') == 'on'
    password = data.get('password', '').strip()

    if not email:
        flash('Email is required.', 'error')
        return redirect(url_for('main.users'))

    existing_user = User.query.filter(User.email.ilike(email), User.id != user_id).first()
    if existing_user:
        flash('Email already in use by another user.', 'error')
        return redirect(url_for('main.users'))

    user.email = email
    user.full_name = full_name
    user.is_admin = is_admin
    user.updated_at = datetime.utcnow()

    if password:
        user.password_hash = generate_password_hash(password)

    db.session.commit()
    flash(f'User {email} updated successfully!', 'success')
    return redirect(url_for('main.users'))


@main_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)

    from flask import current_app
    protected_admin_email = current_app.config['ADMIN_EMAIL'].lower()

    if user.email.lower() == protected_admin_email:
        flash(f'The super admin account ({protected_admin_email}) cannot be deactivated.', 'error')
        return redirect(url_for('main.users'))

    if user.id == session['user_id']:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('main.users'))

    if user.is_admin and user.is_active:
        admin_count = User.query.filter_by(is_admin=True, is_active=True).count()
        if admin_count <= 1:
            flash('Cannot deactivate the last active administrator.', 'error')
            return redirect(url_for('main.users'))

    user.is_active = not user.is_active
    user.updated_at = datetime.utcnow()
    db.session.commit()

    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.email} {status} successfully!', 'success')
    return redirect(url_for('main.users'))


@main_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    from flask import current_app
    protected_admin_email = current_app.config['ADMIN_EMAIL'].lower()

    if user.email.lower() == protected_admin_email:
        flash(f'The super admin account ({protected_admin_email}) cannot be deleted.', 'error')
        return redirect(url_for('main.users'))

    if user.id == session['user_id']:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('main.users'))

    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash('Cannot delete the last administrator.', 'error')
            return redirect(url_for('main.users'))

    email = user.email
    db.session.delete(user)
    db.session.commit()
    flash(f'User {email} deleted successfully!', 'success')
    return redirect(url_for('main.users'))


@main_bp.route('/display')
def display():
    category = request.args.get('category', 'funeral')
    settings = OverlaySettings.query.filter_by(category=category).first()

    if not settings:
        settings = OverlaySettings(category=category)
        db.session.add(settings)
        db.session.commit()

    # Convert settings to dictionary for JSON serialization
    from routes.api import settings_to_dict
    settings_dict = settings_to_dict(settings)

    template_map = {
        'funeral': 'display_funeral.html',
        'wedding': 'display_wedding.html',
        'ceremony': 'display_ceremony.html'
    }

    template = template_map.get(category, 'display_funeral.html')
    return render_template(template, settings=settings_dict, category=category)