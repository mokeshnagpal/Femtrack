from flask import Flask, render_template, request, redirect, session, jsonify, flash
from config import db, ADMIN_USERS, VIEW_PASS, DEFAULT_PASS
from utils.auth import hash_password, check_password
from utils.auth_decorators import login_required, auth_required, api_login_required, api_auth_required
from utils.email_service import send_otp
from utils.otp import generate_otp, validate_otp
from utils.date_helpers import format_date_readable, parse_entry_date, sort_entries_by_date, normalize_entry_for_charts
from utils.firestore_service import (
    get_user_settings, update_user_settings, get_period_entries, 
    get_weight_height_entries, get_latest_weight_height, get_sex_entries, get_latest_sex_entries
)
from utils.biometrics import (
    calculate_bmi, get_bmi_category, get_weight_analytics, 
    get_height_analytics, get_bmi_analytics
)
from utils.fertility import calculate_fertility_analytics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from google.cloud.firestore import FieldFilter
import os

import math
import random

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize Flask app with explicit static and template paths
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'static'),
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_url_path='/static'
)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Register Jinja2 filter for cycle phase colors
def get_day_color(phase, is_past=False, is_predicted=False):
    """Return color for a given cycle phase"""
    colors = {
        'menstruation': {'current': '#dc3545', 'past': '#f8d7da'},
        'follicular': {'current': '#c05621', 'past': '#f3dfd3'},
        'ovulation': {'current': '#ffc107', 'past': '#fff3cd'},
        'luteal': {'current': '#198754', 'past': '#d1e7dd'}
    }
    
    if is_predicted:
        return colors.get(phase, {}).get('past', '#e9ecef')
    
    return colors.get(phase, {}).get('past' if is_past else 'current', '#e9ecef')

app.jinja_env.filters['get_day_color'] = get_day_color

# Register date formatting filter for Jinja2
app.jinja_env.filters['format_date'] = format_date_readable

DEFAULT_SEX_TYPES = [
    'Soft',
    'Hard (Protected)',
    'Hard (Pullout)',
    'Hard (Natural)'
]
DEFAULT_SEX_POSITIONS = [
    'Missionary',
    'Cowgirl',
    'Doggy',
    'Side',
    'Standing'
]

def build_sex_options(user_data):
    """Build sex-entry option lists from defaults plus user customizations."""
    user_data = user_data or {}
    custom_types = user_data.get('custom_sex_types', [])
    custom_positions = user_data.get('custom_sex_positions', [])
    sex_types = list(dict.fromkeys(DEFAULT_SEX_TYPES + custom_types))
    positions = list(dict.fromkeys(DEFAULT_SEX_POSITIONS + custom_positions))
    return sex_types, positions

VALID_ANALYTICS_GROUPS = {'daily', 'weekly', 'monthly', 'yearly'}
VALID_ANALYTICS_LIMITS = {'all', '1', '5', '10', '20', '50'}


def get_analytics_filter_options():
    group_by = request.args.get('group_by', 'daily').strip().lower()
    limit = request.args.get('limit', 'all').strip().lower()
    if group_by not in VALID_ANALYTICS_GROUPS:
        group_by = 'daily'
    if limit not in VALID_ANALYTICS_LIMITS:
        limit = 'all'
    return {
        'group_by': group_by,
        'limit': limit,
        'limit_count': None if limit == 'all' else int(limit)
    }


def safe_entry_date(entry):
    return parse_entry_date(entry.get('date', ''))


def date_obj_to_sort_key(date_obj):
    return date_obj.isoformat() if date_obj else ''


def analytics_bucket_key(date_obj, group_by):
    if group_by == 'weekly':
        return date_obj - timedelta(days=date_obj.weekday())
    if group_by == 'monthly':
        return date_obj.replace(day=1)
    if group_by == 'yearly':
        return date_obj.replace(month=1, day=1)
    return date_obj


def analytics_bucket_label(bucket_date, group_by):
    if group_by == 'weekly':
        week_end = bucket_date + timedelta(days=6)
        return f"{bucket_date.strftime('%d %b')} - {week_end.strftime('%d %b %Y')}"
    if group_by == 'monthly':
        return bucket_date.strftime('%B %Y')
    if group_by == 'yearly':
        return bucket_date.strftime('%Y')
    return bucket_date.strftime('%d %b')


def filter_entries_for_analytics(entries, filters):
    dated_entries = []
    for entry in entries:
        date_obj = safe_entry_date(entry)
        if date_obj:
            dated_entries.append((date_obj, entry))
    dated_entries.sort(key=lambda item: date_obj_to_sort_key(item[0]))

    limit_count = filters.get('limit_count')
    if limit_count is None:
        return [entry for _, entry in dated_entries]

    group_by = filters.get('group_by', 'daily')
    bucket_order = []
    seen_buckets = set()
    for date_obj, _ in dated_entries:
        bucket = analytics_bucket_key(date_obj, group_by)
        if bucket not in seen_buckets:
            seen_buckets.add(bucket)
            bucket_order.append(bucket)

    allowed_buckets = set(bucket_order[-limit_count:])
    return [entry for date_obj, entry in dated_entries if analytics_bucket_key(date_obj, group_by) in allowed_buckets]


def grouped_numeric_average(entries, group_by, value_fields):
    grouped = defaultdict(lambda: {field: [] for field in value_fields})
    for entry in entries:
        date_obj = safe_entry_date(entry)
        if not date_obj:
            continue
        bucket = analytics_bucket_key(date_obj, group_by)
        for field in value_fields:
            try:
                grouped[bucket][field].append(float(entry.get(field) or 0))
            except (TypeError, ValueError):
                pass

    results = []
    for bucket in sorted(grouped.keys()):
        item = {'date': analytics_bucket_label(bucket, group_by)}
        for field in value_fields:
            values = grouped[bucket][field]
            item[field] = round(sum(values) / len(values), 2) if values else 0
        results.append(item)
    return results


def build_period_chart_data(entries, filters):
    filtered_entries = filter_entries_for_analytics(entries, filters)
    for entry in filtered_entries:
        normalize_entry_for_charts(entry)

    group_by = filters.get('group_by', 'daily')
    if group_by == 'daily':
        chart_entries = []
        for entry in filtered_entries:
            item = dict(entry)
            date_obj = safe_entry_date(item)
            item['date'] = analytics_bucket_label(date_obj, 'daily') if date_obj else item.get('date', '')
            chart_entries.append(item)
        return chart_entries

    grouped = defaultdict(lambda: {'amounts': [], 'symptoms': [], 'is_period_start': False})
    for entry in filtered_entries:
        date_obj = safe_entry_date(entry)
        if not date_obj:
            continue
        bucket = analytics_bucket_key(date_obj, group_by)
        grouped[bucket]['amounts'].append(float(entry.get('amount') or 0))
        grouped[bucket]['symptoms'].extend(entry.get('symptoms') or [])
        grouped[bucket]['is_period_start'] = grouped[bucket]['is_period_start'] or bool(entry.get('is_period_start'))

    results = []
    for bucket in sorted(grouped.keys()):
        amounts = grouped[bucket]['amounts']
        results.append({
            'date': analytics_bucket_label(bucket, group_by),
            'amount': round(sum(amounts) / len(amounts), 2) if amounts else 0,
            'symptoms': grouped[bucket]['symptoms'],
            'is_period_start': grouped[bucket]['is_period_start']
        })
    return results


