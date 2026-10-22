import datetime
from flask import Blueprint, request, jsonify, g
from flask_server.db import get_db, to_object_id, is_valid_object_id
from flask_server.middleware.auth import protect, authorize
from flask_server.utils.serializers import serialize_doc

booking_bp = Blueprint("bookings", __name__)

VALID_TRANSITIONS = {
    "Pending": {
        "Accepted": ["provider"],
        "Rejected": ["provider"],
        "Cancelled": ["customer"],
    },
    "Accepted": {
        "In Progress": ["provider"],
        "Cancelled": ["customer"],
    },
    "In Progress": {
        "Completed": ["provider"],
    },
    "Completed": {},
    "Cancelled": {},
    "Rejected": {},
}

def validate_status_transition(current_status, new_status, user_role):
    if current_status not in VALID_TRANSITIONS:
        return False, f"Unknown current status: {current_status}"

    allowed_roles = VALID_TRANSITIONS[current_status].get(new_status)
    if allowed_roles is None:
        return False, f"Invalid status transition from '{current_status}' to '{new_status}'."

    if user_role not in allowed_roles and user_role != "admin":
        return False, f"User role '{user_role}' is not authorized to transition booking to '{new_status}'."

    return True, None

def populate_booking(booking, db):
    if not booking:
        return None
    b = dict(booking)

    # Populate customerId
    if "customerId" in b and b["customerId"]:
        cust = db.users.find_one({"_id": to_object_id(b["customerId"])})
        if cust:
            b["customerId"] = {
                "_id": cust["_id"],
                "name": cust.get("name"),
                "email": cust.get("email"),
                "phone": cust.get("phone"),
                "address": cust.get("address"),
                "latitude": cust.get("latitude"),
                "longitude": cust.get("longitude"),
            }

    # Populate providerId with nested userId
    if "providerId" in b and b["providerId"]:
        prov = db.providerprofiles.find_one({"_id": to_object_id(b["providerId"])})
        if prov:
            prov_dict = dict(prov)
            if "userId" in prov_dict and prov_dict["userId"]:
                p_user = db.users.find_one({"_id": to_object_id(prov_dict["userId"])})
                if p_user:
                    prov_dict["userId"] = {
                        "_id": p_user["_id"],
                        "name": p_user.get("name"),
                        "email": p_user.get("email"),
                        "phone": p_user.get("phone"),
                        "address": p_user.get("address"),
                    }
            b["providerId"] = prov_dict

    # Populate serviceCategory
    if "serviceCategory" in b and b["serviceCategory"]:
        cat = db.servicecategories.find_one({"_id": to_object_id(b["serviceCategory"])})
        if cat:
            b["serviceCategory"] = {
                "_id": cat["_id"],
                "name": cat.get("name"),
                "icon": cat.get("icon"),
            }

    return b

def validate_create_booking(data):
    errors = []
    pid = data.get("providerId")
    if not pid or not is_valid_object_id(pid):
        errors.append("A valid provider ID is required")

    if not data.get("date") or not str(data["date"]).strip():
        errors.append("Service booking date is required")

    if not data.get("time") or not str(data["time"]).strip():
        errors.append("Preferred service time slot is required")

    if not data.get("address") or not str(data["address"]).strip():
        errors.append("Service delivery address is required")

    lat = data.get("latitude")
    if lat is None or lat == "":
        errors.append("Customer latitude coordinate is required")
    else:
        try:
            num_lat = float(lat)
            if num_lat < -90 or num_lat > 90:
                errors.append("Latitude must be between -90 and 90")
        except (ValueError, TypeError):
            errors.append("Latitude must be between -90 and 90")

    lng = data.get("longitude")
    if lng is None or lng == "":
        errors.append("Customer longitude coordinate is required")
    else:
        try:
            num_lng = float(lng)
            if num_lng < -180 or num_lng > 180:
                errors.append("Longitude must be between -180 and 180")
        except (ValueError, TypeError):
            errors.append("Longitude must be between -180 and 180")

    desc = data.get("description", "")
    if not desc or len(str(desc).strip()) < 5:
        errors.append("Please describe the service requirement / problem in at least 5 characters")

    return len(errors) == 0, errors

@booking_bp.route("", methods=["POST"])
@booking_bp.route("/", methods=["POST"])
@protect
@authorize("customer")
def create_booking():
    data = request.get_json() or {}
    is_valid, errors = validate_create_booking(data)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": errors[0],
            "errors": errors,
        }), 400

    db = get_db()
    prov_id = to_object_id(data["providerId"])
    prov = db.providerprofiles.find_one({"_id": prov_id})

    if not prov or not prov.get("isActive", True):
        return jsonify({
            "success": False,
            "message": "The requested service provider is inactive or does not exist",
        }), 404

    # Verify provider user is active
    prov_user = db.users.find_one({"_id": to_object_id(prov["userId"])})
    if not prov_user or not prov_user.get("isActive", True):
        return jsonify({
            "success": False,
            "message": "The requested service provider is inactive or does not exist",
        }), 404

    # Availability check
    if not prov.get("isAvailable", True) or prov.get("availability") != "Available":
        return jsonify({
            "success": False,
            "message": "This provider is currently off-duty or busy and cannot accept new bookings",
        }), 400

    # Self-booking prevention guard
    if str(prov["userId"]) == str(g.current_user["_id"]):
        return jsonify({
            "success": False,
            "message": "You cannot create a service booking request with your own account",
        }), 400

    now = datetime.datetime.now(datetime.timezone.utc)
    booking_doc = {
        "customerId": g.current_user["_id"],
        "providerId": prov["_id"],
        "serviceCategory": prov["serviceCategory"],
        "date": str(data["date"]).strip(),
        "time": str(data["time"]).strip(),
        "address": str(data["address"]).strip(),
        "latitude": float(data["latitude"]),
        "longitude": float(data["longitude"]),
        "description": str(data["description"]).strip(),
        "serviceCharge": float(prov.get("serviceCharge", 300)),
        "status": "Pending",
        "cancellationReason": "",
        "rejectionReason": "",
        "isReviewed": False,
        "reviewId": None,
        "createdAt": now,
        "updatedAt": now,
    }

    res = db.bookings.insert_one(booking_doc)
    booking_doc["_id"] = res.inserted_id

    populated = populate_booking(booking_doc, db)

    return jsonify({
        "success": True,
        "message": "Booking request created successfully. Awaiting provider confirmation.",
        "data": serialize_doc(populated),
    }), 201

