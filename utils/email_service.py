# utils/email_service.py
import smtplib
from config import EMAIL_USER, EMAIL_PASSWORD

def send_otp(email, otp):
    """Send OTP using simple SMTP method"""
    try:
        print(f"Attempting to send OTP to {email}")
        print(f"SMTP User: {EMAIL_USER}")
        
        # Create simple message format
        msg = f"Subject: Your OTP for Menstrual Tracker\n\n{otp} is your OTP for Menstrual Tracker. Valid for 5 minutes."
        
        # Connect to SMTP server
        print("Connecting to SMTP server...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)  # Enable debug output
        
        print("Starting TLS...")
        server.starttls()
        
        print(f"Logging in with {EMAIL_USER}...")
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        
        print(f"Sending email to {email}...")
        server.sendmail(EMAIL_USER, email, msg)
        
        print("Quitting server...")
        server.quit()
        
        print(f"✓ OTP sent successfully to {email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ SMTP Authentication Error: {e}")
        print("Check your Gmail credentials and app password")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"✗ SMTP Connection Error: {e}")
        print("Check your internet connection")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        print(f"✗ SMTP Recipients Refused Error: {e}")
        print("The recipient email was rejected by the server")
        return False
    except Exception as e:
        print(f"✗ Error sending email: {type(e).__name__}: {e}")
        return False
        print("The recipient email address was rejected")
        return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False