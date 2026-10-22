import datetime
from bson import ObjectId

def serialize_doc(doc, hide_password=True):
    """
    Recursively converts MongoDB BSON objects (ObjectId, datetime)
    into standard JSON-serializable Python data structures.
    """
    if doc is None:
        return None

    if isinstance(doc, list):
        return [serialize_doc(item, hide_password=hide_password) for item in doc]

    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if hide_password and key == "password":
                continue
            if key == "__v":
                continue
            result[key] = serialize_doc(value, hide_password=hide_password)
        return result

    if isinstance(doc, ObjectId):
        return str(doc)

    if isinstance(doc, (datetime.datetime, datetime.date)):
        if isinstance(doc, datetime.datetime) and doc.tzinfo is None:
            # Assume UTC for naïve MongoDB datetimes
            return doc.replace(tzinfo=datetime.timezone.utc).isoformat()
        return doc.isoformat()

    return doc

def sanitize_user(user_doc):
    """Sanitizes user document by removing password and serializing ObjectIds."""
    if not user_doc:
        return None
    return serialize_doc(user_doc, hide_password=True)