def build_weight_height_chart_data(entries, filters):
    filtered_entries = filter_entries_for_analytics(entries, filters)
    group_by = filters.get('group_by', 'daily')
    if group_by == 'daily':
        return filtered_entries
    return grouped_numeric_average(filtered_entries, group_by, ['weight', 'height', 'bmi'])


def build_weight_height_summary(entries):
    entries = sorted(entries, key=lambda e: date_obj_to_sort_key(safe_entry_date(e)))
    if not entries:
        return {
            'weight': {'current': 0.0, 'previous': 0.0, 'change': 0.0, 'average': 0.0, 'min': 0.0, 'max': 0.0, 'stability': 'Stable'},
            'height': {'current': 0.0, 'average': 0.0, 'trend': 'Stable'},
            'bmi': {'current': 0.0, 'category': 'Normal', 'average': 0.0, 'min': 0.0, 'max': 0.0, 'stability': 'Stable'}
        }

    weights = [float(e.get('weight') or 0) for e in entries]
    heights = [float(e.get('height') or 0) for e in entries]
    bmis = [float(e.get('bmi') or calculate_bmi(e.get('weight'), e.get('height'))) for e in entries]

    def trend_for(values, stable_diff, up_label='Increasing', down_label='Decreasing'):
        if len(values) >= 3:
            last_3 = values[-3:]
            if max(last_3) - min(last_3) <= stable_diff:
                return 'Stable'
            if last_3[2] > last_3[1] > last_3[0]:
                return up_label
            if last_3[2] < last_3[1] < last_3[0]:
                return down_label
            return 'Fluctuating'
        return 'Stable'

    height_trend = 'Stable'
    if len(heights) >= 2:
        diff = heights[-1] - heights[-2]
        if diff > 0.1:
            height_trend = 'Growing'
        elif diff < -0.1:
            height_trend = 'Shrinking'

    return {
        'weight': {
            'current': weights[-1],
            'previous': weights[-2] if len(weights) > 1 else weights[-1],
            'change': round(weights[-1] - (weights[-2] if len(weights) > 1 else weights[-1]), 2),
            'average': round(sum(weights) / len(weights), 2),
            'min': min(weights),
            'max': max(weights),
            'stability': trend_for(weights, 0.5)
        },
        'height': {
            'current': heights[-1],
            'average': round(sum(heights) / len(heights), 2),
            'trend': height_trend
        },
        'bmi': {
            'current': bmis[-1],
            'category': get_bmi_category(bmis[-1]),
            'average': round(sum(bmis) / len(bmis), 2),
            'min': min(bmis),
            'max': max(bmis),
            'stability': trend_for(bmis, 0.2)
        }
    }


def build_sex_summary(entries):
    entries = sorted(entries, key=lambda e: date_obj_to_sort_key(safe_entry_date(e)), reverse=True)
    sex_type_counts = Counter(e.get('sex_type') for e in entries if e.get('sex_type'))
    sex_position_counts = Counter(e.get('position') for e in entries if e.get('position'))
    most_common_type = sex_type_counts.most_common(1)[0] if sex_type_counts else ('Not set', 0)
    most_common_position = sex_position_counts.most_common(1)[0] if sex_position_counts else ('Not set', 0)
    return {
        'total': len(entries),
        'recent': entries[:3],
        'most_common_type': most_common_type[0],
        'most_common_type_count': most_common_type[1],
        'most_common_position': most_common_position[0],
        'most_common_position_count': most_common_position[1],
        'type_chart': {'labels': list(sex_type_counts.keys()), 'data': list(sex_type_counts.values())},
        'position_chart': {'labels': list(sex_position_counts.keys()), 'data': list(sex_position_counts.values())}
    }


def build_cycle_history_rows(fertility_data, filters):
    cycles = fertility_data.get('previous_cycles') or []
    group_by = filters.get('group_by', 'daily')
    limit_count = filters.get('limit_count')
    if group_by == 'daily':
        return cycles if limit_count is None else cycles[:limit_count]

    grouped = defaultdict(list)
    for cycle in cycles:
        start_date = parse_entry_date(cycle.get('start_date', ''))
        if not start_date:
            continue
        grouped[analytics_bucket_key(start_date, group_by)].append(cycle)

    rows = []
    sorted_buckets = sorted(grouped.keys(), reverse=True)
    if limit_count is not None:
        sorted_buckets = sorted_buckets[:limit_count]
    for bucket in sorted_buckets:
        bucket_cycles = grouped[bucket]
        lengths = [cycle.get('length') for cycle in bucket_cycles if cycle.get('length') is not None]
        rows.append({
            'bucket_label': analytics_bucket_label(bucket, group_by),
            'cycle_count': len(bucket_cycles),
            'average_length': round(sum(lengths) / len(lengths), 1) if lengths else 0,
            'is_complete': all(cycle.get('is_complete') for cycle in bucket_cycles)
        })
    return rows

def is_admin_user(email):
    """Check if email is in admin users list"""
    return email.strip().lower() in ADMIN_USERS

@app.route('/')
@auth_required
def home():
    is_view_only = session.get('view_only', False)
    email = session.get('user') or session.get('view_only_email', 'Anonymous User')
    user_name_param = extract_user_name(email) if '@' in email else 'Analytics Viewer'
    messages_path = os.path.join(BASE_DIR, 'static', 'data', 'home_messages.txt')
    try:
        with open(messages_path, 'r', encoding='utf-8') as messages_file:
            messages = [line.strip() for line in messages_file if line.strip()]
    except OSError as e:
        print(f"Error loading home messages: {e}")
        messages = ['Regular tracking helps you understand your cycle better and identify patterns that may be important for your health.']
    home_message = random.choice(messages) if messages else 'Regular tracking helps you understand your cycle better and identify patterns that may be important for your health.'
    return render_template('home.html', user_email=email, user_name=user_name_param, is_view_only=is_view_only, home_message=home_message)

