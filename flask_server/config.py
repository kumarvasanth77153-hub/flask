import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    PORT = int(os.environ.get("PORT", 5000))
    MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017/local_service_db")
    DB_NAME = os.environ.get("DB_NAME", "local_service_db")
    JWT_SECRET = os.environ.get("JWT_SECRET", "super_secret_jwt_key_urbanaid_2025_secure_token")
    SECRET_KEY = os.environ.get("SECRET_KEY", "urbanaid_super_secret_session_key_2026_flask")
    CLIENT_URL = os.environ.get("CLIENT_URL", "http://localhost:5173")
    NODE_ENV = os.environ.get("NODE_ENV", "development")
    DEBUG = NODE_ENV == "development"
