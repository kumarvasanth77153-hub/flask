import datetime
from flask import Blueprint, request, jsonify, g
from flask_server.db import get_db, to_object_id, is_valid_object_id
from flask_server.middleware.auth import protect, authorize
from flask_server.utils.haversine import calculate_haversine_distance
from flask_server.utils.serializers import serialize_doc

provider_bp = Blueprint("providers", __name__)

def populate_provider(prov, db):
    if not prov:
        return None
    p = dict(prov)
    # Populate user details
    if "userId" in p and p["userId"]:
        user = db.users.find_one({"_id": to_object_id(p["userId"])})
        if user:
            p["userId"] = {
                "_id": user["_id"],
                "name": user.get("name"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "address": user.get("address"),
                "latitude": user.get("latitude"),
                "longitude": user.get("longitude"),
                "isActive": user.get("isActive", True),
            }
        else:
            p["userId"] = None

    # Populate service category
    if "serviceCategory" in p and p["serviceCategory"]:
        cat = db.servicecategories.find_one({"_id": to_object_id(p["serviceCategory"])})
        if cat:
            p["serviceCategory"] = {
                "_id": cat["_id"],
                "name": cat.get("name"),
                "description": cat.get("description"),
                "icon": cat.get("icon"),
                "isActive": cat.get("isActive", True),
            }
        else:
            p["serviceCategory"] = None

    return p

def validate_provider_profile_input(data):
    errors = []
    cat_id = data.get("serviceCategory")
    if not cat_id or not is_valid_object_id(cat_id):
        errors.append("A valid service category ID is required")

    exp = data.get("experience")
    if exp is not None and exp != "":
        try:
            num_exp = float(exp)
            if num_exp < 0:
                errors.append("Experience must be a non-negative number of years")
        except (ValueError, TypeError):
            errors.append("Experience must be a non-negative number of years")

    charge = data.get("serviceCharge")
    if charge is not None and charge != "":
        try:
            num_charge = float(charge)
            if num_charge < 0:
                errors.append("Service charge must be a non-negative amount")
        except (ValueError, TypeError):
            errors.append("Service charge must be a non-negative amount")

    lat = data.get("latitude")
    if lat is None or lat == "":
        errors.append("Operating latitude coordinate is required")
    else:
        try:
            num_lat = float(lat)
            if num_lat < -90 or num_lat > 90:
                errors.append("Latitude must be between -90 and 90")
        except (ValueError, TypeError):
            errors.append("Latitude must be between -90 and 90")

    lng = data.get("longitude")
    if lng is None or lng == "":
        errors.append("Operating longitude coordinate is required")
    else:
        try:
            num_lng = float(lng)
            if num_lng < -180 or num_lng > 180:
                errors.append("Longitude must be between -180 and 180")
        except (ValueError, TypeError):
            errors.append("Longitude must be between -180 and 180")

    avail = data.get("availability")
    if avail and avail not in ["Available", "Busy", "On Leave"]:
        errors.append("Availability status must be Available, Busy, or On Leave")

    return len(errors) == 0, errors

@provider_bp.route("/profile", methods=["GET"])
@protect
@authorize("provider")
def get_my_profile():
    db = get_db()
    prov = db.providerprofiles.find_one({"userId": g.current_user["_id"]})
    if not prov:
        return jsonify({
            "success": False,
            "message": "Provider profile not yet configured",
        }), 404

    populated = populate_provider(prov, db)
    return jsonify({
        "success": True,
        "data": serialize_doc(populated),
    }), 200

@provider_bp.route("/profile", methods=["POST", "PUT"])
@protect
@authorize("provider")
def create_or_update_profile():
    data = request.get_json() or {}
    is_valid, errors = validate_provider_profile_input(data)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": errors[0],
            "errors": errors,
        }), 400

    db = get_db()
    cat_id = to_object_id(data["serviceCategory"])
    category = db.servicecategories.find_one({"_id": cat_id})
    if not category or not category.get("isActive", True):
        return jsonify({
            "success": False,
            "message": "Selected service category is invalid or inactive",
        }), 400

    user_id = g.current_user["_id"]
    now = datetime.datetime.now(datetime.timezone.utc)

    avail = data.get("availability", "Available")
    is_avail = data.get("isAvailable")
    if is_avail is None:
        is_avail = avail == "Available"
    else:
        is_avail = bool(is_avail)

    profile_fields = {
        "userId": user_id,
        "serviceCategory": cat_id,
        "experience": int(data.get("experience", 1)),
        "description": str(data.get("description", "")).strip(),
        "serviceCharge": float(data.get("serviceCharge", 300)),
        "latitude": float(data["latitude"]),
        "longitude": float(data["longitude"]),
        "address": str(data.get("address", g.current_user.get("address", ""))).strip(),
        "availability": avail,
        "isAvailable": is_avail,
        "isActive": True,
        "updatedAt": now,
    }

    existing = db.providerprofiles.find_one({"userId": user_id})

    if existing:
        db.providerprofiles.update_one({"userId": user_id}, {"$set": profile_fields})
        # Synchronize User model address & coordinates
        db.users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "address": profile_fields["address"],
                    "latitude": profile_fields["latitude"],
                    "longitude": profile_fields["longitude"],
                    "updatedAt": now,
                }
            },
        )
        updated = db.providerprofiles.find_one({"userId": user_id})
        populated = populate_provider(updated, db)
        return jsonify({
            "success": True,
            "message": "Provider profile updated successfully",
            "data": serialize_doc(populated),
        }), 200
    else:
        profile_fields["averageRating"] = 0
        profile_fields["totalReviews"] = 0
        profile_fields["createdAt"] = now
        ins = db.providerprofiles.insert_one(profile_fields)
        profile_fields["_id"] = ins.inserted_id

        db.users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "address": profile_fields["address"],
                    "latitude": profile_fields["latitude"],
                    "longitude": profile_fields["longitude"],
                    "updatedAt": now,
                }
            },
        )
        populated = populate_provider(profile_fields, db)
        return jsonify({
            "success": True,
            "message": "Provider profile created successfully",
            "data": serialize_doc(populated),
        }), 201

