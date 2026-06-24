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

def validate_otp(email, otp):
    if email not in otp_store:
        return False
    entry = otp_store[email]
    if datetime.now() > entry["expiry"]:
        del otp_store[email]
        return False
    if entry["otp"] != otp:
        return False
    # Valid OTP
    del otp_store[email]
    return True