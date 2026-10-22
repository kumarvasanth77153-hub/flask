import datetime
import re
from flask import Blueprint, request, jsonify, g
from flask_server.db import get_db, to_object_id, is_valid_object_id
from flask_server.middleware.auth import protect, authorize
from flask_server.utils.serializers import serialize_doc

admin_bp = Blueprint("admin", __name__)

# Enforce auth & admin role on all admin endpoints
@admin_bp.before_request
@protect
@authorize("admin")
def ensure_admin():
    pass

@admin_bp.route("/analytics", methods=["GET"])
def get_analytics():
    db = get_db()

    total_users = db.users.count_documents({})
    total_customers = db.users.count_documents({"role": "customer"})
    total_providers = db.users.count_documents({"role": "provider"})

    active_profiles = db.providerprofiles.count_documents({"isActive": True})
    available_providers = db.providerprofiles.count_documents({
        "isActive": True,
        "isAvailable": True,
        "availability": "Available",
    })

    total_categories = db.servicecategories.count_documents({"isActive": True})
    total_bookings = db.bookings.count_documents({})
    total_reviews = db.reviews.count_documents({})

    # Aggregate booking statuses & completed revenue
    status_agg = list(db.bookings.aggregate([
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "totalValue": {"$sum": "$serviceCharge"},
            }
        }
    ]))

    booking_status_map = {
        "Pending": 0,
        "Accepted": 0,
        "In Progress": 0,
        "Completed": 0,
        "Cancelled": 0,
        "Rejected": 0,
    }
    completed_revenue = 0

    for item in status_agg:
        st = item["_id"]
        if st in booking_status_map:
            booking_status_map[st] = item["count"]
        if st == "Completed":
            completed_revenue = item.get("totalValue", 0)

    # Aggregate platform average rating
    rating_agg = list(db.reviews.aggregate([
        {
            "$group": {
                "_id": None,
                "avgRating": {"$avg": "$rating"},
            }
        }
    ]))
    platform_avg_rating = round(float(rating_agg[0]["avgRating"]), 1) if rating_agg else 0

    # Recent 6 bookings
    raw_recent_bookings = list(db.bookings.find().sort("createdAt", -1).limit(6))
    recent_bookings = []
    for b in raw_recent_bookings:
        b_dict = dict(b)
        cust = db.users.find_one({"_id": to_object_id(b.get("customerId"))})
        if cust:
            b_dict["customerId"] = {
                "_id": cust["_id"],
                "name": cust.get("name"),
                "email": cust.get("email"),
                "phone": cust.get("phone"),
            }
        prov = db.providerprofiles.find_one({"_id": to_object_id(b.get("providerId"))})
        if prov:
            p_dict = dict(prov)
            p_user = db.users.find_one({"_id": to_object_id(prov.get("userId"))})
            p_dict["userId"] = {
                "_id": p_user["_id"],
                "name": p_user.get("name"),
                "email": p_user.get("email"),
            } if p_user else None
            b_dict["providerId"] = p_dict
        cat = db.servicecategories.find_one({"_id": to_object_id(b.get("serviceCategory"))})
        if cat:
            b_dict["serviceCategory"] = {
                "_id": cat["_id"],
                "name": cat.get("name"),
                "icon": cat.get("icon"),
            }
        recent_bookings.append(b_dict)

    # Recent 5 reviews
    raw_recent_reviews = list(db.reviews.find().sort("createdAt", -1).limit(5))
    recent_reviews = []
    for r in raw_recent_reviews:
        r_dict = dict(r)
        cust = db.users.find_one({"_id": to_object_id(r.get("customerId"))})
        if cust:
            r_dict["customerId"] = {"_id": cust["_id"], "name": cust.get("name")}
        prov = db.providerprofiles.find_one({"_id": to_object_id(r.get("providerId"))})
        if prov:
            p_user = db.users.find_one({"_id": to_object_id(prov.get("userId"))})
            r_dict["providerId"] = {
                "_id": prov["_id"],
                "userId": {"name": p_user.get("name") if p_user else ""},
            }
        recent_reviews.append(r_dict)

    return jsonify({
        "success": True,
        "data": {
            "users": {
                "total": total_users,
                "customers": total_customers,
                "providers": total_providers,
            },
            "workforce": {
                "totalProfiles": active_profiles,
                "currentlyAvailable": available_providers,
            },
            "services": {
                "activeCategories": total_categories,
            },
            "bookings": {
                "total": total_bookings,
                "completedRevenue": completed_revenue,
                "statusBreakdown": booking_status_map,
            },
            "reputation": {
                "totalReviews": total_reviews,
                "averageRating": platform_avg_rating,
            },
            "recentBookings": serialize_doc(recent_bookings),
            "recentReviews": serialize_doc(recent_reviews),
        },
    }), 200

@admin_bp.route("/users", methods=["GET"])
def get_users():
    role_arg = request.args.get("role")
    status_arg = request.args.get("status")
    search_arg = request.args.get("search", "").strip()

    query = {}
    if role_arg and role_arg in ["customer", "provider", "admin"]:
        query["role"] = role_arg

    if status_arg is not None:
        query["isActive"] = status_arg.lower() == "active"

    if search_arg:
        regex_term = {"$regex": re.escape(search_arg), "$options": "i"}
        query["$or"] = [
            {"name": regex_term},
            {"email": regex_term},
            {"phone": regex_term},
        ]

    db = get_db()
    users = list(db.users.find(query, {"password": 0}).sort("createdAt", -1))

    return jsonify({
        "success": True,
        "count": len(users),
        "data": serialize_doc(users),
    }), 200

