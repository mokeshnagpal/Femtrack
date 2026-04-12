from flask import Flask, render_template, request, redirect, session, jsonify, flash
from config import db, ADMIN_USERS, VIEW_PASS
from utils.auth import hash_password, check_password
from datetime import datetime, timedelta
from google.cloud.firestore import FieldFilter
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Register Jinja2 filter for cycle phase colors
def get_day_color(phase, is_past=False, is_predicted=False):
    """Return color for a given cycle phase"""
    colors = {
        'menstruation': {'current': '#dc3545', 'past': '#f8d7da'},
        'follicular': {'current': '#0dcaf0', 'past': '#cfe2ff'},
        'ovulation': {'current': '#ffc107', 'past': '#fff3cd'},
        'luteal': {'current': '#198754', 'past': '#d1e7dd'}
    }
    
    if is_predicted:
        return colors.get(phase, {}).get('past', '#e9ecef')
    
    return colors.get(phase, {}).get('past' if is_past else 'current', '#e9ecef')

app.jinja_env.filters['get_day_color'] = get_day_color

def format_date_readable(date_obj):
    """Format date as 'DD Month YYYY' (e.g., '14 July 2026')"""
    if isinstance(date_obj, str):
        # If it's a string, parse it first
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
        except ValueError:
            return date_obj
    return date_obj.strftime('%d %B %Y')

# Register date formatting filter for Jinja2
app.jinja_env.filters['format_date'] = format_date_readable

def parse_entry_date(date_value):
    """Parse an entry date string into a date object."""
    if isinstance(date_value, datetime):
        return date_value.date()
    if isinstance(date_value, str):
        for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d %b', '%d %B %Y'):
            try:
                return datetime.strptime(date_value, fmt).date()
            except ValueError:
                continue
    return None


def sort_entries_by_date(entries, reverse=False):
    """Sort entry dictionaries by their date value."""
    def sort_key(entry):
        parsed_date = parse_entry_date(entry.get('date', ''))
        return parsed_date or datetime.min.date()
    entries.sort(key=sort_key, reverse=reverse)


def normalize_entry_for_charts(entry):
    """Normalize entry fields for analytics chart rendering."""
    if 'amount' not in entry or entry['amount'] is None:
        entry['amount'] = entry.get('flow_amount', 0) or 0
        if entry['amount'] == 0 and isinstance(entry.get('symptoms'), list):
            for symptom in entry['symptoms']:
                if isinstance(symptom, dict) and symptom.get('name') == 'period':
                    entry['amount'] = symptom.get('flow_amount', 0) or 0
                    break
    try:
        entry['amount'] = int(entry['amount']) if entry['amount'] else 0
    except (ValueError, TypeError):
        entry['amount'] = 0
    return entry


def is_admin_user(email):
    """Check if email is in admin users list"""
    return email in ADMIN_USERS

@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    
    # Extract name from email
    email = session['user']
    # Extract part before @ and format it
    name_part = email.split('@')[0]
    # Replace dots/underscores with spaces and capitalize each word
    user_name = ' '.join(word.capitalize() for word in name_part.replace('_', ' ').replace('.', ' ').split())
    
    return render_template('home.html', user_email=email, user_name=user_name)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        print(f"Login attempt for email: {email}")
        
        # Check if user is admin
        if not is_admin_user(email):
            print(f"Login failed: {email} is not an admin user")
            flash('Access denied. This email is not authorized.')
            return redirect('/login')
        
        # Check if user exists in database
        users = db.collection('users').where(filter=FieldFilter('email', '==', email)).stream()
        user_found = False
        
        for user_doc in users:
            user_data = user_doc.to_dict()
            if check_password(password, user_data.get('password', b'')):
                print(f"Login successful for {email}")
                session['user'] = email
                return redirect('/')
            user_found = True
            break
        
        if user_found:
            print(f"Login failed: Invalid password for {email}")
            flash('Invalid password')
        else:
            print(f"First login for {email}, creating account...")
            # First time login - create account with hashed password
            hashed = hash_password(password)
            db.collection('users').add({
                "email": email,
                "password": hashed,
                "view_password": VIEW_PASS,
                "created_at": datetime.now()
            })
            print(f"Account created for {email}")
            session['user'] = email
            return redirect('/')
        
    
    return render_template('login.html')

