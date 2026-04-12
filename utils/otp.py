# utils/otp.py
import random
from datetime import datetime, timedelta

otp_store = {}

def generate_otp(email):
    otp = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=5)

    otp_store[email] = {
        "otp": otp,
        "expiry": expiry
    }

    return otp