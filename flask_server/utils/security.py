import datetime
import bcrypt
import jwt
from flask_server.config import Config

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def check_password(password: str, hashed_password: str) -> bool:
    """Compares a plaintext password with a bcrypt hash."""
    if not password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def generate_token(user_id, role: str) -> str:
    """Generates a signed JWT token valid for 30 days matching Node.js jwt.sign."""
    payload = {
        "id": str(user_id),
        "role": role,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30),
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")
    return token

def decode_token(token: str):
    """Decodes and validates a JWT token. Returns payload dict or raises Exception."""
    return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
