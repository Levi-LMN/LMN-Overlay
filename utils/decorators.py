from functools import wraps
from flask import session, redirect, url_for, flash
from models import User


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            flash('Your account has been deactivated.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def license_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

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
            return redirect(url_for('auth.login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            flash('Your account has been deactivated.', 'error')
            return redirect(url_for('auth.login'))
        if not user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.control'))
        return f(*args, **kwargs)
    return decorated_function