@provider_bp.route("/availability", methods=["PUT"])
@protect
@authorize("provider")
def update_availability():
    data = request.get_json() or {}
    db = get_db()
    prov = db.providerprofiles.find_one({"userId": g.current_user["_id"]})
    if not prov:
        return jsonify({
            "success": False,
            "message": "Provider profile not found. Please create your profile first.",
        }), 404

    is_avail = data.get("isAvailable")
    avail = data.get("availability")

    update_fields = {"updatedAt": datetime.datetime.now(datetime.timezone.utc)}

    current_avail = prov.get("availability", "Available")
    current_is_avail = prov.get("isAvailable", True)

    if is_avail is not None:
        current_is_avail = bool(is_avail)
        if current_is_avail and current_avail == "Busy":
            current_avail = "Available"
        elif not current_is_avail and current_avail == "Available":
            current_avail = "Busy"

    if avail and avail in ["Available", "Busy", "On Leave"]:
        current_avail = avail
        current_is_avail = avail == "Available"

    update_fields["isAvailable"] = current_is_avail
    update_fields["availability"] = current_avail

    db.providerprofiles.update_one({"_id": prov["_id"]}, {"$set": update_fields})

    return jsonify({
        "success": True,
        "message": f"Availability updated to {current_avail}",
        "data": {
            "isAvailable": current_is_avail,
            "availability": current_avail,
        },
    }), 200