def extract_user_name(email):
    """Extract and format user name from email"""
    name_part = email.split('@')[0]
    return ' '.join(word.capitalize() for word in name_part.replace('_', ' ').replace('.', ' ').split())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        print(f"Login attempt for email: {email}")

        if not is_admin_user(email):
            print(f"Login failed: {email} is not an admin user")
            flash('Access denied. This email is not authorized.')
            return redirect('/login')

        user_data = get_user_settings(email)

        if user_data:
            if check_password(password, user_data.get('password', b'')):
                print(f"Login successful for {email}")
                session['user'] = email
                return redirect('/')
            print(f"Login failed: Invalid password for {email}")
            flash('Invalid password')
            return redirect('/login')

        if password != DEFAULT_PASS:
            print(f"Login failed: First-time admin login attempted with invalid password for {email}")
            flash('Account not found. Use the default password on first login.')
            return redirect('/login')

        print(f"First login for {email}, creating account...")
        db.collection('users').document(email).set({"email": email})
        db.collection('users').document(email).collection('users_setting').document('settings').set({
            "email": email,
            "password": hash_password(password),
            "view_password": VIEW_PASS,
            "created_at": datetime.now()
        })
        print(f"Account created for {email}")
        session['user'] = email
        return redirect('/')

    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address')
            return redirect('/forgot-password')

        if not is_admin_user(email):
            flash('Access denied. This email is not authorized.')
            return redirect('/forgot-password')

        otp = generate_otp(email)
        email_sent = send_otp(email, otp)

        return render_template('otp.html', email=email, debug_otp=None if email_sent else otp, email_sent=email_sent)

    return render_template('forgot_password.html')

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    email = request.form.get('email', '').strip().lower()
    otp = request.form.get('otp', '').strip()

    if not email or not otp:
        flash('OTP verification failed. Please try again.')
        return redirect('/forgot-password')

    if not validate_otp(email, otp):
        flash('Invalid or expired OTP')
        return redirect('/forgot-password')

    session['password_reset_email'] = email
    return redirect('/reset-password')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = session.get('password_reset_email', '')
    if not email:
        flash('Password reset session expired. Please request a new OTP.')
        return redirect('/forgot-password')

    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if new_password != confirm_password:
            flash('New passwords do not match')
            return redirect('/reset-password')

        if not new_password:
            flash('New password cannot be empty')
            return redirect('/reset-password')

        user_setting_doc = get_user_settings(email)

        user_data = {
            'email': email,
            'password': hash_password(new_password),
            'view_password': VIEW_PASS,
            'created_at': datetime.now()
        }

        if user_setting_doc:
            update_user_settings(email, {'password': hash_password(new_password)})
        else:
            db.collection('users').document(email).set({"email": email})
            db.collection('users').document(email).collection('users_setting').document('settings').set(user_data)

        session.pop('password_reset_email', None)
        session['user'] = email
        flash('Password reset successfully. You are now logged in.')
        return redirect('/')

    return render_template('reset_password.html', email=email)

@app.route('/input', methods=['GET', 'POST'])
@login_required
def input_page():
    
    if request.method == 'POST':
        try:
            # Get date and validate
            entry_date = request.form.get('date', '')
            if not entry_date:
                flash('Date is required')
                return redirect('/input')
            
            # Get symptoms
            symptoms = request.form.getlist('symptoms') or []
            
            # Prepare base data
            data = {
                "user_id": session['user'],
                "date": entry_date,
                "symptoms": [],
                "notes": request.form.get('notes', ''),
                "updated_at": datetime.now()
            }
            
            # Check if this is an edit (entry_id provided)
            entry_id = request.form.get('entry_id', '')
            if not entry_id:
                # New entry - add created_at
                data["created_at"] = datetime.now()
            
            # Process Period symptom if selected
            has_period = 'period' in symptoms
            period_ended = request.form.get('period_ended') == 'on'
            
            if has_period or period_ended:
                period_data = {
                    "name": "period"
                }
                
                if has_period:
                    flow_amount = request.form.get('flow_amount', '')
                    period_data["flow_amount"] = int(flow_amount) if flow_amount else None
                    period_data["start_marked"] = request.form.get('periodStart') == 'on'
                    period_data["start_time"] = request.form.get('start_time', '') or None
                    
                if period_ended:
                    period_data["end_marked"] = True
                    period_data["end_time"] = request.form.get('end_time', '') or None
                
                data["symptoms"].append(period_data)
            
            # Process Feeling Weird symptom if selected
            if 'weird' in symptoms:
                weird_intensity = request.form.get('weird_intensity', '')
                data["symptoms"].append({
                    "name": "weird",
                    "intensity": weird_intensity
                })
            
            # Process Craving symptom if selected
            if 'craving' in symptoms:
                craving_intensity = request.form.get('craving_intensity', '')
                data["symptoms"].append({
                    "name": "craving",
                    "intensity": craving_intensity
                })
            
            # Process Irritation symptom if selected
            if 'irritation' in symptoms:
                irritation_intensity = request.form.get('irritation_intensity', '')
                data["symptoms"].append({
                    "name": "irritation",
                    "intensity": irritation_intensity
                })
            
            # Process Diarrhea symptom if selected
            if 'diarrhea' in symptoms:
                data["symptoms"].append({
                    "name": "diarrhea",
                    "intensity": None
                })
            
            # Store in Firestore
            if entry_id:
                # Update existing entry
                db.collection('users').document(session['user']).collection('period_entries').document(entry_id).update(data)
                flash('Entry updated successfully!')
            else:
                # Create new entry
                db.collection('users').document(session['user']).collection('period_entries').add(data)
                flash('Entry added successfully!')
            
            return redirect('/entries')
            
        except Exception as e:
            print(f"Error saving entry: {e}")
            flash('Error saving entry. Please try again.')
            return redirect('/input')
    
    try:
        user_data = get_user_settings(session['user']) or {}
        user_defaults = user_data.get('defaults', {})
    except:
        user_defaults = {}
    
    # Check if editing an entry
    entry_to_edit = None
    entry_id = request.args.get('entry_id', '')
    if entry_id:
        try:
            entry_doc = db.collection('users').document(session['user']).collection('period_entries').document(entry_id).get()
            if entry_doc.exists:
                entry_to_edit = entry_doc.to_dict()
                entry_to_edit['id'] = entry_id
        except Exception as e:
            print(f"Error fetching entry: {e}")
            flash('Error loading entry for editing')
    
    return render_template('input.html', user_defaults=user_defaults, entry_to_edit=entry_to_edit)

@app.route('/analytics')
@auth_required
def analytics():
    is_view_only = session.get('view_only', False)
    user_email = session.get('user') or session.get('view_only_email', '')
    filters = get_analytics_filter_options()

    try:
        entries = get_period_entries(user_email)
        filtered_entries = filter_entries_for_analytics(entries, filters)
        sort_entries_by_date(filtered_entries, reverse=True)

        fertility_data = calculate_fertility_analytics(filtered_entries)
        cycle_history_rows = build_cycle_history_rows(calculate_fertility_analytics(entries), filters)

        weight_height_entries = get_weight_height_entries(user_email, sort_by='date', sort_order='asc')
        filtered_weight_height_entries = filter_entries_for_analytics(weight_height_entries, filters)
        wh_analytics = build_weight_height_summary(filtered_weight_height_entries)

        sex_entries_data = get_sex_entries(user_email, sort_by='date', sort_order='desc')
        filtered_sex_entries = filter_entries_for_analytics(sex_entries_data, filters)
        sex_summary = build_sex_summary(filtered_sex_entries)

        return render_template('analytics.html',
                               fertility=fertility_data,
                               cycle_history_rows=cycle_history_rows,
                               analytics_filters=filters,
                               weight_height=wh_analytics,
                               sex_summary=sex_summary,
                               is_view_only=is_view_only)
    except Exception as e:
        print(f"Error loading analytics: {e}")
        flash(f'Error loading analytics: {str(e)}')
        return redirect('/')

