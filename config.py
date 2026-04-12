# config.py
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# Firebase setup from environment variable
firebase_key_json = os.getenv('FIREBASE_KEY')
if not firebase_key_json:
    raise ValueError("FIREBASE_KEY environment variable is not set. Please set it with your Firebase service account credentials.")

try:
    firebase_key_dict = json.loads(os.environ["FIREBASE_KEY"])
    firebase_key_dict["private_key"] = firebase_key["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(firebase_key_dict)
    firebase_admin.initialize_app(cred)
except json.JSONDecodeError as e:
    raise ValueError(f"FIREBASE_KEY is not valid JSON: {e}")
except Exception as e:
    raise ValueError(f"Failed to initialize Firebase: {e}")

db = firestore.client()

# Admin users configuration
ADMIN_USERS = os.getenv('ADMIN_USER', '').split(',') if os.getenv('ADMIN_USER') else []
ADMIN_USERS = [email.strip() for email in ADMIN_USERS]

# View password (shared analytics access)
VIEW_PASS = os.getenv('VIEW_PASS', 'Mokesh87654321')
