import pymongo
from bson import ObjectId
from bson.errors import InvalidId
from flask_server.config import Config

_client = None
_db = None

def get_client():
    global _client
    if _client is None:
        try:
            import certifi
            _client = pymongo.MongoClient(
                Config.MONGODB_URI,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=8000
            )
        except Exception:
            _client = pymongo.MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=8000
            )
    return _client

def get_db():
    global _db
    if _db is None:
        client = get_client()
        # Parse db name from URI or use Config.DB_NAME
        try:
            default_db_name = client.get_default_database().name
        except Exception:
            default_db_name = Config.DB_NAME
        _db = client[default_db_name or Config.DB_NAME]
    return _db

def to_object_id(val):
    """Safely converts string or ObjectId to ObjectId. Returns None if invalid."""
    if val is None:
        return None
    if isinstance(val, ObjectId):
        return val
    try:
        return ObjectId(str(val))
    except (InvalidId, ValueError, TypeError):
        return None

def is_valid_object_id(val):
    """Checks if a string or value is a valid 24-character hexadecimal ObjectId."""
    if not val:
        return False
    if isinstance(val, ObjectId):
        return True
    try:
        ObjectId(str(val))
        return True
    except (InvalidId, ValueError, TypeError):
        return False

def init_indexes():
    """Ensure essential database indexes exist for performance."""
    try:
        db = get_db()
        db.users.create_index([("email", pymongo.ASCENDING)], unique=True)
        db.providerprofiles.create_index([("userId", pymongo.ASCENDING)], unique=True)
        db.providerprofiles.create_index([("serviceCategory", pymongo.ASCENDING), ("isAvailable", pymongo.ASCENDING), ("isActive", pymongo.ASCENDING)])
        db.providerprofiles.create_index([("latitude", pymongo.ASCENDING), ("longitude", pymongo.ASCENDING)])
        db.servicecategories.create_index([("name", pymongo.ASCENDING)], unique=True)
        db.bookings.create_index([("customerId", pymongo.ASCENDING), ("status", pymongo.ASCENDING)])
        db.bookings.create_index([("providerId", pymongo.ASCENDING), ("status", pymongo.ASCENDING)])
        db.bookings.create_index([("createdAt", pymongo.DESCENDING)])
        db.reviews.create_index([("bookingId", pymongo.ASCENDING)], unique=True)
        db.reviews.create_index([("providerId", pymongo.ASCENDING), ("createdAt", pymongo.DESCENDING)])
        db.reviews.create_index([("customerId", pymongo.ASCENDING)])
        print("[DB] MongoDB indexes ensured successfully.")
    except Exception as e:
        print(f"[DB] Index initialization note: {e}")