@app.route('/predictor')
@auth_required
def predictor():
    """Cycle predictor and fertility tracker"""
    
    is_view_only = session.get('view_only', False)
    user_email = session.get('user') or session.get('view_only_email', '')
    
    try:
        # Fetch all entries for the user
        entries = get_period_entries(user_email)
        
        # Sort entries by date descending
        sort_entries_by_date(entries, reverse=True)
        
        # Calculate cycle data and supporting body/sex context
        cycle_data = calculate_fertility_analytics(entries)
        latest_body_metric = get_latest_weight_height(user_email)
        recent_sex_entries = get_latest_sex_entries(user_email, limit=5)
        cycle_data['latest_bmi'] = latest_body_metric.get('bmi') if latest_body_metric else None
        cycle_data['latest_bmi_category'] = latest_body_metric.get('bmi_category') if latest_body_metric else None
        cycle_data['recent_sex_count'] = len(recent_sex_entries)
        cycle_data['recent_sex_entries'] = recent_sex_entries
        if cycle_data.get('next_cycle') and cycle_data.get('previous_cycles'):
            cycle_data['predicted_vs_actual_note'] = 'Predictions are compared against your completed period starts as more cycles are logged.'
        else:
            cycle_data['predicted_vs_actual_note'] = 'Add more period starts to compare predicted dates with actual tracked starts.'
        
        return render_template('predictor.html', cycle_data=cycle_data, is_view_only=is_view_only)
    except Exception as e:
        print(f"Error loading predictor: {e}")
        flash(f'Error loading predictor: {str(e)}')
        return redirect('/')

@app.route('/weight-height')
@auth_required
def weight_height_list():
    is_view_only = session.get('view_only', False)
    user_email = session.get('user') or session.get('view_only_email', '')
    
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
        
    try:
        try:
            total_count = db.collection('users').document(user_email).collection('weight_height_entries').count().get()[0][0].value
        except Exception as e:
            print(f"Error using count() on weight_height: {e}")
            total_count = len([d for d in db.collection('users').document(user_email).collection('weight_height_entries').select([]).stream()])
            
        limit = 12
        total_pages = math.ceil(total_count / limit)
        if total_pages < 1:
            total_pages = 1
        if page > total_pages:
            page = total_pages
            
        offset_val = (page - 1) * limit
        
        docs = db.collection('users').document(user_email).collection('weight_height_entries')\
                 .order_by('date', direction='DESCENDING')\
                 .limit(limit)\
                 .offset(offset_val)\
                 .stream()
                 
        entries_list = []
        for doc in docs:
            entry = doc.to_dict()
            entry['id'] = doc.id
            if 'created_at' in entry and entry['created_at']:
                entry['created_at'] = entry['created_at'].isoformat() if hasattr(entry['created_at'], 'isoformat') else str(entry['created_at'])
            if 'updated_at' in entry and entry['updated_at']:
                entry['updated_at'] = entry['updated_at'].isoformat() if hasattr(entry['updated_at'], 'isoformat') else str(entry['updated_at'])
            entries_list.append(entry)
            
        return render_template('weight_height_list.html',
                               entries=entries_list,
                               is_view_only=is_view_only,
                               current_page=page,
                               total_pages=total_pages,
                               total_count=total_count)
    except Exception as e:
        print(f"Error fetching weight/height entries: {e}")
        flash('Error loading metrics')
        return redirect('/')

