import re
import datetime
from flask import Blueprint, request, jsonify
from flask_server.db import get_db, to_object_id, is_valid_object_id
from flask_server.middleware.auth import protect, authorize
from flask_server.utils.serializers import serialize_doc

category_bp = Blueprint("categories", __name__)

def validate_category_input(data):
    errors = []
    if not data.get("name") or not str(data["name"]).strip():
        errors.append("Category name is required")
    if not data.get("description") or not str(data["description"]).strip():
        errors.append("Category description is required")
    return len(errors) == 0, errors

@category_bp.route("", methods=["GET"])
@category_bp.route("/", methods=["GET"])
def get_categories():
    db = get_db()
    cats = list(db.servicecategories.find({"isActive": True}).sort("name", 1))
    return jsonify({
        "success": True,
        "count": len(cats),
        "data": serialize_doc(cats),
    }), 200

@category_bp.route("/<category_id>", methods=["GET"])
def get_category_by_id(category_id):
    if not is_valid_object_id(category_id):
        return jsonify({
            "success": False,
            "message": "Service category not found",
        }), 404

    db = get_db()
    cat = db.servicecategories.find_one({"_id": to_object_id(category_id)})
    if not cat:
        return jsonify({
            "success": False,
            "message": "Service category not found",
        }), 404

    return jsonify({
        "success": True,
        "data": serialize_doc(cat),
    }), 200

@category_bp.route("", methods=["POST"])
@category_bp.route("/", methods=["POST"])
@protect
@authorize("admin")
def create_category():
    data = request.get_json() or {}
    is_valid, errors = validate_category_input(data)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": errors[0],
            "errors": errors,
        }), 400

    name = str(data["name"]).strip()
    db = get_db()

    # Case-insensitive duplicate check
    existing = db.servicecategories.find_one({
        "name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}
    })
    if existing:
        return jsonify({
            "success": False,
            "message": "A category with this name already exists",
        }), 409

    now = datetime.datetime.now(datetime.timezone.utc)
    cat_doc = {
        "name": name,
        "description": str(data["description"]).strip(),
        "icon": str(data.get("icon", "Wrench")).strip() or "Wrench",
        "isActive": True,
        "createdAt": now,
        "updatedAt": now,
    }

    res = db.servicecategories.insert_one(cat_doc)
    cat_doc["_id"] = res.inserted_id

    return jsonify({
        "success": True,
        "message": "Service category created successfully",
        "data": serialize_doc(cat_doc),
    }), 201

@category_bp.route("/<category_id>", methods=["PUT"])
@protect
@authorize("admin")
def update_category(category_id):
    if not is_valid_object_id(category_id):
        return jsonify({
            "success": False,
            "message": "Service category not found",
        }), 404

    db = get_db()
    cat = db.servicecategories.find_one({"_id": to_object_id(category_id)})
    if not cat:
        return jsonify({
            "success": False,
            "message": "Service category not found",
        }), 404

    data = request.get_json() or {}
    update_fields = {"updatedAt": datetime.datetime.now(datetime.timezone.utc)}

    if "name" in data and data["name"]:
        update_fields["name"] = str(data["name"]).strip()
    if "description" in data and data["description"]:
        update_fields["description"] = str(data["description"]).strip()
    if "icon" in data and data["icon"]:
        update_fields["icon"] = str(data["icon"]).strip()
    if "isActive" in data:
        update_fields["isActive"] = bool(data["isActive"])

    db.servicecategories.update_one({"_id": cat["_id"]}, {"$set": update_fields})
    updated = db.servicecategories.find_one({"_id": cat["_id"]})

    return jsonify({
        "success": True,
        "message": "Service category updated successfully",
        "data": serialize_doc(updated),
    }), 200

@category_bp.route("/<category_id>", methods=["DELETE"])
@protect
@authorize("admin")
def delete_category(category_id):
    if not is_valid_object_id(category_id):
        return jsonify({
            "success": False,
            "message": "Service category not found",
        }), 404

    db = get_db()
    cat = db.servicecategories.find_one({"_id": to_object_id(category_id)})
    if not cat:
        return jsonify({
            "success": False,
            "message": "Service category not found",
        }), 404

    db.servicecategories.update_one(
        {"_id": cat["_id"]},
        {"$set": {"isActive": False, "updatedAt": datetime.datetime.now(datetime.timezone.utc)}}
    )

    return jsonify({
        "success": True,
        "message": "Service category deactivated successfully",
    }), 200
