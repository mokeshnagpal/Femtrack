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
    current_fertile_window = None
    next_fertile_window = None
    
    if period_dates:
        # Group period_dates into contiguous period blocks (gap <= 2 days)
        periods = []
        curr_period = [period_dates[0]]
        for d in period_dates[1:]:
            if (d - curr_period[-1]).days <= 2:
                curr_period.append(d)
            else:
                periods.append(curr_period)
                curr_period = [d]
        periods.append(curr_period)
        
        # The latest period starts on the first day of the last block
        latest_period = periods[-1]
        cycle_start = latest_period[0]
        days_in_cycle = (today - cycle_start).days
        
        # Check if we're in ongoing cycle
        if days_in_cycle < average_cycle_length:
            current_cycle = {
                'start_date': cycle_start.isoformat(),
                'start_date_str': format_date_readable(cycle_start),
                'days_in_cycle': days_in_cycle,
                'predicted_end': (cycle_start + timedelta(days=average_cycle_length)).isoformat(),
                'is_fertile': is_in_fertile_window(days_in_cycle, average_cycle_length),
                'cycle_percentage': (days_in_cycle / average_cycle_length) * 100,
                'is_current': True
            }
            
            next_start = cycle_start + timedelta(days=average_cycle_length)
            next_cycle = {
                'start_date': next_start.isoformat(),
                'predicted': True,
                'is_current': False
            }
            
            current_fertile_window = calculate_fertile_window(cycle_start, average_cycle_length)
            next_fertile_window = calculate_fertile_window(next_start, average_cycle_length)
        else:
            current_cycle = {
                'start_date': cycle_start.isoformat(),
                'start_date_str': format_date_readable(cycle_start),
                'days_in_cycle': average_cycle_length,
                'predicted_end': (cycle_start + timedelta(days=average_cycle_length)).isoformat(),
                'is_complete': True,
                'is_current': False
            }
            
            next_start = cycle_start + timedelta(days=average_cycle_length)
            days_until_next = (next_start - today).days
            next_cycle = {
                'start_date': next_start.isoformat(),
                'start_date_str': format_date_readable(next_start),
                'predicted': True,
                'days_until': days_until_next if days_until_next > 0 else 0,
                'is_current': False
            }
            
            current_fertile_window = calculate_fertile_window(cycle_start, average_cycle_length)
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
        
        timeline = build_timeline(cycle_start, average_cycle_length, today)
        last_period_date = period_dates[-1]
    else:
        timeline = build_timeline(today, average_cycle_length, today)
        last_period_date = None
    
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
        'last_period': last_period_date.isoformat() if last_period_date else None,
        'periods': periods,
        'cycle_lengths': cycle_lengths,
        'period_dates': period_dates
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
    for i in range(cycle_length):
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
    print(f"[{datetime.now().isoformat()}] INFO: Running calculate_fertility_analytics with {len(entries)} entries")
    cycle_data = calculate_cycle_data(entries)
    
    periods = cycle_data.get('periods') or []
    cycle_lengths = cycle_data.get('cycle_lengths') or []
    period_dates = cycle_data.get('period_dates') or []

    period_lengths = [len(p) for p in periods]
    average_period_length = int(sum(period_lengths) / len(period_lengths)) if period_lengths else 5
            
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
        cycle_start = periods[-1][0] if periods else period_dates[0]
        next_start_date = cycle_start + timedelta(days=average_cycle_length)
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