@app.route('/weight-height/add', methods=['GET', 'POST'])
@login_required
def add_weight_height():
        
    if request.method == 'POST':
        date = request.form.get('date')
        weight = request.form.get('weight')
        height = request.form.get('height')
        
        if not date or not weight or not height:
            flash('Date, weight, and height are required.')
            return redirect('/weight-height/add')
            
        try:
            weight = float(weight)
            height = float(height)
            if weight <= 0 or height <= 0:
                flash('Weight and height must be positive values.')
                return redirect('/weight-height/add')
                
            # Check duplicate (one entry per user per date)
            docs = db.collection('users').document(session['user']).collection('weight_height_entries').where(filter=FieldFilter('date', '==', date)).stream()
            existing = None
            for doc in docs:
                existing = doc.to_dict()
                break
            if existing:
                flash(f'An entry already exists for {date}. Please edit that entry instead.')
                return redirect('/weight-height')
                
            bmi = calculate_bmi(weight, height)
            bmi_cat = get_bmi_category(bmi)
            
            db.collection('users').document(session['user']).collection('weight_height_entries').add({
                'user_id': session['user'],
                'date': date,
                'weight': weight,
                'height': height,
                'bmi': bmi,
                'bmi_category': bmi_cat,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            flash('Weight & Height entry added successfully!')
            return redirect('/weight-height')
        except ValueError:
            flash('Invalid weight or height value.')
            return redirect('/weight-height/add')
        except Exception as e:
            print(f"Error adding weight-height: {e}")
            flash('An error occurred. Please try again.')
            return redirect('/weight-height/add')
            
    return render_template('weight_height_form.html', title='Add Weight & Height', action_url='/weight-height/add', entry=None)

@app.route('/weight-height/edit/<entry_id>', methods=['GET', 'POST'])
@login_required
def edit_weight_height(entry_id):
        
    doc = db.collection('users').document(session['user']).collection('weight_height_entries').document(entry_id).get()
    if not doc.exists:
        flash('Entry not found.')
        return redirect('/weight-height')
    entry = doc.to_dict()
    entry['id'] = doc.id
    
    if entry.get('user_id') != session['user']:
        flash('Unauthorized to edit this entry.')
        return redirect('/weight-height')
        
    if request.method == 'POST':
        date = request.form.get('date')
        weight = request.form.get('weight')
        height = request.form.get('height')
        
        if not date or not weight or not height:
            flash('Date, weight, and height are required.')
            return redirect(f'/weight-height/edit/{entry_id}')
            
        try:
            weight = float(weight)
            height = float(height)
            if weight <= 0 or height <= 0:
                flash('Weight and height must be positive values.')
                return redirect(f'/weight-height/edit/{entry_id}')
                
            # Date changes are allowed, but check duplicate if date changed
            if date != entry['date']:
                docs = db.collection('users').document(session['user']).collection('weight_height_entries').where(filter=FieldFilter('date', '==', date)).stream()
                existing = None
                for doc_existing in docs:
                    existing = doc_existing.to_dict()
                    break
                if existing:
                    flash(f'An entry already exists for {date}.')
                    return redirect(f'/weight-height/edit/{entry_id}')
                    
            bmi = calculate_bmi(weight, height)
            bmi_cat = get_bmi_category(bmi)
            
            # Update in Firestore
            db.collection('users').document(session['user']).collection('weight_height_entries').document(entry_id).update({
                'date': date,
                'weight': weight,
                'height': height,
                'bmi': bmi,
                'bmi_category': bmi_cat,
                'updated_at': datetime.now()
            })
            
            flash('Weight & Height entry updated successfully!')
            return redirect('/weight-height')
        except ValueError:
            flash('Invalid weight or height value.')
            return redirect(f'/weight-height/edit/{entry_id}')
        except Exception as e:
            print(f"Error updating weight-height: {e}")
            flash('An error occurred. Please try again.')
            return redirect(f'/weight-height/edit/{entry_id}')
            
    return render_template('weight_height_form.html', title='Edit Weight & Height', action_url=f'/weight-height/edit/{entry_id}', entry=entry)

@app.route('/weight-height/delete/<entry_id>', methods=['POST'])
@login_required
def delete_weight_height(entry_id):
        
    doc = db.collection('users').document(session['user']).collection('weight_height_entries').document(entry_id).get()
    if not doc.exists or doc.to_dict().get('user_id') != session['user']:
        flash('Entry not found or unauthorized.')
        return redirect('/weight-height')
        
    try:
        db.collection('users').document(session['user']).collection('weight_height_entries').document(entry_id).delete()
        flash('Weight & Height entry deleted successfully!')
    except Exception as e:
        print(f"Error deleting weight-height: {e}")
        flash('An error occurred.')
        
    return redirect('/weight-height')

# --- CRUD APIs ---
@app.route('/api/weight-height', methods=['GET'])
@api_auth_required
def api_get_weight_height():
    user_email = session.get('user') or session.get('view_only_email', '')
    entries = get_weight_height_entries(user_email, sort_by='date', sort_order='desc')
    return jsonify(entries)

@app.route('/api/weight-height/latest', methods=['GET'])
@api_auth_required
def api_get_latest_weight_height():
    user_email = session.get('user') or session.get('view_only_email', '')
    latest = get_latest_weight_height(user_email)
    if latest:
        return jsonify(latest)
    return jsonify({'error': 'No data found'}), 404

@app.route('/api/weight-height', methods=['POST'])
@api_login_required
def api_create_weight_height():
    data = request.get_json() or {}
    date = data.get('date')
    weight = data.get('weight')
    height = data.get('height')
    
    if not date or not weight or not height:
        return jsonify({'error': 'date, weight, and height are required'}), 400
        
    try:
        weight = float(weight)
        height = float(height)
        if weight <= 0 or height <= 0:
            return jsonify({'error': 'weight and height must be positive'}), 400
            
        docs = db.collection('users').document(session['user']).collection('weight_height_entries').where(filter=FieldFilter('date', '==', date)).stream()
        existing = None
        for doc in docs:
            existing = doc.to_dict()
            break
        if existing:
            return jsonify({'error': f'Entry already exists for {date}'}), 409
            
        bmi = calculate_bmi(weight, height)
        bmi_cat = get_bmi_category(bmi)
        
        doc_ref = db.collection('users').document(session['user']).collection('weight_height_entries').add({
            'user_id': session['user'],
            'date': date,
            'weight': weight,
            'height': height,
            'bmi': bmi,
            'bmi_category': bmi_cat,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        ref = doc_ref[1] if isinstance(doc_ref, tuple) else doc_ref
        created = ref.get().to_dict()
        created['id'] = ref.id
        return jsonify(created), 201
    except ValueError:
        return jsonify({'error': 'weight and height must be numbers'}), 400

@app.route('/api/weight-height/<entry_id>', methods=['PUT'])
@api_login_required
def api_update_weight_height(entry_id):
    data = request.get_json() or {}
    weight = data.get('weight')
    height = data.get('height')
    
    doc = db.collection('users').document(session['user']).collection('weight_height_entries').document(entry_id).get()
    if not doc.exists or doc.to_dict().get('user_id') != session['user']:
        return jsonify({'error': 'Entry not found or unauthorized'}), 404
    entry = doc.to_dict()
        
    try:
        if weight is not None:
            weight = float(weight)
            if weight <= 0:
                return jsonify({'error': 'weight must be positive'}), 400
        else:
            weight = entry['weight']
            
        if height is not None:
            height = float(height)
            if height <= 0:
                return jsonify({'error': 'height must be positive'}), 400
        else:
            height = entry['height']
            
        bmi = calculate_bmi(weight, height)
        bmi_cat = get_bmi_category(bmi)
        
        db.collection('users').document(session['user']).collection('weight_height_entries').document(entry_id).update({
            'weight': weight,
            'height': height,
            'bmi': bmi,
            'bmi_category': bmi_cat,
            'updated_at': datetime.now()
        })
        updated_entry = db.collection('users').document(session['user']).collection('weight_height_entries').document(entry_id).get().to_dict()
        updated_entry['id'] = entry_id
        return jsonify(updated_entry)
    except ValueError:
        return jsonify({'error': 'weight and height must be numbers'}), 400

@app.route('/api/weight-height/<entry_id>', methods=['DELETE'])
@api_login_required
def api_delete_weight_height(entry_id):
    doc = db.collection('users').document(session['user']).collection('weight_height_entries').document(entry_id).get()
    if not doc.exists or doc.to_dict().get('user_id') != session['user']:
        return jsonify({'error': 'Entry not found or unauthorized'}), 404
        
    db.collection('users').document(session['user']).collection('weight_height_entries').document(entry_id).delete()
    return jsonify({'success': True})

@app.route('/api/weight-height/analytics', methods=['GET'])
@api_auth_required
def api_weight_height_analytics():
    user_email = session.get('user') or session.get('view_only_email', '')
    analytics = {
        'weight': get_weight_analytics(user_email),
        'height': get_height_analytics(user_email),
        'bmi': get_bmi_analytics(user_email)
    }
    return jsonify(analytics)

@app.route('/api/weight-height/trends', methods=['GET'])
@api_auth_required
def api_weight_height_trends():
    user_email = session.get('user') or session.get('view_only_email', '')
    filters = get_analytics_filter_options()
    entries = get_weight_height_entries(user_email, sort_by='date', sort_order='asc')
    return jsonify(build_weight_height_chart_data(entries, filters))

@app.route('/sex-entries')
@auth_required
def sex_entries():
    """View and manage sexual activity entries."""
    is_view_only = session.get('view_only', False)
    user_email = session.get('user') or session.get('view_only_email', '')
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1

    try:
        try:
            total_count = db.collection('users').document(user_email).collection('sex_entries').count().get()[0][0].value
        except Exception as e:
            print(f"Error using count() on sex_entries: {e}")
            total_count = len([d for d in db.collection('users').document(user_email).collection('sex_entries').select([]).stream()])

        limit = 11
        total_pages = math.ceil(total_count / limit) if total_count else 1
        if page > total_pages:
            page = total_pages

        docs = db.collection('users').document(user_email).collection('sex_entries')\
                 .order_by('date', direction='DESCENDING')\
                 .limit(limit)\
                 .offset((page - 1) * limit)\
                 .stream()

        entries_list = []
        for doc in docs:
            entry = doc.to_dict()
            entry['id'] = doc.id
            if 'created_at' in entry and entry['created_at']:
                entry['created_at'] = entry['created_at'].isoformat() if hasattr(entry['created_at'], 'isoformat') else str(entry['created_at'])
            if 'updated_at' in entry and entry['updated_at']:
                entry['updated_at'] = entry['updated_at'].isoformat() if hasattr(entry['updated_at'], 'isoformat') else str(entry['updated_at'])
            entries_list.append(entry)

        return render_template('sex_entries.html', entries=entries_list, is_view_only=is_view_only,
                               current_page=page, total_pages=total_pages, total_count=total_count)
    except Exception as e:
        print(f"Error fetching sex entries: {e}")
        flash('Error loading sex entries')
        return redirect('/')

@app.route('/sex-entries/add', methods=['GET', 'POST'])
@login_required
def add_sex_entry():
    user_data = get_user_settings(session['user']) or {}
    sex_types, positions = build_sex_options(user_data)

    if request.method == 'POST':
        date = request.form.get('date', '').strip()
        sex_type = request.form.get('sex_type', '').strip()
        position = request.form.get('position', '').strip()
        notes = request.form.get('notes', '').strip()

        if not date or not sex_type:
            flash('Date and sex type are required.')
            return redirect('/sex-entries/add')

        try:
            db.collection('users').document(session['user']).collection('sex_entries').add({
                'user_id': session['user'],
                'date': date,
                'sex_type': sex_type,
                'position': position,
                'notes': notes,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            flash('Sex entry added successfully')
            return redirect('/sex-entries')
        except Exception as e:
            print(f"Error adding sex entry: {e}")
            flash('Error saving sex entry')
            return redirect('/sex-entries/add')

    return render_template('sex_entry_form.html', title='Add Sex Entry', action_url='/sex-entries/add',
                           entry=None, sex_types=sex_types, positions=positions)

@app.route('/sex-entries/edit/<entry_id>', methods=['GET', 'POST'])
@login_required
def edit_sex_entry(entry_id):
    doc = db.collection('users').document(session['user']).collection('sex_entries').document(entry_id).get()
    if not doc.exists:
        flash('Sex entry not found')
        return redirect('/sex-entries')

    entry = doc.to_dict()
    entry['id'] = doc.id
    if entry.get('user_id') != session['user']:
        flash('Unauthorized to edit this entry')
        return redirect('/sex-entries')

    user_data = get_user_settings(session['user']) or {}
    sex_types, positions = build_sex_options(user_data)

    if request.method == 'POST':
        date = request.form.get('date', '').strip()
        sex_type = request.form.get('sex_type', '').strip()
        position = request.form.get('position', '').strip()
        notes = request.form.get('notes', '').strip()

        if not date or not sex_type:
            flash('Date and sex type are required.')
            return redirect(f'/sex-entries/edit/{entry_id}')

        try:
            db.collection('users').document(session['user']).collection('sex_entries').document(entry_id).update({
                'date': date,
                'sex_type': sex_type,
                'position': position,
                'notes': notes,
                'updated_at': datetime.now()
            })
            flash('Sex entry updated successfully')
            return redirect('/sex-entries')
        except Exception as e:
            print(f"Error updating sex entry: {e}")
            flash('Error updating sex entry')
            return redirect(f'/sex-entries/edit/{entry_id}')

    return render_template('sex_entry_form.html', title='Edit Sex Entry', action_url=f'/sex-entries/edit/{entry_id}',
                           entry=entry, sex_types=sex_types, positions=positions)

@app.route('/sex-entries/delete/<entry_id>', methods=['POST'])
@login_required
def delete_sex_entry(entry_id):
    doc = db.collection('users').document(session['user']).collection('sex_entries').document(entry_id).get()
    if not doc.exists or doc.to_dict().get('user_id') != session['user']:
        flash('Sex entry not found or unauthorized')
        return redirect('/sex-entries')

    try:
        db.collection('users').document(session['user']).collection('sex_entries').document(entry_id).delete()
        flash('Sex entry deleted successfully')
    except Exception as e:
        print(f"Error deleting sex entry: {e}")
        flash('Error deleting sex entry')
    return redirect('/sex-entries')

@app.route('/api/sex-entries/trends')
@api_auth_required
def api_sex_entries_trends():
    user_email = session.get('user') or session.get('view_only_email', '')
    filters = get_analytics_filter_options()
    entries = get_sex_entries(user_email, sort_by='date', sort_order='asc')
    return jsonify(filter_entries_for_analytics(entries, filters))
@app.route('/entries')
@auth_required
def entries():
    """View and manage all entries"""
    
    is_view_only = session.get('view_only', False)
    user_email = session.get('user') or session.get('view_only_email', '')
    
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
        
    try:
        try:
            total_count = db.collection('users').document(user_email).collection('period_entries').count().get()[0][0].value
        except Exception as e:
            print(f"Error using count() on period_entries: {e}")
            total_count = len([d for d in db.collection('users').document(user_email).collection('period_entries').select([]).stream()])
            
        limit = 12
        total_pages = math.ceil(total_count / limit)
        if total_pages < 1:
            total_pages = 1
        if page > total_pages:
            page = total_pages
            
        offset_val = (page - 1) * limit
        
        # Fetch only 12 rows for the current page
        docs = db.collection('users').document(user_email).collection('period_entries')\
                 .order_by('date', direction='DESCENDING')\
                 .limit(limit)\
                 .offset(offset_val)\
                 .stream()
                 
        entries_list = []
        for doc in docs:
            entry_data = doc.to_dict()
            entry_data['id'] = doc.id
            if 'notes' not in entry_data or entry_data['notes'] is None:
                entry_data['notes'] = ''
            if 'symptoms' not in entry_data or entry_data['symptoms'] is None:
                entry_data['symptoms'] = []
            if 'created_at' in entry_data and entry_data['created_at']:
                entry_data['created_at'] = entry_data['created_at'].isoformat() if hasattr(entry_data['created_at'], 'isoformat') else str(entry_data['created_at'])
            if 'updated_at' in entry_data and entry_data['updated_at']:
                entry_data['updated_at'] = entry_data['updated_at'].isoformat() if hasattr(entry_data['updated_at'], 'isoformat') else str(entry_data['updated_at'])
            entries_list.append(entry_data)
            
        return render_template('entries.html', 
                               entries=entries_list, 
                               is_view_only=is_view_only,
                               current_page=page,
                               total_pages=total_pages,
                               total_count=total_count)
    except Exception as e:
        print(f"Error fetching entries: {e}")
        flash('Error loading entries')
        return redirect('/')

@app.route('/delete-entry/<entry_id>', methods=['POST'])
def delete_entry(entry_id):
    """Delete a specific entry"""
    if 'user' not in session:
        return redirect('/login')
    
    try:
        # Verify the entry belongs to the current user
        entry_doc = db.collection('users').document(session['user']).collection('period_entries').document(entry_id).get()
        if not entry_doc.exists:
            flash('Entry not found')
            return redirect('/entries')
        
        entry_data = entry_doc.to_dict()
        if entry_data.get('user_id') != session['user']:
            flash('Unauthorized to delete this entry')
            return redirect('/entries')
        
        # Delete the entry
        db.collection('users').document(session['user']).collection('period_entries').document(entry_id).delete()
        flash('Entry deleted successfully!')
        return redirect('/entries')
    
    except Exception as e:
        print(f"Error deleting entry: {e}")
        flash('Error deleting entry')
        return redirect('/entries')

@app.route('/analytics-data')
def analytics_data():
    if 'user' not in session and not session.get('view_only'):
        return jsonify({'error': 'Not logged in'}), 401

    user_email = session.get('user') or session.get('view_only_email', '')
    filters = get_analytics_filter_options()
    data = get_period_entries(user_email)
    return jsonify(build_period_chart_data(data, filters))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():

    user_data = get_user_settings(session['user'])
    if not user_data:
        flash('User not found')
        return redirect('/login')

    if request.method == 'POST':
        if 'change_password' in request.form:
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if new_password != confirm_password:
                flash('New passwords do not match')
                return redirect('/settings')

            if check_password(old_password, user_data.get('password', b'')):
                update_user_settings(session['user'], {'password': hash_password(new_password)})
                flash('Password changed successfully')
                return redirect('/settings')

            flash('Invalid old password')
            return redirect('/settings')

        if 'verify_view_password' in request.form:
            entered_view_password = request.form.get('view_password_check', '')
            current_view_password = user_data.get('view_password', VIEW_PASS)
            if entered_view_password == current_view_password:
                return render_template('settings.html', view_pass=current_view_password, view_password_verified=True)
            flash('Invalid view-only password')
            return redirect('/settings')

        if 'change_view_password' in request.form:
            new_view_password = request.form.get('new_view_password', '')
            confirm_view_password = request.form.get('confirm_view_password', '')

            if not new_view_password:
                flash('New view-only password cannot be empty')
                return redirect('/settings')

            if new_view_password != confirm_view_password:
                flash('New view-only passwords do not match')
                return redirect('/settings')

            update_user_settings(session['user'], {'view_password': new_view_password})
            flash('View-only password changed successfully')
            return redirect('/settings')

    return render_template('settings.html', view_pass=user_data.get('view_password', VIEW_PASS), view_password_verified=False)
@app.route('/customize', methods=['GET', 'POST'])
@login_required
def customize():
    
    user_email = session['user']
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        user_data = get_user_settings(user_email)
        if not user_data:
            flash('User not found')
            return redirect('/customize')
        
        if action == 'add_sex_type':
            option = request.form.get('sex_type_name', '').strip()
            if not option:
                flash('Sex type is required')
                return redirect('/customize')
            custom_sex_types = user_data.get('custom_sex_types', [])
            if option in DEFAULT_SEX_TYPES or option in custom_sex_types:
                flash('Sex type already exists')
                return redirect('/customize')
            custom_sex_types.append(option)
            update_user_settings(user_email, {'custom_sex_types': custom_sex_types})
            flash('Sex type added successfully')

        elif action == 'add_sex_position':
            option = request.form.get('sex_position_name', '').strip()
            if not option:
                flash('Position is required')
                return redirect('/customize')
            custom_sex_positions = user_data.get('custom_sex_positions', [])
            if option in DEFAULT_SEX_POSITIONS or option in custom_sex_positions:
                flash('Position already exists')
                return redirect('/customize')
            custom_sex_positions.append(option)
            update_user_settings(user_email, {'custom_sex_positions': custom_sex_positions})
            flash('Position added successfully')

        elif action == 'edit_sex_type':
            old_option = request.form.get('old_sex_type_name', '').strip()
            new_option = request.form.get('sex_type_name', '').strip()
            custom_sex_types = user_data.get('custom_sex_types', [])
            if old_option not in custom_sex_types:
                flash('Only custom sex types can be edited')
                return redirect('/customize')
            if not new_option:
                flash('Sex type is required')
                return redirect('/customize')
            if new_option != old_option and (new_option in DEFAULT_SEX_TYPES or new_option in custom_sex_types):
                flash('Sex type already exists')
                return redirect('/customize')
            custom_sex_types = [new_option if item == old_option else item for item in custom_sex_types]
            update_user_settings(user_email, {'custom_sex_types': custom_sex_types})
            flash('Sex type updated successfully')

        elif action == 'edit_sex_position':
            old_option = request.form.get('old_sex_position_name', '').strip()
            new_option = request.form.get('sex_position_name', '').strip()
            custom_sex_positions = user_data.get('custom_sex_positions', [])
            if old_option not in custom_sex_positions:
                flash('Only custom positions can be edited')
                return redirect('/customize')
            if not new_option:
                flash('Position is required')
                return redirect('/customize')
            if new_option != old_option and (new_option in DEFAULT_SEX_POSITIONS or new_option in custom_sex_positions):
                flash('Position already exists')
                return redirect('/customize')
            custom_sex_positions = [new_option if item == old_option else item for item in custom_sex_positions]
            update_user_settings(user_email, {'custom_sex_positions': custom_sex_positions})
            flash('Position updated successfully')

        elif action == 'delete_sex_type':
            option = request.form.get('sex_type_name', '').strip()
            custom_sex_types = [item for item in user_data.get('custom_sex_types', []) if item != option]
            update_user_settings(user_email, {'custom_sex_types': custom_sex_types})
            flash('Sex type removed successfully')

        elif action == 'delete_sex_position':
            option = request.form.get('sex_position_name', '').strip()
            custom_sex_positions = [item for item in user_data.get('custom_sex_positions', []) if item != option]
            update_user_settings(user_email, {'custom_sex_positions': custom_sex_positions})
            flash('Position removed successfully')

        elif action == 'add_symptom':
            symptom_name = request.form.get('symptom_name', '').strip().lower()
            has_intensity = request.form.get('has_intensity') == 'yes'
            
            if not symptom_name:
                flash('Symptom name is required')
                return redirect('/customize')
            
            custom_symptoms = user_data.get('custom_symptoms', [])
            
            if any(s['name'] == symptom_name for s in custom_symptoms):
                flash('Symptom already exists')
                return redirect('/customize')
            
            custom_symptoms.append({
                'name': symptom_name,
                'display_name': request.form.get('symptom_name', ''),
                'has_intensity': has_intensity,
                'system_default': False
            })
            
            update_user_settings(user_email, {
                'custom_symptoms': custom_symptoms
            })
            flash('Symptom added successfully')
            
        elif action == 'edit_symptom':
            symptom_name = request.form.get('symptom_name', '').strip()
            display_name = request.form.get('display_name', '').strip()
            has_intensity = request.form.get('has_intensity') == 'yes'
            is_system_default = request.form.get('is_system_default').lower() == 'true'
            old_has_intensity = request.form.get('old_has_intensity').lower() == 'true'
            
            if is_system_default:
                symptom_overrides = user_data.get('symptom_overrides', {})
                if symptom_name not in symptom_overrides:
                    symptom_overrides[symptom_name] = {}
                
                symptom_overrides[symptom_name] = {
                    'display_name': display_name,
                    'has_intensity': has_intensity
                }
                
                if old_has_intensity and not has_intensity:
                    docs = db.collection('users').document(session['user']).collection('period_entries').stream()
                    for doc in docs:
                        entry_data = doc.to_dict()
                        if 'symptoms' in entry_data:
                            for symptom in entry_data['symptoms']:
                                if symptom.get('name') == symptom_name and 'intensity' not in symptom and has_intensity is False:
                                    pass
                                elif symptom.get('name') == symptom_name and 'intensity' in symptom:
                                    symptom['intensity_before_removal'] = symptom.get('intensity', 'medium')
                    
                update_user_settings(user_email, {
                    'symptom_overrides': symptom_overrides
                })
            else:
                custom_symptoms = user_data.get('custom_symptoms', [])
                for symptom in custom_symptoms:
                    if symptom['name'] == symptom_name:
                        symptom['display_name'] = display_name
                        symptom['has_intensity'] = has_intensity
                        break
                
                if old_has_intensity and not has_intensity:
                    docs = db.collection('users').document(session['user']).collection('period_entries').stream()
                    for doc in docs:
                        entry_data = doc.to_dict()
                        if 'symptoms' in entry_data:
                            for symptom in entry_data['symptoms']:
                                if symptom.get('name') == symptom_name and 'intensity' in symptom:
                                    symptom['intensity_before_removal'] = 'medium'
                                    if 'intensity' in symptom:
                                        del symptom['intensity']
                
                update_user_settings(user_email, {
                    'custom_symptoms': custom_symptoms
                })
            
            flash('Symptom updated successfully')
            
        elif action == 'delete_symptom':
            symptom_name = request.form.get('symptom_name', '').strip()
            is_system_default = request.form.get('is_system_default').lower() == 'true'
            
            if is_system_default:
                disabled_symptoms = user_data.get('disabled_symptoms', [])
                if symptom_name not in disabled_symptoms:
                    disabled_symptoms.append(symptom_name)
                
                docs = db.collection('users').document(session['user']).collection('period_entries').stream()
                for doc in docs:
                    entry_data = doc.to_dict()
                    if 'symptoms' in entry_data:
                        entry_data['symptoms'] = [s for s in entry_data['symptoms'] if s.get('name') != symptom_name]
                        db.collection('users').document(session['user']).collection('period_entries').document(doc.id).update({
                            'symptoms': entry_data['symptoms']
                        })
                
                update_user_settings(user_email, {
                    'disabled_symptoms': disabled_symptoms
                })
            else:
                custom_symptoms = user_data.get('custom_symptoms', [])
                custom_symptoms = [s for s in custom_symptoms if s['name'] != symptom_name]
                
                docs = db.collection('users').document(session['user']).collection('period_entries').stream()
                for doc in docs:
                    entry_data = doc.to_dict()
                    if 'symptoms' in entry_data:
                        entry_data['symptoms'] = [s for s in entry_data['symptoms'] if s.get('name') != symptom_name]
                        db.collection('users').document(session['user']).collection('period_entries').document(doc.id).update({
                            'symptoms': entry_data['symptoms']
                        })
                
                update_user_settings(user_email, {
                    'custom_symptoms': custom_symptoms
                })
            
            flash('Symptom deleted successfully')
            
        elif action == 'save_defaults':
            defaults = {
                'flow_amount': int(request.form.get('default_flow_amount', 5)),
                'weird_intensity': request.form.get('default_weird_intensity', ''),
                'craving_intensity': request.form.get('default_craving_intensity', ''),
                'irritation_intensity': request.form.get('default_irritation_intensity', ''),
                'diarrhea_intensity': request.form.get('default_diarrhea_intensity', '')
            }
            
            update_user_settings(user_email, {
                'defaults': defaults
            })
            flash('Default settings saved successfully')
        
        return redirect('/customize')
    
    try:
        user_data = get_user_settings(user_email)
        if not user_data:
            flash('User settings not found')
            return redirect('/')
        
        # Standard symptoms
        standard_symptoms = [
            {'name': 'period', 'display_name': 'Period', 'has_intensity': False, 'system_default': True},
            {'name': 'date', 'display_name': 'Date', 'has_intensity': False, 'system_default': True},
            {'name': 'weird', 'display_name': 'Feeling Weird', 'has_intensity': True, 'system_default': True},
            {'name': 'craving', 'display_name': 'Craving', 'has_intensity': True, 'system_default': True},
            {'name': 'irritation', 'display_name': 'Irritation', 'has_intensity': True, 'system_default': True}
        ]
        
        # Get user's overrides and disabled symptoms
        symptom_overrides = user_data.get('symptom_overrides', {})
        disabled_symptoms = user_data.get('disabled_symptoms', [])
        
        # Build final symptoms list with overrides applied
        all_symptoms = []
        for symptom in standard_symptoms:
            if symptom['name'] not in disabled_symptoms:
                # Apply overrides if they exist
                if symptom['name'] in symptom_overrides:
                    override = symptom_overrides[symptom['name']]
                    symptom = symptom.copy()
                    symptom['display_name'] = override.get('display_name', symptom['display_name'])
                    symptom['has_intensity'] = override.get('has_intensity', symptom['has_intensity'])
                
                all_symptoms.append(symptom)
        
        # Add custom symptoms
        custom_symptoms = user_data.get('custom_symptoms', [])
        all_symptoms.extend(custom_symptoms)
        
        defaults = user_data.get('defaults', {})
        sex_types, sex_positions = build_sex_options(user_data)
        custom_sex_types = user_data.get('custom_sex_types', [])
        custom_sex_positions = user_data.get('custom_sex_positions', [])
        
        return render_template('customize.html', symptoms=all_symptoms, defaults=defaults,
                               sex_types=sex_types, sex_positions=sex_positions,
                               custom_sex_types=custom_sex_types,
                               custom_sex_positions=custom_sex_positions)
    except Exception as e:
        flash(f'Error loading customize page: {str(e)}')
        return redirect('/')

@app.route('/view-analytics-mode', methods=['GET', 'POST'])
def view_analytics_mode():
    """View-only mode - no login required"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == VIEW_PASS:
            return redirect(f'/view-analytics/{password}')
        else:
            flash('Invalid analytics password')
    
    return render_template('view_analytics_mode.html')

@app.route('/view-analytics-login', methods=['GET', 'POST'])
def view_analytics_login():
    """View specific user's analytics with email and password"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email:
            flash('Please enter an email address')
            return redirect('/view-analytics-login')

        try:
            user_data = get_user_settings(email)
            if not user_data:
                flash('User not found')
                return redirect('/view-analytics-login')
            current_view_password = user_data.get('view_password', VIEW_PASS)
            if password != current_view_password:
                flash('Invalid analytics password')
                return redirect('/view-analytics-login')

            session['view_only'] = True
            session['view_only_email'] = email
            session.modified = True
            return redirect('/')

        except Exception as e:
            print(f"Error fetching user: {e}")
            flash('Error loading user data')
            return redirect('/view-analytics-login')

    return render_template('view_analytics_login.html')

@app.route('/view-analytics/<password>')
def view_analytics(password):
    """View shared analytics with VIEW_PASS"""
    if password != VIEW_PASS:
        flash('Invalid analytics password')
        return redirect('/view-analytics-mode')

    try:
        if not ADMIN_USERS:
            flash('No admin user configured')
            return redirect('/view-analytics-mode')

        admin_email = ADMIN_USERS[0]
        user_data = get_user_settings(admin_email)
        if user_data:
            session['view_only'] = True
            session['view_only_email'] = admin_email
            session.modified = True
            return redirect('/')

    except Exception as e:
        print(f"Error fetching admin user: {e}")
        flash('Error loading analytics data')

    return redirect('/view-analytics-mode')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('view_only', None)
    return redirect('/login')

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors - page not found"""
    print(f"404 Error: {request.path} not found")
    flash('Page not found')
    if 'user' in session:
        return redirect('/')
    return redirect('/login')

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors - server error"""
    print(f"500 Error: {str(error)}")
    flash('An internal server error occurred')
    return redirect('/login'), 500

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors - forbidden"""
    flash('Access forbidden')
    return redirect('/login'), 403

@app.after_request
def add_header(response):
    """Add cache control headers"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == "__main__":
    app.run(debug=True)











