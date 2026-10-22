import datetime
from flask import Blueprint, request, jsonify, g
from flask_server.db import get_db, to_object_id, is_valid_object_id
from flask_server.middleware.auth import protect, authorize
from flask_server.utils.serializers import serialize_doc

review_bp = Blueprint("reviews", __name__)

def recalculate_provider_rating(provider_id, db):
    pipeline = [
        {"$match": {"providerId": to_object_id(provider_id)}},
        {
            "$group": {
                "_id": "$providerId",
                "averageRating": {"$avg": "$rating"},
                "totalReviews": {"$sum": 1},
            }
        },
    ]
    stats = list(db.reviews.aggregate(pipeline))
    if stats:
        avg = round(float(stats[0]["averageRating"]), 1)
        total = int(stats[0]["totalReviews"])
        db.providerprofiles.update_one(
            {"_id": to_object_id(provider_id)},
            {"$set": {"averageRating": avg, "totalReviews": total}},
        )
        return avg, total
    else:
        db.providerprofiles.update_one(
            {"_id": to_object_id(provider_id)},
            {"$set": {"averageRating": 0, "totalReviews": 0}},
        )
        return 0, 0

def validate_create_review(data):
    errors = []
    bid = data.get("bookingId")
    if not bid:
        errors.append("Booking ID is required")
    elif not is_valid_object_id(bid):
        errors.append("Invalid booking ID format")

    rating = data.get("rating")
    if rating is None or rating == "":
        errors.append("Rating is required")
    else:
        try:
            num_rating = float(rating)
            if num_rating < 1 or num_rating > 5:
                errors.append("Rating must be an integer or number between 1 and 5 stars")
        except (ValueError, TypeError):
            errors.append("Rating must be an integer or number between 1 and 5 stars")

    comment = data.get("comment")
    if not comment or not isinstance(comment, str) or not comment.strip():
        errors.append("Review comment is required")
    elif len(comment.strip()) < 3:
        errors.append("Review comment must be at least 3 characters long")
    elif len(comment.strip()) > 1000:
        errors.append("Review comment cannot exceed 1000 characters")

    return len(errors) == 0, errors

@review_bp.route("", methods=["POST"])
@review_bp.route("/", methods=["POST"])
@protect
@authorize("customer")
def create_review():
    data = request.get_json() or {}
    is_valid, errors = validate_create_review(data)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": errors[0],
            "errors": errors,
        }), 400

    db = get_db()
    booking_id = to_object_id(data["bookingId"])
    booking = db.bookings.find_one({"_id": booking_id})

    if not booking:
        return jsonify({
            "success": False,
            "message": "The specified service booking record does not exist",
        }), 404

    # Verified Customer Integrity
    if str(booking["customerId"]) != str(g.current_user["_id"]):
        return jsonify({
            "success": False,
            "message": "You can only review service bookings completed under your own account",
        }), 403

    # Status Integrity
    if booking.get("status") != "Completed":
        return jsonify({
            "success": False,
            "message": f"Reviews can only be submitted for 'Completed' appointments. Current status is '{booking.get('status')}'.",
        }), 400

    # Duplicate Prevention
    existing = db.reviews.find_one({"bookingId": booking["_id"]})
    if existing or booking.get("isReviewed", False):
        return jsonify({
            "success": False,
            "message": "A review has already been submitted for this booking appointment.",
        }), 400

    now = datetime.datetime.now(datetime.timezone.utc)
    review_doc = {
        "bookingId": booking["_id"],
        "customerId": g.current_user["_id"],
        "providerId": booking["providerId"],
        "rating": round(float(data["rating"])),
        "comment": str(data["comment"]).strip(),
        "createdAt": now,
        "updatedAt": now,
    }

    res = db.reviews.insert_one(review_doc)
    review_doc["_id"] = res.inserted_id

    # Mark booking as reviewed
    db.bookings.update_one(
        {"_id": booking["_id"]},
        {"$set": {"isReviewed": True, "reviewId": review_doc["_id"], "updatedAt": now}},
    )

    # Recalculate provider reputation
    avg_rating, total_reviews = recalculate_provider_rating(booking["providerId"], db)

    # Populate review for response
    pop_cust = db.users.find_one({"_id": g.current_user["_id"]})
    prov_profile = db.providerprofiles.find_one({"_id": to_object_id(booking["providerId"])})
    prov_user = db.users.find_one({"_id": to_object_id(prov_profile["userId"])}) if prov_profile else None

    pop_review = dict(review_doc)
    pop_review["customerId"] = {
        "_id": pop_cust["_id"],
        "name": pop_cust.get("name"),
        "email": pop_cust.get("email"),
    }
    pop_review["providerId"] = {
        "_id": prov_profile["_id"] if prov_profile else booking["providerId"],
        "userId": {
            "name": prov_user.get("name") if prov_user else "",
        },
    }

    return jsonify({
        "success": True,
        "message": "Thank you! Your verified rating and review have been published.",
        "data": serialize_doc(pop_review),
        "providerReputation": {
            "averageRating": avg_rating,
            "totalReviews": total_reviews,
        },
    }), 201

