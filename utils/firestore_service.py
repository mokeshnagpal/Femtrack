# utils/firestore_service.py
from config import db
from google.cloud.firestore import FieldFilter

def get_user_settings(user_email):
    """Retrieve user settings document dictionary."""
    doc_ref = db.collection('users').document(user_email).collection('users_setting').document('settings')
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def update_user_settings(user_email, data):
    """Update user settings document with the given data."""
    doc_ref = db.collection('users').document(user_email).collection('users_setting').document('settings')
    doc_ref.update(data)

def get_period_entries(user_email):
    """Retrieve all daily period log entries for a user."""
    docs = db.collection('users').document(user_email).collection('period_entries').stream()
    entries = []
    for doc in docs:
        entry = doc.to_dict()
        entry['id'] = doc.id
        if 'created_at' in entry and entry['created_at']:
            entry['created_at'] = entry['created_at'].isoformat() if hasattr(entry['created_at'], 'isoformat') else str(entry['created_at'])
        if 'updated_at' in entry and entry['updated_at']:
            entry['updated_at'] = entry['updated_at'].isoformat() if hasattr(entry['updated_at'], 'isoformat') else str(entry['updated_at'])
        entries.append(entry)
    return entries

def get_weight_height_entries(user_email, filters=None, sort_by='date', sort_order='desc'):
    """Retrieve sorted and filtered weight/height health entries for a user."""
    docs = db.collection('users').document(user_email).collection('weight_height_entries').stream()
    entries = []
    for doc in docs:
        entry = doc.to_dict()
        entry['id'] = doc.id
        if 'created_at' in entry and entry['created_at']:
            entry['created_at'] = entry['created_at'].isoformat() if hasattr(entry['created_at'], 'isoformat') else str(entry['created_at'])
        if 'updated_at' in entry and entry['updated_at']:
            entry['updated_at'] = entry['updated_at'].isoformat() if hasattr(entry['updated_at'], 'isoformat') else str(entry['updated_at'])
        entries.append(entry)
    
    if filters:
        search_query = filters.get('search', '').lower().strip()
        if search_query:
            entries = [
                e for e in entries
                if search_query in str(e.get('weight', '')).lower()
                or search_query in str(e.get('height', '')).lower()
                or search_query in str(e.get('bmi', '')).lower()
                or search_query in str(e.get('bmi_category', '')).lower()
                or search_query in str(e.get('date', '')).lower()
            ]
        
        from_date = filters.get('from_date', '').strip()
        if from_date:
            entries = [e for e in entries if e.get('date', '') >= from_date]
            
        to_date = filters.get('to_date', '').strip()
        if to_date:
            entries = [e for e in entries if e.get('date', '') <= to_date]
            
    # Sort
    reverse = (sort_order == 'desc')
    def get_sort_val(e):
        val = e.get(sort_by)
        if val is None:
            if sort_by in ('weight', 'height', 'bmi'):
                return 0.0
            return ''
        if sort_by in ('weight', 'height', 'bmi'):
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
        return val
        
    entries.sort(key=get_sort_val, reverse=reverse)
    return entries

def get_latest_weight_height(user_email):
    """Retrieve the most recent weight/height record."""
    entries = get_weight_height_entries(user_email, sort_by='date', sort_order='desc')
    if entries:
        return entries[0]
    return None

def get_sex_entries(user_email, filters=None, sort_by='date', sort_order='desc'):
    """Retrieve sorted and filtered sexual activity entries for a user."""
    docs = db.collection('users').document(user_email).collection('sex_entries').stream()
    entries = []
    for doc in docs:
        entry = doc.to_dict()
        entry['id'] = doc.id
        if 'created_at' in entry and entry['created_at']:
            entry['created_at'] = entry['created_at'].isoformat() if hasattr(entry['created_at'], 'isoformat') else str(entry['created_at'])
        if 'updated_at' in entry and entry['updated_at']:
            entry['updated_at'] = entry['updated_at'].isoformat() if hasattr(entry['updated_at'], 'isoformat') else str(entry['updated_at'])
        entries.append(entry)

    if filters:
        search_query = filters.get('search', '').lower().strip()
        if search_query:
            entries = [
                e for e in entries
                if search_query in str(e.get('date', '')).lower()
                or search_query in str(e.get('sex_type', '')).lower()
                or search_query in str(e.get('position', '')).lower()
                or search_query in str(e.get('notes', '')).lower()
            ]

    reverse = sort_order == 'desc'
    entries.sort(key=lambda e: e.get(sort_by, ''), reverse=reverse)
    return entries

def get_latest_sex_entries(user_email, limit=5):
    """Retrieve recent sexual activity entries for dashboard context."""
    return get_sex_entries(user_email, sort_by='date', sort_order='desc')[:limit]
