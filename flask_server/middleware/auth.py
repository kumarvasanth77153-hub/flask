from functools import wraps
from flask import request, jsonify, g
from flask_server.db import get_db, to_object_id
from flask_server.utils.security import decode_token

def protect(f):
    """
    Decorator that verifies the JWT token from Authorization header
    and attaches current active user to Flask's request context `g.current_user`.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header and auth_header.startswith("Bearer "):
            parts = auth_header.split(" ")
            if len(parts) == 2:
                token = parts[1]

        if not token:
            return jsonify({
                "success": False,
                "message": "Not authorized - No token provided",
            }), 401

        try:
            payload = decode_token(token)
            user_id = payload.get("id")
            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "Not authorized - Invalid or expired token",
                }), 401

            db = get_db()
            user = db.users.find_one({"_id": to_object_id(user_id)})

            if not user:
                return jsonify({
                    "success": False,
                    "message": "The user belonging to this token no longer exists",
                }), 401

            if not user.get("isActive", True):
                return jsonify({
                    "success": False,
                    "message": "Account is deactivated. Please contact support.",
                }), 403

            # Store user in Flask request global
            g.current_user = user
            return f(*args, **kwargs)

        except Exception as e:
            return jsonify({
                "success": False,
                "message": "Not authorized - Invalid or expired token",
            }), 401

    return decorated

def authorize(*roles):
    """
    Decorator that checks if authenticated user possesses one of the allowed roles.
    Must be applied along with @protect.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user or user.get("role") not in roles:
                role_name = user.get("role") if user else "anonymous"
                return jsonify({
                    "success": False,
                    "message": f"User role '{role_name}' is not authorized to access this resource",
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
