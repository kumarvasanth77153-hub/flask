import re
import datetime
from flask import Blueprint, request, jsonify, g
from flask_server.db import get_db, to_object_id
from flask_server.middleware.auth import protect
from flask_server.utils.security import hash_password, check_password, generate_token
from flask_server.utils.serializers import sanitize_user

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$")

def validate_register_input(data):
    errors = []
    if not data.get("name") or not str(data["name"]).strip():
        errors.append("Full name is required")

    email = str(data.get("email", "")).strip()
    if not email or not EMAIL_REGEX.match(email):
        errors.append("A valid email address is required")

    password = str(data.get("password", ""))
    if not password or len(password) < 6:
        errors.append("Password must be at least 6 characters long")

    phone = str(data.get("phone", "")).strip()
    if not phone or len(phone) < 7:
        errors.append("A valid contact phone number is required")

    role = data.get("role")
    if role and role not in ["customer", "provider"]:
        errors.append("Public registration only supports customer and provider roles")

    lat = data.get("latitude")
    if lat is not None and lat != "":
        try:
            num_lat = float(lat)
            if num_lat < -90 or num_lat > 90:
                errors.append("Latitude must be a valid number between -90 and 90")
        except (ValueError, TypeError):
            errors.append("Latitude must be a valid number between -90 and 90")

    lng = data.get("longitude")
    if lng is not None and lng != "":
        try:
            num_lng = float(lng)
            if num_lng < -180 or num_lng > 180:
                errors.append("Longitude must be a valid number between -180 and 180")
        except (ValueError, TypeError):
            errors.append("Longitude must be a valid number between -180 and 180")

    return len(errors) == 0, errors

def validate_login_input(data):
    errors = []
    if not data.get("email") or not str(data["email"]).strip():
        errors.append("Email is required")
    if not data.get("password"):
        errors.append("Password is required")
    return len(errors) == 0, errors

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    is_valid, errors = validate_register_input(data)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": errors[0],
            "errors": errors,
        }), 400

    email = str(data["email"]).strip().lower()
    db = get_db()

    existing = db.users.find_one({"email": email})
    if existing:
        return jsonify({
            "success": False,
            "message": "An account with this email address already exists",
        }), 409

    hashed = hash_password(str(data["password"]))
    now = datetime.datetime.now(datetime.timezone.utc)

    user_doc = {
        "name": str(data["name"]).strip(),
        "email": email,
        "password": hashed,
        "phone": str(data["phone"]).strip(),
        "role": data.get("role", "customer"),
        "address": str(data.get("address", "")).strip(),
        "latitude": float(data["latitude"]) if data.get("latitude") is not None and data.get("latitude") != "" else None,
        "longitude": float(data["longitude"]) if data.get("longitude") is not None and data.get("longitude") != "" else None,
        "isActive": True,
        "createdAt": now,
        "updatedAt": now,
    }

    insert_result = db.users.insert_one(user_doc)
    user_doc["_id"] = insert_result.inserted_id

    token = generate_token(user_doc["_id"], user_doc["role"])

    return jsonify({
        "success": True,
        "message": "Account registered successfully",
        "token": token,
        "user": sanitize_user(user_doc),
    }), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    is_valid, errors = validate_login_input(data)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": errors[0],
            "errors": errors,
        }), 400

    email = str(data["email"]).strip().lower()
    password = str(data["password"])
    db = get_db()

    user = db.users.find_one({"email": email})
    if not user:
        return jsonify({
            "success": False,
            "message": "Invalid email or password credentials",
        }), 401

    if not user.get("isActive", True):
        return jsonify({
            "success": False,
            "message": "Account has been disabled. Please contact administrator.",
        }), 403

    if not check_password(password, user.get("password", "")):
        return jsonify({
            "success": False,
            "message": "Invalid email or password credentials",
        }), 401

    token = generate_token(user["_id"], user.get("role", "customer"))

    return jsonify({
        "success": True,
        "message": "Logged in successfully",
        "token": token,
        "user": sanitize_user(user),
    }), 200

@auth_bp.route("/me", methods=["GET"])
@protect
def get_me():
    user = g.current_user
    return jsonify({
        "success": True,
        "user": sanitize_user(user),
    }), 200

@auth_bp.route("/profile", methods=["PUT"])
@protect
def update_profile():
    data = request.get_json() or {}
    user = g.current_user
    db = get_db()

    update_fields = {"updatedAt": datetime.datetime.now(datetime.timezone.utc)}

    if "name" in data and data["name"]:
        update_fields["name"] = str(data["name"]).strip()
    if "phone" in data and data["phone"]:
        update_fields["phone"] = str(data["phone"]).strip()
    if "address" in data:
        update_fields["address"] = str(data["address"]).strip()
    if "latitude" in data:
        lat = data["latitude"]
        update_fields["latitude"] = float(lat) if lat is not None and lat != "" else None
    if "longitude" in data:
        lng = data["longitude"]
        update_fields["longitude"] = float(lng) if lng is not None and lng != "" else None

    db.users.update_one({"_id": user["_id"]}, {"$set": update_fields})
    updated_user = db.users.find_one({"_id": user["_id"]})

    # If provider, synchronize ProviderProfile coordinates & address
    if user.get("role") == "provider":
        prov_sync = {}
        if "address" in update_fields:
            prov_sync["address"] = update_fields["address"]
        if "latitude" in update_fields and update_fields["latitude"] is not None:
            prov_sync["latitude"] = update_fields["latitude"]
        if "longitude" in update_fields and update_fields["longitude"] is not None:
            prov_sync["longitude"] = update_fields["longitude"]
        if prov_sync:
            db.providerprofiles.update_one({"userId": user["_id"]}, {"$set": prov_sync})

    return jsonify({
        "success": True,
        "message": "Profile updated successfully",
        "user": sanitize_user(updated_user),
    }), 200