@app.route('/input', methods=['GET', 'POST'])
def input_page():
    if 'user' not in session:
        return redirect('/login')
    
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
            if 'period' in symptoms:
                flow_amount = request.form.get('flow_amount', '')
                
                period_data = {
                    "name": "period",
                    "flow_amount": int(flow_amount) if flow_amount else None,
                    "start_marked": request.form.get('periodStart') == 'on',
                    "end_marked": request.form.get('periodEnd') == 'on',
                    "start_time": request.form.get('start_time', '') or None,
                    "end_time": request.form.get('end_time', '') or None
                }
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
            
            # Process Joint Pain symptom if selected
            if 'joint_pain' in symptoms:
                joint_pain_intensity = request.form.get('joint_pain_intensity', '')
                data["symptoms"].append({
                    "name": "joint_pain",
                    "intensity": joint_pain_intensity
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
                db.collection('entries').document(entry_id).update(data)
                flash('Entry updated successfully!')
            else:
                # Create new entry
                db.collection('entries').add(data)
                flash('Entry added successfully!')
            
            return redirect('/entries')
            
        except Exception as e:
            print(f"Error saving entry: {e}")
            flash('Error saving entry. Please try again.')
            return redirect('/input')
    
    # For GET request - fetch user defaults and check for edit parameter
    try:
        user_doc = db.collection('users').document(session['user']).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        user_defaults = user_data.get('defaults', {})
    except:
        user_defaults = {}
    
    # Check if editing an entry
    entry_to_edit = None
    entry_id = request.args.get('entry_id', '')
    if entry_id:
        try:
            entry_doc = db.collection('entries').document(entry_id).get()
            if entry_doc.exists:
                entry_to_edit = entry_doc.to_dict()
                entry_to_edit['id'] = entry_id
        except Exception as e:
            print(f"Error fetching entry: {e}")
            flash('Error loading entry for editing')
    
    return render_template('input.html', user_defaults=user_defaults, entry_to_edit=entry_to_edit)

@app.route('/analytics')
def analytics():
    if 'user' not in session:
        return redirect('/login')
    
    try:
        user_email = session['user']
        
        # Fetch all entries for the user
        entries_query = db.collection('entries').where(
            filter=FieldFilter('user_id', '==', user_email)
        ).stream()
        
        entries = []
        for doc in entries_query:
            entries.append({
                'id': doc.id,
                **doc.to_dict()
            })
        
        # Sort entries by date descending
        sort_entries_by_date(entries, reverse=True)
        
        # Calculate cycle data
        cycle_data = calculate_cycle_data(entries)
        
        return render_template('analytics.html', cycle_data=cycle_data)
    except Exception as e:
        print(f"Error loading analytics: {e}")
        flash(f'Error loading analytics: {str(e)}')
        return redirect('/')

@app.route('/predictor')
def predictor():
    """Cycle predictor and fertility tracker"""
    if 'user' not in session:
        return redirect('/login')
    
    try:
        user_email = session['user']
        
        # Fetch all entries for the user
        entries_query = db.collection('entries').where(
            filter=FieldFilter('user_id', '==', user_email)
        ).stream()
        
        entries = []
        for doc in entries_query:
            entries.append({
                'id': doc.id,
                **doc.to_dict()
            })
        
        # Sort entries by date descending
        sort_entries_by_date(entries, reverse=True)
        
        # Calculate cycle data
        cycle_data = calculate_cycle_data(entries)
        
        return render_template('predictor.html', cycle_data=cycle_data, entries=entries)
    except Exception as e:
        print(f"Error loading predictor: {e}")
        flash(f'Error loading predictor: {str(e)}')
        return redirect('/')

def calculate_cycle_data(entries):
    """
    Calculate cycle predictions based on entry history
    Returns:
    - previous_cycles: list of completed cycles with their data
    - current_cycle: data for the ongoing cycle (if any)
    - next_cycle: predictions for the next cycle
    - fertile_window: predicted fertile window
    """
    if not entries:
        return {
            'average_cycle_length': 28,
            'previous_cycles': [],
            'current_cycle': None,
            'next_cycle': None,
            'fertile_window': None,
            'timeline': []
        }
    
    # Extract period entries (where period symptom is marked)
    period_dates = []
    period_starts = []
    for entry in entries:
        if 'symptoms' in entry:
            for symptom in entry['symptoms']:
                if symptom.get('name') == 'period':
                    # Parse date string
                    date_str = entry.get('date')
                    if date_str:
                        date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        period_dates.append(date)
                        # Collect period start dates
                        if symptom.get('start_marked'):
                            period_starts.append(date)
    
    period_dates.sort()
    period_starts.sort()
    
    # Calculate cycle lengths using period start dates
    cycle_lengths = []
    for i in range(1, len(period_starts)):
        cycle_length = (period_starts[i] - period_starts[i-1]).days
        if 15 < cycle_length < 50:  # Valid cycle length
            cycle_lengths.append(cycle_length)
    
    # Calculate average cycle length
    average_cycle_length = int(sum(cycle_lengths) / len(cycle_lengths)) if cycle_lengths else 28
    
    # Build cycle data
    today = datetime.now().date()
    previous_cycles = []
    current_cycle = None
    next_cycle = None
    fertile_window = None
    
    if period_dates:
        last_period = period_dates[-1]
        days_since_last_period = (today - last_period).days
        
        # Check if we're in ongoing cycle
        if days_since_last_period < average_cycle_length:
            # Ongoing cycle
            current_cycle = {
                'start_date': last_period.isoformat(),
                'start_date_str': format_date_readable(last_period),
                'days_in_cycle': days_since_last_period,
                'predicted_end': (last_period + timedelta(days=average_cycle_length)).isoformat(),
                'is_fertile': is_in_fertile_window(days_since_last_period, average_cycle_length),
                'cycle_percentage': (days_since_last_period / average_cycle_length) * 100,
                'is_current': True
            }
            
            # Next cycle prediction
            next_start = last_period + timedelta(days=average_cycle_length)
            next_cycle = {
                'start_date': next_start.isoformat(),
                'predicted': True,
                'is_current': False
            }
            
            # Calculate fertile window for current cycle
            current_fertile_window = calculate_fertile_window(last_period, average_cycle_length)
            
            # Calculate fertile window for next cycle
            next_start = last_period + timedelta(days=average_cycle_length)
            next_fertile_window = calculate_fertile_window(next_start, average_cycle_length)
        else:
            # Last period was completed, next cycle is upcoming
            current_cycle = {
                'start_date': last_period.isoformat(),
                'start_date_str': format_date_readable(last_period),
                'days_in_cycle': average_cycle_length,
                'predicted_end': (last_period + timedelta(days=average_cycle_length)).isoformat(),
                'is_complete': True,
                'is_current': False
            }
            
            # Predict next cycle
            next_start = last_period + timedelta(days=average_cycle_length)
            days_until_next = (next_start - today).days
            next_cycle = {
                'start_date': next_start.isoformat(),
                'start_date_str': format_date_readable(next_start),
                'predicted': True,
                'days_until': days_until_next if days_until_next > 0 else 0,
                'is_current': False
            }
            
            # Calculate fertile window for completed cycle (historical)
            current_fertile_window = calculate_fertile_window(last_period, average_cycle_length)
            
            # Calculate fertile window for upcoming cycle
            next_fertile_window = calculate_fertile_window(next_start, average_cycle_length)
        
        # Build previous cycles from historical data
        for i in range(len(period_starts) - 1):
            start_date = period_starts[i]
            end_date = period_starts[i + 1]
            prev_cycle = {
                'start_date': start_date.isoformat(),
                'start_date_str': format_date_readable(start_date),
                'end_date': end_date.isoformat(),
                'length': (end_date - start_date).days,
                'is_complete': True,
                'is_current': False
            }
            previous_cycles.append(prev_cycle)
        
        previous_cycles.reverse()
    
    # Build timeline data
    timeline = build_timeline(last_period if period_dates else today, average_cycle_length, today)
    
    return {
        'average_cycle_length': average_cycle_length,
        'actual_ovulation_day': average_cycle_length // 2,  # Day of peak fertility/ovulation
        'previous_cycles': previous_cycles,
        'current_cycle': current_cycle,
        'next_cycle': next_cycle,
        'current_fertile_window': current_fertile_window,
        'next_fertile_window': next_fertile_window,
        'fertile_window': current_fertile_window,  # Keep for backward compatibility
        'timeline': timeline,
        'last_period': last_period.isoformat() if period_dates else None
    }

def is_in_fertile_window(days_in_cycle, cycle_length):
    """Check if a day is in the fertile window"""
    ovulation_day = cycle_length // 2  # Approximate ovulation day
    fertile_start = ovulation_day - 5   # 5 days before ovulation
    fertile_end = ovulation_day + 1     # Day after ovulation
    
    return fertile_start <= days_in_cycle <= fertile_end

def calculate_fertile_window(cycle_start, cycle_length):
    """Calculate the fertile window for a cycle"""
    ovulation_day = cycle_length // 2
    fertile_start = cycle_start + timedelta(days=ovulation_day - 5)
    fertile_end = cycle_start + timedelta(days=ovulation_day + 1)
    
    return {
        'start': fertile_start.isoformat(),
        'end': fertile_end.isoformat(),
        'start_str': format_date_readable(fertile_start),
        'end_str': format_date_readable(fertile_end),
        'duration': 6  # Usually 5-6 days
    }

def build_timeline(cycle_start, cycle_length, today):
    """Build timeline data for visualization"""
    timeline = []
    
    # Previous cycle (last cycle before current)
    prev_start = cycle_start - timedelta(days=cycle_length)
    for i in range(cycle_length):
        date = prev_start + timedelta(days=i)
        phase = get_cycle_phase(i, cycle_length)
        timeline.append({
            'date': date.isoformat(),
            'day': i + 1,
            'phase': phase,
            'is_past': date < today,
            'is_today': date == today,
            'cycle': 'previous'
        })
    
    # Current/upcoming cycle
    for i in range(cycle_length):
        date = cycle_start + timedelta(days=i)
        phase = get_cycle_phase(i, cycle_length)
        timeline.append({
            'date': date.isoformat(),
            'day': i + 1,
            'phase': phase,
            'is_past': date < today,
            'is_today': date == today,
            'is_future': date > today,
            'cycle': 'current'
        })
    
    # Next cycle (next predicted cycle)
    next_start = cycle_start + timedelta(days=cycle_length)
    for i in range(min(14, cycle_length)):  # Show first 2 weeks of next cycle
        date = next_start + timedelta(days=i)
        phase = get_cycle_phase(i, cycle_length)
        timeline.append({
            'date': date.isoformat(),
            'day': i + 1,
            'phase': phase,
            'is_future': date > today,
            'cycle': 'next'
        })
    
    return timeline

def get_cycle_phase(day, cycle_length):
    """Determine the phase of the menstrual cycle"""
    if day < 5:
        return 'menstruation'
    elif day < 14:
        return 'follicular'
    elif day < 21:
        return 'ovulation'
    else:
        return 'luteal'

@app.route('/entries')
def entries():
    """View and manage all entries"""
    if 'user' not in session:
        return redirect('/login')
    
    try:
        # Fetch all entries for the current user
        docs = db.collection('entries').where(filter=FieldFilter('user_id', '==', session['user'])).stream()
        entries_list = []
        
        for doc in docs:
            entry_data = doc.to_dict()
            entry_data['id'] = doc.id
            entries_list.append(entry_data)
        
        # Sort by date in descending order (newest first)
        sort_entries_by_date(entries_list, reverse=True)
        
        return render_template('entries.html', entries=entries_list)
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
        entry_doc = db.collection('entries').document(entry_id).get()
        if not entry_doc.exists:
            flash('Entry not found')
            return redirect('/entries')
        
        entry_data = entry_doc.to_dict()
        if entry_data.get('user_id') != session['user']:
            flash('Unauthorized to delete this entry')
            return redirect('/entries')
        
        # Delete the entry
        db.collection('entries').document(entry_id).delete()
        flash('Entry deleted successfully!')
        return redirect('/entries')
    
    except Exception as e:
        print(f"Error deleting entry: {e}")
        flash('Error deleting entry')
        return redirect('/entries')

@app.route('/analytics-data')
def analytics_data():
    if 'user' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    # Fetch entries without order_by to avoid index requirement
    docs = db.collection('entries').where(filter=FieldFilter('user_id', '==', session['user'])).stream()
    data = [doc.to_dict() for doc in docs]
    
    # Sort by date in Python
    sort_entries_by_date(data, reverse=False)
    
    # Format dates to show month names and ensure amount is numeric
    from datetime import datetime
    for entry in data:
        normalize_entry_for_charts(entry)
        try:
            date_obj = datetime.strptime(entry.get('date', ''), '%Y-%m-%d').date()
            entry['date'] = date_obj.strftime('%d %b')  # Format as "15 Jan"
        except (ValueError, KeyError):
            entry['date'] = entry.get('date', '')
    
    return jsonify(data)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        if 'change_password' in request.form:
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if new_password != confirm_password:
                flash('New passwords do not match')
                return redirect('/settings')

            users = db.collection('users').where(filter=FieldFilter('email', '==', session['user'])).stream()
            for user_doc in users:
                user_data = user_doc.to_dict()
                if check_password(old_password, user_data.get('password', b'')):
                    db.collection('users').document(user_doc.id).update({
                        'password': hash_password(new_password)
                    })
                    flash('Password changed successfully')
                    return redirect('/settings')
                break
            flash('Invalid old password')

    return render_template('settings.html', view_pass=VIEW_PASS)

@app.route('/customize', methods=['GET', 'POST'])
def customize():
    if 'user' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        # Get or create user document
        users = db.collection('users').where(filter=FieldFilter('email', '==', session['user'])).stream()
        user_doc_id = None
        for user_doc in users:
            user_doc_id = user_doc.id
            break
        
        if not user_doc_id:
            flash('User not found')
            return redirect('/customize')
        
        if action == 'add_symptom':
            symptom_name = request.form.get('symptom_name', '').strip().lower()
            has_intensity = request.form.get('has_intensity') == 'yes'
            
            if not symptom_name:
                flash('Symptom name is required')
                return redirect('/customize')
            
            # Get current user data
            user_doc = db.collection('users').document(user_doc_id).get()
            user_data = user_doc.to_dict() or {}
            custom_symptoms = user_data.get('custom_symptoms', [])
            
            # Check if symptom already exists
            if any(s['name'] == symptom_name for s in custom_symptoms):
                flash('Symptom already exists')
                return redirect('/customize')
            
            # Add new symptom
            custom_symptoms.append({
                'name': symptom_name,
                'display_name': request.form.get('symptom_name', ''),
                'has_intensity': has_intensity,
                'system_default': False
            })
            
            db.collection('users').document(user_doc_id).update({
                'custom_symptoms': custom_symptoms
            })
            flash('Symptom added successfully')
            
        elif action == 'edit_symptom':
            symptom_name = request.form.get('symptom_name', '').strip()
            display_name = request.form.get('display_name', '').strip()
            has_intensity = request.form.get('has_intensity') == 'yes'
            is_system_default = request.form.get('is_system_default').lower() == 'true'
            old_has_intensity = request.form.get('old_has_intensity').lower() == 'true'
            
            # Get current user data
            user_doc = db.collection('users').document(user_doc_id).get()
            user_data = user_doc.to_dict() or {}
            
            if is_system_default:
                # Store override for system default symptom
                symptom_overrides = user_data.get('symptom_overrides', {})
                if symptom_name not in symptom_overrides:
                    symptom_overrides[symptom_name] = {}
                
                symptom_overrides[symptom_name] = {
                    'display_name': display_name,
                    'has_intensity': has_intensity
                }
                
                # If removing intensity, mark entries for conversion
                if old_has_intensity and not has_intensity:
                    # Update all entries for this user to default to 'medium' intensity for this symptom
                    docs = db.collection('entries').where(filter=FieldFilter('user_id', '==', session['user'])).stream()
                    for doc in docs:
                        entry_data = doc.to_dict()
                        if 'symptoms' in entry_data:
                            for symptom in entry_data['symptoms']:
                                if symptom.get('name') == symptom_name and 'intensity' not in symptom and has_intensity is False:
                                    # No intensity to convert, just mark as processed
                                    pass
                                elif symptom.get('name') == symptom_name and 'intensity' in symptom:
                                    # If they had intensity, default to medium if removing
                                    symptom['intensity_before_removal'] = symptom.get('intensity', 'medium')
                    
                db.collection('users').document(user_doc_id).update({
                    'symptom_overrides': symptom_overrides
                })
            else:
                # Edit custom symptom
                custom_symptoms = user_data.get('custom_symptoms', [])
                for symptom in custom_symptoms:
                    if symptom['name'] == symptom_name:
                        symptom['display_name'] = display_name
                        symptom['has_intensity'] = has_intensity
                        break
                
                # If removing intensity, update entries
                if old_has_intensity and not has_intensity:
                    docs = db.collection('entries').where(filter=FieldFilter('user_id', '==', session['user'])).stream()
                    for doc in docs:
                        entry_data = doc.to_dict()
                        if 'symptoms' in entry_data:
                            for symptom in entry_data['symptoms']:
                                if symptom.get('name') == symptom_name and 'intensity' in symptom:
                                    # Store intensity as medium for conversion
                                    symptom['intensity_before_removal'] = 'medium'
                                    # Remove the old intensity field
                                    if 'intensity' in symptom:
                                        del symptom['intensity']
                
                db.collection('users').document(user_doc_id).update({
                    'custom_symptoms': custom_symptoms
                })
            
            flash('Symptom updated successfully')
            
        elif action == 'delete_symptom':
            symptom_name = request.form.get('symptom_name', '').strip()
            is_system_default = request.form.get('is_system_default').lower() == 'true'
            
            # Get current user data
            user_doc = db.collection('users').document(user_doc_id).get()
            user_data = user_doc.to_dict() or {}
            
            if is_system_default:
                # Mark system default as disabled/deleted for this user
                disabled_symptoms = user_data.get('disabled_symptoms', [])
                if symptom_name not in disabled_symptoms:
                    disabled_symptoms.append(symptom_name)
                
                # Delete all entries with this symptom for this user
                docs = db.collection('entries').where(filter=FieldFilter('user_id', '==', session['user'])).stream()
                for doc in docs:
                    entry_data = doc.to_dict()
                    if 'symptoms' in entry_data:
                        entry_data['symptoms'] = [s for s in entry_data['symptoms'] if s.get('name') != symptom_name]
                        db.collection('entries').document(doc.id).update({
                            'symptoms': entry_data['symptoms']
                        })
                
                db.collection('users').document(user_doc_id).update({
                    'disabled_symptoms': disabled_symptoms
                })
            else:
                # Delete custom symptom
                custom_symptoms = user_data.get('custom_symptoms', [])
                custom_symptoms = [s for s in custom_symptoms if s['name'] != symptom_name]
                
                # Delete all entries with this symptom for this user
                docs = db.collection('entries').where(filter=FieldFilter('user_id', '==', session['user'])).stream()
                for doc in docs:
                    entry_data = doc.to_dict()
                    if 'symptoms' in entry_data:
                        entry_data['symptoms'] = [s for s in entry_data['symptoms'] if s.get('name') != symptom_name]
                        db.collection('entries').document(doc.id).update({
                            'symptoms': entry_data['symptoms']
                        })
                
                db.collection('users').document(user_doc_id).update({
                    'custom_symptoms': custom_symptoms
                })
            
            flash('Symptom deleted successfully')
            
        elif action == 'save_defaults':
            defaults = {
                'flow_amount': int(request.form.get('default_flow_amount', 5)),
                'weird_intensity': request.form.get('default_weird_intensity', ''),
                'craving_intensity': request.form.get('default_craving_intensity', ''),
                'irritation_intensity': request.form.get('default_irritation_intensity', ''),
                'joint_pain_intensity': request.form.get('default_joint_pain_intensity', ''),
                'diarrhea_intensity': request.form.get('default_diarrhea_intensity', '')
            }
            
            db.collection('users').document(user_doc_id).update({
                'defaults': defaults
            })
            flash('Default settings saved successfully')
        
        return redirect('/customize')
    
    # GET request - display customize page
    try:
        users = db.collection('users').where(filter=FieldFilter('email', '==', session['user'])).stream()
        user_data = {}
        user_doc_id = None
        for user_doc in users:
            user_data = user_doc.to_dict() or {}
            user_doc_id = user_doc.id
            break
        
        # Standard symptoms
        standard_symptoms = [
            {'name': 'period', 'display_name': 'Period', 'has_intensity': False, 'system_default': True},
            {'name': 'date', 'display_name': 'Date', 'has_intensity': False, 'system_default': True},
            {'name': 'weird', 'display_name': 'Feeling Weird', 'has_intensity': True, 'system_default': True},
            {'name': 'craving', 'display_name': 'Craving', 'has_intensity': True, 'system_default': True},
            {'name': 'irritation', 'display_name': 'Irritation', 'has_intensity': True, 'system_default': True},
            {'name': 'joint_pain', 'display_name': 'Joint Pain', 'has_intensity': True, 'system_default': True}
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
        
        return render_template('customize.html', symptoms=all_symptoms, defaults=defaults)
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
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Validate password
        if password != VIEW_PASS:
            flash('Invalid analytics password')
            return redirect('/view-analytics-login')
        
        # Validate email exists
        if not email:
            flash('Please enter an email address')
            return redirect('/view-analytics-login')
        
        try:
            # Check if user exists
            users = db.collection('users').where(filter=FieldFilter('email', '==', email)).stream()
            user_found = False
            
            for user_doc in users:
                user_found = True
                # Fetch entries for this user
                docs = db.collection('entries').where(filter=FieldFilter('user_id', '==', email)).stream()
                data = [normalize_entry_for_charts(doc.to_dict()) for doc in docs]
                
                # Sort by date in Python
                sort_entries_by_date(data, reverse=False)
                
                # Set session for view-only mode
                session['view_only'] = True
                
                return render_template('shared_analytics.html', data=data, view_mode=True, user_email=email)
            
            if not user_found:
                flash('User not found')
                return redirect('/view-analytics-login')
                
        except Exception as e:
            print(f"Error fetching analytics: {e}")
            flash('Error loading analytics data')
            return redirect('/view-analytics-login')
    
    # GET request - display login form
    return render_template('view_analytics_login.html')

@app.route('/view-analytics/<password>')
def view_analytics(password):
    """View shared analytics with VIEW_PASS"""
    if password != VIEW_PASS:
        flash('Invalid analytics password')
        return redirect('/view-analytics-mode')
    
    try:
        # Get first admin user's analytics for demo
        users = db.collection('users').where(filter=FieldFilter('email', '==', ADMIN_USERS[0])).stream()
        for user_doc in users:
            # Fetch entries without order_by to avoid index requirement
            docs = db.collection('entries').where(filter=FieldFilter('user_id', '==', user_doc.to_dict()['email'])).stream()
            data = [normalize_entry_for_charts(doc.to_dict()) for doc in docs]
            
            # Sort by date in Python
            sort_entries_by_date(data, reverse=False)
            
            return render_template('shared_analytics.html', data=data, view_mode=True)
    except Exception as e:
        print(f"Error fetching analytics: {e}")
        flash('Error loading analytics data')
    
    return redirect('/view-analytics-mode')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('view_only', None)
    return redirect('/login')