@review_bp.route("/provider/<provider_id>", methods=["GET"])
def get_provider_reviews(provider_id):
    if not is_valid_object_id(provider_id):
        return jsonify({
            "success": False,
            "message": "Invalid provider profile ID format",
        }), 400

    db = get_db()
    prov_id = to_object_id(provider_id)
    raw_reviews = list(db.reviews.find({"providerId": prov_id}).sort("createdAt", -1))

    distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    populated_reviews = []

    for r in raw_reviews:
        star = min(5, max(1, int(round(r.get("rating", 5)))))
        distribution[star] += 1

        r_dict = dict(r)
        cust = db.users.find_one({"_id": to_object_id(r["customerId"])})
        if cust:
            r_dict["customerId"] = {
                "_id": cust["_id"],
                "name": cust.get("name"),
            }
        populated_reviews.append(r_dict)

    # Format distribution keys as strings ("5", "4", "3", "2", "1") for JS object compatibility
    dist_map = {str(k): v for k, v in distribution.items()}

    prov = db.providerprofiles.find_one({"_id": prov_id})

    return jsonify({
        "success": True,
        "count": len(populated_reviews),
        "averageRating": prov.get("averageRating", 0) if prov else 0,
        "totalReviews": prov.get("totalReviews", len(populated_reviews)) if prov else len(populated_reviews),
        "distribution": dist_map,
        "data": serialize_doc(populated_reviews),
    }), 200

@review_bp.route("/my", methods=["GET"])
@protect
@authorize("customer")
def get_my_reviews():
    db = get_db()
    raw_reviews = list(db.reviews.find({"customerId": g.current_user["_id"]}).sort("createdAt", -1))

    populated = []
    for r in raw_reviews:
        r_dict = dict(r)
        # Populate provider
        prov = db.providerprofiles.find_one({"_id": to_object_id(r["providerId"])})
        if prov:
            p_dict = dict(prov)
            p_user = db.users.find_one({"_id": to_object_id(prov.get("userId"))})
            p_cat = db.servicecategories.find_one({"_id": to_object_id(prov.get("serviceCategory"))})
            p_dict["userId"] = {"name": p_user.get("name")} if p_user else None
            p_dict["serviceCategory"] = {"name": p_cat.get("name"), "icon": p_cat.get("icon")} if p_cat else None
            r_dict["providerId"] = p_dict

        # Populate booking
        booking = db.bookings.find_one({"_id": to_object_id(r["bookingId"])})
        if booking:
            r_dict["bookingId"] = {
                "_id": booking["_id"],
                "date": booking.get("date"),
                "time": booking.get("time"),
                "serviceCharge": booking.get("serviceCharge"),
                "description": booking.get("description"),
            }
        populated.append(r_dict)

    return jsonify({
        "success": True,
        "count": len(populated),
        "data": serialize_doc(populated),
    }), 200

@review_bp.route("/booking/<booking_id>", methods=["GET"])
def get_review_by_booking(booking_id):
    if not is_valid_object_id(booking_id):
        return jsonify({
            "success": False,
            "message": "Invalid booking ID format",
        }), 400

    db = get_db()
    r = db.reviews.find_one({"bookingId": to_object_id(booking_id)})
    if not r:
        return jsonify({
            "success": True,
            "data": None,
        }), 200

    r_dict = dict(r)
    cust = db.users.find_one({"_id": to_object_id(r["customerId"])})
    if cust:
        r_dict["customerId"] = {
            "_id": cust["_id"],
            "name": cust.get("name"),
        }

    return jsonify({
        "success": True,
        "data": serialize_doc(r_dict),
    }), 200
