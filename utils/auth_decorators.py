# utils/auth_decorators.py
from functools import wraps
from flask import session, redirect, flash, jsonify

def login_required(f):
    """Decorator to restrict routes to fully logged-in users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def auth_required(f):
    """Decorator to restrict routes to authenticated users or shared view-only sessions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session and not session.get('view_only'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def api_login_required(f):
    """Decorator to restrict APIs to fully logged-in users, returning 401 JSON error on failure."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def api_auth_required(f):
    """Decorator to restrict APIs to authenticated users or shared view-only sessions, returning 401 JSON on failure."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session and not session.get('view_only'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function