@provider_bp.route("/nearby", methods=["GET"])
def get_nearby_providers():
    lat = request.args.get("latitude")
    lng = request.args.get("longitude")

    if lat is None or lng is None or lat == "" or lng == "":
        return jsonify({
            "success": False,
            "message": "Please provide both latitude and longitude coordinates to search nearby providers",
        }), 400

    try:
        user_lat = float(lat)
        user_lng = float(lng)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid coordinate values. Latitude must be -90 to 90, Longitude must be -180 to 180.",
        }), 400

    if user_lat < -90 or user_lat > 90 or user_lng < -180 or user_lng > 180:
        return jsonify({
            "success": False,
            "message": "Invalid coordinate values. Latitude must be -90 to 90, Longitude must be -180 to 180.",
        }), 400

    radius_arg = request.args.get("radius", "10")
    radius_km = float("inf") if radius_arg == "all" else float(radius_arg)

    category_filter = request.args.get("category")
    search_query = request.args.get("search", "").strip().lower()
    availability_filter = request.args.get("availability")
    min_rating = request.args.get("minRating")
    max_price = request.args.get("maxPrice")
    sort_by = request.args.get("sortBy", "distance")

    db = get_db()
    providers = list(db.providerprofiles.find({"isActive": True}))

    results = []
    for prov in providers:
        pop = populate_provider(prov, db)
        if not pop.get("userId") or not pop.get("serviceCategory") or not pop["serviceCategory"].get("name"):
            continue

        prov_lat = pop.get("latitude")
        prov_lng = pop.get("longitude")
        distance = calculate_haversine_distance(user_lat, user_lng, prov_lat, prov_lng)

        # Radius filter
        if radius_km != float("inf") and (distance is None or distance > radius_km):
            continue

        # Category filter
        if category_filter and category_filter != "all":
            cat_id_match = str(pop["serviceCategory"].get("_id")) == category_filter
            cat_name_match = str(pop["serviceCategory"].get("name", "")).lower() == category_filter.lower()
            if not cat_id_match and not cat_name_match:
                continue

        # Search keyword filter
        if search_query:
            prov_name = str(pop["userId"].get("name", "")).lower()
            cat_name = str(pop["serviceCategory"].get("name", "")).lower()
            desc = str(pop.get("description", "")).lower()
            if search_query not in prov_name and search_query not in cat_name and search_query not in desc:
                continue

        # Availability filter
        if availability_filter == "available":
            if not pop.get("isAvailable") or pop.get("availability") != "Available":
                continue

        # Minimum rating filter
        if min_rating is not None and min_rating != "":
            try:
                if float(pop.get("averageRating", 0)) < float(min_rating):
                    continue
            except (ValueError, TypeError):
                pass

        # Maximum price filter
        if max_price is not None and max_price != "":
            try:
                if float(pop.get("serviceCharge", 0)) > float(max_price):
                    continue
            except (ValueError, TypeError):
                pass

        pop["distanceKm"] = distance
        results.append(pop)

    # Sort results
    if sort_by == "rating":
        results.sort(key=lambda x: x.get("averageRating", 0), reverse=True)
    elif sort_by == "price_asc":
        results.sort(key=lambda x: x.get("serviceCharge", 0))
    elif sort_by == "price_desc":
        results.sort(key=lambda x: x.get("serviceCharge", 0), reverse=True)
    elif sort_by == "experience":
        results.sort(key=lambda x: x.get("experience", 0), reverse=True)
    else:  # default 'distance'
        results.sort(key=lambda x: x.get("distanceKm", float("inf")) if x.get("distanceKm") is not None else float("inf"))

    return jsonify({
        "success": True,
        "count": len(results),
        "userCoordinates": {
            "latitude": user_lat,
            "longitude": user_lng,
        },
        "radiusKm": "All" if radius_arg == "all" else radius_km,
        "data": serialize_doc(results),
    }), 200

@provider_bp.route("", methods=["GET"])
@provider_bp.route("/", methods=["GET"])
def get_all_providers():
    db = get_db()
    cat_arg = request.args.get("category")
    is_avail_arg = request.args.get("isAvailable")

    query = {"isActive": True}
    if cat_arg:
        if is_valid_object_id(cat_arg):
            query["serviceCategory"] = to_object_id(cat_arg)

    if is_avail_arg is not None:
        query["isAvailable"] = is_avail_arg.lower() == "true"

    providers = list(db.providerprofiles.find(query).sort("averageRating", -1))
    populated_list = [populate_provider(p, db) for p in providers]

    return jsonify({
        "success": True,
        "count": len(populated_list),
        "data": serialize_doc(populated_list),
    }), 200

@provider_bp.route("/<provider_id>", methods=["GET"])
def get_provider_by_id(provider_id):
    if not is_valid_object_id(provider_id):
        return jsonify({
            "success": False,
            "message": "Provider profile not found or inactive",
        }), 404

    db = get_db()
    prov = db.providerprofiles.find_one({"_id": to_object_id(provider_id)})
    if not prov or not prov.get("isActive", True):
        return jsonify({
            "success": False,
            "message": "Provider profile not found or inactive",
        }), 404

    populated = populate_provider(prov, db)
    return jsonify({
        "success": True,
        "data": serialize_doc(populated),
    }), 200
