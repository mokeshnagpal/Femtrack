# config.py
import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# Firebase setup
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# Admin users configuration
ADMIN_USERS = os.getenv('ADMIN_USER', '').split(',') if os.getenv('ADMIN_USER') else []
ADMIN_USERS = [email.strip() for email in ADMIN_USERS]

# View password (shared analytics access)
VIEW_PASS = os.getenv('VIEW_PASS', 'Mokesh87654321')