# utils/biometrics.py
from utils.firestore_service import get_weight_height_entries

def calculate_bmi(weight, height):
    """Calculate BMI dynamically given weight in kg and height in cm."""
    if not weight or not height:
        return 0.0
    try:
        height_m = float(height) / 100.0
        return round(float(weight) / (height_m ** 2), 2)
    except ZeroDivisionError:
        return 0.0

def get_bmi_category(bmi):
    """Return BMI category name string."""
    if bmi < 18.5:
        return 'Underweight'
    elif bmi < 25.0:
        return 'Normal'
    elif bmi < 30.0:
        return 'Overweight'
    else:
        return 'Obese'

def get_weight_analytics(user_email):
    """Calculate weight statistics and stability markers."""
    entries = get_weight_height_entries(user_email, sort_by='date', sort_order='asc') # oldest first
    if not entries:
        return {
            'current': 0.0,
            'previous': 0.0,
            'change': 0.0,
            'average': 0.0,
            'min': 0.0,
            'max': 0.0,
            'stability': 'Stable'
        }

    weights = [float(e['weight']) for e in entries]
    latest_weight = weights[-1]
    previous_weight = weights[-2] if len(weights) > 1 else latest_weight
    weight_change = round(latest_weight - previous_weight, 2)
    avg_weight = round(sum(weights) / len(weights), 2)
    min_weight = min(weights)
    max_weight = max(weights)

    # Determine stability
    stability = 'Stable'
    if len(weights) >= 3:
        last_3 = weights[-3:]
        max_diff = max(last_3) - min(last_3)
        if max_diff <= 0.5:
            stability = 'Stable'
        elif last_3[2] > last_3[1] > last_3[0]:
            stability = 'Increasing'
        elif last_3[2] < last_3[1] < last_3[0]:
            stability = 'Decreasing'
        else:
            stability = 'Fluctuating'

    return {
        'current': latest_weight,
        'previous': previous_weight,
        'change': weight_change,
        'average': avg_weight,
        'min': min_weight,
        'max': max_weight,
        'stability': stability
    }

def get_height_analytics(user_email):
    """Calculate height statistics and growth trends."""
    entries = get_weight_height_entries(user_email, sort_by='date', sort_order='asc')
    if not entries:
        return {
            'current': 0.0,
            'average': 0.0,
            'trend': 'Stable'
        }
    heights = [float(e['height']) for e in entries]
    latest_height = heights[-1]
    avg_height = round(sum(heights) / len(heights), 2)
    
    trend = 'Stable'
    if len(heights) >= 2:
        diff = latest_height - heights[-2]
        if diff > 0.1:
            trend = 'Growing'
        elif diff < -0.1:
            trend = 'Shrinking'
            
    return {
        'current': latest_height,
        'average': avg_height,
        'trend': trend
    }

def get_bmi_analytics(user_email):
    """Calculate BMI statistics and stability progression."""
    entries = get_weight_height_entries(user_email, sort_by='date', sort_order='asc')
    if not entries:
        return {
            'current': 0.0,
            'category': 'Normal',
            'average': 0.0,
            'min': 0.0,
            'max': 0.0,
            'stability': 'Stable'
        }
    bmis = [float(e['bmi']) for e in entries]
    latest_bmi = bmis[-1]
    latest_cat = get_bmi_category(latest_bmi)
    avg_bmi = round(sum(bmis) / len(bmis), 2)
    min_bmi = min(bmis)
    max_bmi = max(bmis)
    
    stability = 'Stable'
    if len(bmis) >= 3:
        last_3 = bmis[-3:]
        max_diff = max(last_3) - min(last_3)
        if max_diff <= 0.2:
            stability = 'Stable'
        elif last_3[2] > last_3[1] > last_3[0]:
            stability = 'Increasing'
        elif last_3[2] < last_3[1] < last_3[0]:
            stability = 'Decreasing'
        else:
            stability = 'Fluctuating'
            
    return {
        'current': latest_bmi,
        'category': latest_cat,
        'average': avg_bmi,
        'min': min_bmi,
        'max': max_bmi,
        'stability': stability
    }
