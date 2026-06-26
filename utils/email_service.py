# utils/email_service.py
import smtplib
from config import EMAIL_USER, EMAIL_PASSWORD

def send_otp(email, otp):
    """Send OTP using simple SMTP method"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("[ERROR] SMTP settings are not configured. Check EMAIL_USER and EMAIL_PASSWORD.")
        return False

    try:
        print(f"Attempting to send OTP to {email}")
        print(f"SMTP User: {EMAIL_USER}")
        
        msg = f"Subject: Your OTP for Menstrual Tracker\n\n{otp} is your OTP for Menstrual Tracker. Valid for 5 minutes."
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, email, msg)
        server.quit()

        print(f"[SUCCESS] OTP sent successfully to {email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"[ERROR] SMTP Authentication Error: {e}")
        print("Check your Gmail credentials and app password")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"[ERROR] SMTP Connection Error: {e}")
        print("Check your internet connection")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        print(f"[ERROR] SMTP Recipients Refused Error: {e}")
        print("The recipient email was rejected by the server")
        return False
    except Exception as e:
        print(f"[ERROR] Error sending email: {type(e).__name__}: {e}")
        return False