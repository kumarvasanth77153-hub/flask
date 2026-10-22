import datetime
from flask import Blueprint, request, jsonify, g
from flask_server.db import get_db
from flask_server.middleware.auth import protect, authorize
from flask_server.utils.serializers import sanitize_user

customer_bp = Blueprint("customers", __name__)

@customer_bp.route("/profile", methods=["GET"])
@protect
@authorize("customer")
def get_customer_profile():
    return jsonify({
        "success": True,
        "data": sanitize_user(g.current_user),
    }), 200

@customer_bp.route("/profile", methods=["PUT"])
@protect
@authorize("customer")
def update_customer_profile():
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
    updated = db.users.find_one({"_id": user["_id"]})

    return jsonify({
        "success": True,
        "message": "Customer profile updated successfully",
        "data": sanitize_user(updated),
    }), 200
