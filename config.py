# config.py
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Ensure the .env is loaded from this project directory
ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(ENV_PATH)

# Firebase setup from environment variable only
firebase_credentials_str = os.environ.get('FIREBASE_CREDENTIALS')

if not firebase_credentials_str:
    raise ValueError("FIREBASE_CREDENTIALS environment variable is required. Set it in .env or Render environment settings.")

try:
    firebase_credentials_dict = json.loads(firebase_credentials_str)

    # Fix newline escape sequences in private_key
    if 'private_key' in firebase_credentials_dict:
        pk = firebase_credentials_dict['private_key']
        # Replace escaped newlines (\\n in JSON) with actual newlines
        firebase_credentials_dict['private_key'] = pk.replace('\\n', '\n')

    cred = credentials.Certificate(firebase_credentials_dict)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

except json.JSONDecodeError as e:
    raise ValueError(f"FIREBASE_CREDENTIALS is not valid JSON: {e}")
except Exception as e:
    raise ValueError(f"Failed to initialize Firebase: {e}")


# Firestore DB
db = firestore.client()

# Admin users configuration
ADMIN_USERS = os.getenv('ADMIN_USER', '').split(',') if os.getenv('ADMIN_USER') else []
ADMIN_USERS = [email.strip() for email in ADMIN_USERS]

# View password (shared analytics access)
VIEW_PASS = os.getenv('VIEW_PASS', 'Mokesh87654321')