@admin_bp.route("/users/<user_id>/toggle-status", methods=["PUT"])
def toggle_user_status(user_id):
    if not is_valid_object_id(user_id):
        return jsonify({
            "success": False,
            "message": "Target user record not found",
        }), 404

    db = get_db()
    target_user = db.users.find_one({"_id": to_object_id(user_id)})
    if not target_user:
        return jsonify({
            "success": False,
            "message": "Target user record not found",
        }), 404

    # Security policy: admin cannot suspend their own active account
    if str(target_user["_id"]) == str(g.current_user["_id"]):
        return jsonify({
            "success": False,
            "message": "Security policy: Administrators cannot suspend their own active account",
        }), 400

    new_active = not target_user.get("isActive", True)
    now = datetime.datetime.now(datetime.timezone.utc)

    db.users.update_one(
        {"_id": target_user["_id"]},
        {"$set": {"isActive": new_active, "updatedAt": now}},
    )

    # If provider, synchronize ProviderProfile status
    if target_user.get("role") == "provider":
        db.providerprofiles.update_one(
            {"userId": target_user["_id"]},
            {"$set": {"isActive": new_active, "updatedAt": now}},
        )

    return jsonify({
        "success": True,
        "message": f"User account has been {'activated' if new_active else 'suspended'}",
        "data": {
            "id": str(target_user["_id"]),
            "name": target_user.get("name"),
            "isActive": new_active,
        },
    }), 200

@admin_bp.route("/providers", methods=["GET"])
def get_providers():
    cat_arg = request.args.get("category")
    is_avail_arg = request.args.get("isAvailable")
    is_active_arg = request.args.get("isActive")

    query = {}
    if cat_arg and is_valid_object_id(cat_arg):
        query["serviceCategory"] = to_object_id(cat_arg)

    if is_avail_arg is not None:
        query["isAvailable"] = is_avail_arg.lower() == "true"

    if is_active_arg is not None:
        query["isActive"] = is_active_arg.lower() == "true"

    db = get_db()
    raw_providers = list(db.providerprofiles.find(query).sort("createdAt", -1))

    populated = []
    for prov in raw_providers:
        p_dict = dict(prov)
        user = db.users.find_one({"_id": to_object_id(prov.get("userId"))})
        if user:
            p_dict["userId"] = {
                "_id": user["_id"],
                "name": user.get("name"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "address": user.get("address"),
                "isActive": user.get("isActive", True),
            }
        cat = db.servicecategories.find_one({"_id": to_object_id(prov.get("serviceCategory"))})
        if cat:
            p_dict["serviceCategory"] = {
                "_id": cat["_id"],
                "name": cat.get("name"),
                "icon": cat.get("icon"),
            }
        populated.append(p_dict)

    return jsonify({
        "success": True,
        "count": len(populated),
        "data": serialize_doc(populated),
    }), 200

@admin_bp.route("/providers/<provider_id>/toggle-status", methods=["PUT"])
def toggle_provider_status(provider_id):
    if not is_valid_object_id(provider_id):
        return jsonify({
            "success": False,
            "message": "Provider profile record not found",
        }), 404

    db = get_db()
    prov = db.providerprofiles.find_one({"_id": to_object_id(provider_id)})
    if not prov:
        return jsonify({
            "success": False,
            "message": "Provider profile record not found",
        }), 404

    new_active = not prov.get("isActive", True)
    now = datetime.datetime.now(datetime.timezone.utc)

    db.providerprofiles.update_one(
        {"_id": prov["_id"]},
        {"$set": {"isActive": new_active, "updatedAt": now}},
    )

    user = db.users.find_one({"_id": to_object_id(prov.get("userId"))})

    return jsonify({
        "success": True,
        "message": f"Provider status updated to {'Verified / Active' if new_active else 'Suspended / Inactive'}",
        "data": {
            "id": str(prov["_id"]),
            "name": user.get("name") if user else "",
            "isActive": new_active,
        },
    }), 200

@admin_bp.route("/bookings", methods=["GET"])
def get_bookings():
    status_arg = request.args.get("status")
    limit_arg = request.args.get("limit", "50")

    query = {}
    if status_arg and status_arg != "all":
        query["status"] = status_arg

    try:
        limit_val = int(limit_arg)
    except (ValueError, TypeError):
        limit_val = 50

    db = get_db()
    raw_bookings = list(db.bookings.find(query).sort("createdAt", -1).limit(limit_val))

    populated = []
    for b in raw_bookings:
        b_dict = dict(b)
        cust = db.users.find_one({"_id": to_object_id(b.get("customerId"))})
        if cust:
            b_dict["customerId"] = {
                "_id": cust["_id"],
                "name": cust.get("name"),
                "email": cust.get("email"),
                "phone": cust.get("phone"),
                "address": cust.get("address"),
            }
        prov = db.providerprofiles.find_one({"_id": to_object_id(b.get("providerId"))})
        if prov:
            p_dict = dict(prov)
            p_user = db.users.find_one({"_id": to_object_id(prov.get("userId"))})
            if p_user:
                p_dict["userId"] = {
                    "_id": p_user["_id"],
                    "name": p_user.get("name"),
                    "email": p_user.get("email"),
                    "phone": p_user.get("phone"),
                }
            b_dict["providerId"] = p_dict
        cat = db.servicecategories.find_one({"_id": to_object_id(b.get("serviceCategory"))})
        if cat:
            b_dict["serviceCategory"] = {
                "_id": cat["_id"],
                "name": cat.get("name"),
                "icon": cat.get("icon"),
            }
        populated.append(b_dict)

    return jsonify({
        "success": True,
        "count": len(populated),
        "data": serialize_doc(populated),
    }), 200