@booking_bp.route("/my", methods=["GET"])
@protect
@authorize("customer")
def get_my_customer_bookings():
    db = get_db()
    status_filter = request.args.get("status")

    query = {"customerId": g.current_user["_id"]}
    if status_filter and status_filter != "all":
        query["status"] = status_filter

    bookings = list(db.bookings.find(query).sort("createdAt", -1))
    populated_list = [populate_booking(b, db) for b in bookings]

    return jsonify({
        "success": True,
        "count": len(populated_list),
        "data": serialize_doc(populated_list),
    }), 200

@booking_bp.route("/provider", methods=["GET"])
@protect
@authorize("provider")
def get_provider_bookings():
    db = get_db()
    prov = db.providerprofiles.find_one({"userId": g.current_user["_id"]})
    if not prov:
        return jsonify({
            "success": False,
            "message": "Provider profile not found for this account",
        }), 404

    status_filter = request.args.get("status")
    query = {"providerId": prov["_id"]}
    if status_filter and status_filter != "all":
        query["status"] = status_filter

    bookings = list(db.bookings.find(query).sort("createdAt", -1))
    populated_list = [populate_booking(b, db) for b in bookings]

    return jsonify({
        "success": True,
        "count": len(populated_list),
        "data": serialize_doc(populated_list),
    }), 200

@booking_bp.route("/<booking_id>", methods=["GET"])
@protect
def get_booking_by_id(booking_id):
    if not is_valid_object_id(booking_id):
        return jsonify({
            "success": False,
            "message": "Booking not found",
        }), 404

    db = get_db()
    booking = db.bookings.find_one({"_id": to_object_id(booking_id)})
    if not booking:
        return jsonify({
            "success": False,
            "message": "Booking not found",
        }), 404

    prov = db.providerprofiles.find_one({"_id": to_object_id(booking["providerId"])})

    is_customer = str(booking["customerId"]) == str(g.current_user["_id"])
    is_provider = prov and str(prov.get("userId")) == str(g.current_user["_id"])
    is_admin = g.current_user.get("role") == "admin"

    if not is_customer and not is_provider and not is_admin:
        return jsonify({
            "success": False,
            "message": "Not authorized to view this booking",
        }), 403

    populated = populate_booking(booking, db)
    return jsonify({
        "success": True,
        "data": serialize_doc(populated),
    }), 200

@booking_bp.route("/<booking_id>/status", methods=["PUT"])
@protect
def update_booking_status(booking_id):
    if not is_valid_object_id(booking_id):
        return jsonify({
            "success": False,
            "message": "Booking not found",
        }), 404

    data = request.get_json() or {}
    target_status = data.get("status")
    reason = data.get("reason", "")

    if not target_status:
        return jsonify({
            "success": False,
            "message": "Target booking status is required",
        }), 400

    db = get_db()
    booking = db.bookings.find_one({"_id": to_object_id(booking_id)})
    if not booking:
        return jsonify({
            "success": False,
            "message": "Booking not found",
        }), 404

    prov = db.providerprofiles.find_one({"_id": to_object_id(booking["providerId"])})

    is_customer = str(booking["customerId"]) == str(g.current_user["_id"])
    is_provider = prov and str(prov.get("userId")) == str(g.current_user["_id"])
    is_admin = g.current_user.get("role") == "admin"

    if not is_customer and not is_provider and not is_admin:
        return jsonify({
            "success": False,
            "message": "You are not authorized to update this booking",
        }), 403

    caller_role = "admin" if is_admin else ("provider" if is_provider else "customer")

    is_valid, err_msg = validate_status_transition(booking.get("status"), target_status, caller_role)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": err_msg,
        }), 400

    update_fields = {
        "status": target_status,
        "updatedAt": datetime.datetime.now(datetime.timezone.utc),
    }

    if target_status == "Rejected" and reason:
        update_fields["rejectionReason"] = reason

    if target_status == "Cancelled" and reason:
        update_fields["cancellationReason"] = reason

    db.bookings.update_one({"_id": booking["_id"]}, {"$set": update_fields})
    updated = db.bookings.find_one({"_id": booking["_id"]})
    populated = populate_booking(updated, db)

    return jsonify({
        "success": True,
        "message": f"Booking status updated to '{target_status}' successfully",
        "data": serialize_doc(populated),
    }), 200

@booking_bp.route("/<booking_id>/cancel", methods=["PUT"])
@protect
@authorize("customer")
def cancel_booking(booking_id):
    data = request.get_json() or {}
    data["status"] = "Cancelled"
    # Forward to update status handler
    return update_booking_status(booking_id)
