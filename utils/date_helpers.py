# utils/date_helpers.py
from datetime import datetime

def format_date_readable(date_obj):
    """Format date as 'DD Month YYYY' (e.g., '14 July 2026')"""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
        except ValueError:
            return date_obj
    return date_obj.strftime('%d %B %Y')

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
    """Sort entry dictionaries by their date value in-place."""
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
