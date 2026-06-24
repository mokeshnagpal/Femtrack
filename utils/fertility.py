# utils/fertility.py
from datetime import datetime, timedelta
from utils.date_helpers import format_date_readable

def calculate_cycle_data(entries):
    """
    Calculate cycle predictions based on entry history
    Returns:
    - previous_cycles: list of completed cycles with their data
    - current_cycle: data for the ongoing cycle (if any)
    - next_cycle: predictions for the next cycle
    - fertile_window: predicted fertile window
    - timeline: timeline details
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
                if isinstance(symptom, dict) and symptom.get('name') == 'period':
                    date_str = entry.get('date')
                    if date_str:
                        date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        period_dates.append(date)
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
            current_cycle = {
                'start_date': last_period.isoformat(),
                'start_date_str': format_date_readable(last_period),
                'days_in_cycle': days_since_last_period,
                'predicted_end': (last_period + timedelta(days=average_cycle_length)).isoformat(),
                'is_fertile': is_in_fertile_window(days_since_last_period, average_cycle_length),
                'cycle_percentage': (days_since_last_period / average_cycle_length) * 100,
                'is_current': True
            }
            
            next_start = last_period + timedelta(days=average_cycle_length)
            next_cycle = {
                'start_date': next_start.isoformat(),
                'predicted': True,
                'is_current': False
            }
            
            current_fertile_window = calculate_fertile_window(last_period, average_cycle_length)
            next_fertile_window = calculate_fertile_window(next_start, average_cycle_length)
        else:
            current_cycle = {
                'start_date': last_period.isoformat(),
                'start_date_str': format_date_readable(last_period),
                'days_in_cycle': average_cycle_length,
                'predicted_end': (last_period + timedelta(days=average_cycle_length)).isoformat(),
                'is_complete': True,
                'is_current': False
            }
            
            next_start = last_period + timedelta(days=average_cycle_length)
            days_until_next = (next_start - today).days
            next_cycle = {
                'start_date': next_start.isoformat(),
                'start_date_str': format_date_readable(next_start),
                'predicted': True,
                'days_until': days_until_next if days_until_next > 0 else 0,
                'is_current': False
            }
            
            current_fertile_window = calculate_fertile_window(last_period, average_cycle_length)
            next_fertile_window = calculate_fertile_window(next_start, average_cycle_length)
        
        # Build previous cycles
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
    
    timeline = build_timeline(last_period if period_dates else today, average_cycle_length, today)
    
    return {
        'average_cycle_length': average_cycle_length,
        'actual_ovulation_day': average_cycle_length // 2,
        'previous_cycles': previous_cycles,
        'current_cycle': current_cycle,
        'next_cycle': next_cycle,
        'current_fertile_window': current_fertile_window,
        'next_fertile_window': next_fertile_window,
        'fertile_window': current_fertile_window,
        'timeline': timeline,
        'last_period': last_period.isoformat() if period_dates else None
    }

def is_in_fertile_window(days_in_cycle, cycle_length):
    """Check if a day is in the fertile window"""
    ovulation_day = cycle_length // 2
    fertile_start = ovulation_day - 5
    fertile_end = ovulation_day + 1
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
        'duration': 6
    }

def build_timeline(cycle_start, cycle_length, today):
    """Build timeline data for visualization"""
    timeline = []
    
    # Previous cycle
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
    
    # Next cycle predictions
    next_start = cycle_start + timedelta(days=cycle_length)
    for i in range(min(14, cycle_length)):
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

def calculate_fertility_analytics(entries):
    """Calculate fertility intelligence metrics."""
    cycle_data = calculate_cycle_data(entries)
    
    # Extract period dates to compute period length
    period_dates = []
    for entry in entries:
        if 'symptoms' in entry:
            for symptom in entry['symptoms']:
                if isinstance(symptom, dict) and symptom.get('name') == 'period':
                    date_str = entry.get('date')
                    if date_str:
                        try:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                            period_dates.append(date_obj)
                        except ValueError:
                            pass
                            
    period_dates.sort()
    periods = []
    if period_dates:
        curr_period = [period_dates[0]]
        for d in period_dates[1:]:
            if (d - curr_period[-1]).days <= 2:
                curr_period.append(d)
            else:
                periods.append(curr_period)
                curr_period = [d]
        periods.append(curr_period)
        
    period_lengths = [len(p) for p in periods]
    average_period_length = int(sum(period_lengths) / len(period_lengths)) if period_lengths else 5

    # Extract cycle lengths
    period_starts = []
    for entry in entries:
        if 'symptoms' in entry:
            for symptom in entry['symptoms']:
                if isinstance(symptom, dict) and symptom.get('name') == 'period' and symptom.get('start_marked'):
                    date_str = entry.get('date')
                    if date_str:
                        try:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                            period_starts.append(date_obj)
                        except ValueError:
                            pass
    period_starts.sort()
    cycle_lengths = []
    for i in range(1, len(period_starts)):
        cycle_length = (period_starts[i] - period_starts[i-1]).days
        if 15 < cycle_length < 50:
            cycle_lengths.append(cycle_length)
            
    # Regularity Score
    if len(cycle_lengths) >= 2:
        max_diff = max(cycle_lengths) - min(cycle_lengths)
        if max_diff <= 2:
            cycle_regularity_score = 'Regular'
            fertility_window_consistency = 95
        elif max_diff <= 5:
            cycle_regularity_score = 'Moderately Regular'
            fertility_window_consistency = 80
        else:
            cycle_regularity_score = 'Irregular'
            fertility_window_consistency = 60
    else:
        cycle_regularity_score = 'Regular'
        fertility_window_consistency = 90
        
    # Prediction Confidence Score
    num_cycles = len(cycle_lengths)
    if num_cycles == 0:
        fertility_confidence_score = 20
    elif num_cycles == 1:
        fertility_confidence_score = 50
    elif num_cycles == 2:
        fertility_confidence_score = 75
    else:
        fertility_confidence_score = min(95, 75 + (num_cycles - 2) * 5)
        
    # Current phase and fertility probability today
    average_cycle_length = cycle_data['average_cycle_length']
    current_cycle = cycle_data['current_cycle']
    
    if current_cycle:
        day = current_cycle.get('days_in_cycle', 1)
        day_clamped = min(max(day, 1), average_cycle_length)
        ov_day = average_cycle_length // 2
        
        if day_clamped <= average_period_length:
            fertility_probability = 30
        elif day_clamped < ov_day - 5:
            fertility_probability = 40
        elif day_clamped <= ov_day + 1:
            distance = abs(day_clamped - ov_day)
            fertility_probability = max(50, 100 - distance * 15)
        elif day_clamped <= average_cycle_length:
            fertility_probability = 30
        else:
            fertility_probability = 20
            
        curr_day = current_cycle.get('days_in_cycle', 0)
        phase = get_cycle_phase(curr_day, average_cycle_length)
        current_cycle_phase = phase.capitalize()
    else:
        fertility_probability = 30
        current_cycle_phase = 'Menstruation'
        
    # Ovulation prediction
    predicted_ovulation_date_str = 'None'
    predicted_next_period_str = 'None'
    if period_dates:
        last_period = period_dates[-1]
        next_start_date = last_period + timedelta(days=average_cycle_length)
        predicted_ovulation = next_start_date - timedelta(days=14)
        predicted_ovulation_date_str = format_date_readable(predicted_ovulation)
        predicted_next_period_str = format_date_readable(next_start_date)
        
    # Update cycle_data dict
    cycle_data['average_period_length'] = average_period_length
    cycle_data['average_ovulation_day'] = average_cycle_length // 2
    cycle_data['cycle_regularity_score'] = cycle_regularity_score
    cycle_data['fertility_window_consistency'] = fertility_window_consistency
    cycle_data['fertility_confidence_score'] = fertility_confidence_score
    cycle_data['fertility_probability'] = fertility_probability
    cycle_data['current_cycle_phase'] = current_cycle_phase
    cycle_data['predicted_ovulation_date_str'] = predicted_ovulation_date_str
    cycle_data['predicted_next_period_str'] = predicted_next_period_str
    
    return cycle_data
