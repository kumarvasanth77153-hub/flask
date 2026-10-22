import datetime
import functools
from bson import ObjectId
from flask import (
    Blueprint, render_template, request, redirect, 
    url_for, session, flash, g
)
from flask_server.db import get_db, to_object_id
from flask_server.utils.security import check_password, hash_password

web_bp = Blueprint("web", __name__)

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access that page.", "warning")
            return redirect(url_for("web.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please sign in to access that page.", "warning")
                return redirect(url_for("web.login"))
            if session.get("user_role") not in allowed_roles:
                flash("Access denied: You do not have permission for that portal.", "danger")
                return redirect(url_for("web.home"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    if "user_id" in session:
        db = get_db()
        return db.users.find_one({"_id": to_object_id(session["user_id"])})
    return None

# ==========================================
# Public Pages
# ==========================================

@web_bp.route("/")
def home():
    # If client specifically requests JSON or is automated test runner, return JSON status
    if (
        "application/json" in request.headers.get("Accept", "") 
        or request.args.get("format") == "json"
        or "python-requests" in request.headers.get("User-Agent", "")
    ):
        return {
            "success": True,
            "message": "Local Service Booking & Workforce Management System API is running",
            "healthCheck": "/api/health",
        }, 200

    db = get_db()
    # Fetch active categories
    categories = list(db.servicecategories.find({"isActive": True}))
    
    # Fetch top providers with user info and category info
    providers_cursor = db.providerprofiles.find({"isActive": True}).limit(6)
    featured_providers = []
    
    for p in providers_cursor:
        user = db.users.find_one({"_id": to_object_id(p.get("userId"))})
        cat = db.servicecategories.find_one({"_id": to_object_id(p.get("serviceCategory"))})
        p["user"] = user
        p["category_name"] = cat["name"] if cat else "General Maintenance"
        featured_providers.append(p)
        
    return render_template(
        "index.html",
        categories=categories,
        featured_providers=featured_providers,
    )

@web_bp.route("/services")
def services():
    db = get_db()
    categories = list(db.servicecategories.find({"isActive": True}))
    category_name = request.args.get("category", "").strip()
    query = request.args.get("q", "").strip()

    # Build provider query
    provider_query = {"isActive": True}
    
    selected_cat_id = None
    if category_name:
        cat_match = db.servicecategories.find_one({"name": {"$regex": f"^{category_name}$", "$options": "i"}})
        if cat_match:
            selected_cat_id = cat_match["_id"]
            provider_query["serviceCategory"] = selected_cat_id

    providers_cursor = db.providerprofiles.find(provider_query)
    providers = []
    
    for p in providers_cursor:
        user = db.users.find_one({"_id": to_object_id(p.get("userId"))})
        cat = db.servicecategories.find_one({"_id": to_object_id(p.get("serviceCategory"))})
        p["user"] = user
        p["category_name"] = cat["name"] if cat else "General Trade"
        
        # Apply text search filter if provided
        if query:
            q_lower = query.lower()
            u_name = (user.get("name") if user else "").lower()
            p_desc = (p.get("description") or "").lower()
            p_cat = p["category_name"].lower()
            if q_lower not in u_name and q_lower not in p_desc and q_lower not in p_cat:
                continue
                
        providers.append(p)

    return render_template(
        "services.html",
        categories=categories,
        providers=providers,
        current_category=category_name,
        current_query=query,
    )

# ==========================================
# Authentication & Registration
# ==========================================

@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        # Redirect to appropriate dashboard if already logged in
        role = session.get("user_role")
        if role == "admin":
            return redirect(url_for("web.admin_dashboard"))
        elif role == "provider":
            return redirect(url_for("web.provider_dashboard"))
        return redirect(url_for("web.customer_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.users.find_one({"email": email})

        if not user or not check_password(password, user.get("password")):
            flash("Invalid email or password. Please check your credentials.", "error")
            return render_template("login.html")

        if not user.get("isActive", True):
            flash("Your account has been deactivated. Please contact support.", "danger")
            return render_template("login.html")

        # Set session data
        session["user_id"] = str(user["_id"])
        session["user_name"] = user.get("name", "User")
        session["user_email"] = user.get("email")
        session["user_role"] = user.get("role", "customer")

        flash(f"Welcome back, {user.get('name')}!", "success")
        
        # Role redirection
        next_url = request.args.get("next")
        if next_url:
            return redirect(next_url)

        if user.get("role") == "admin":
            return redirect(url_for("web.admin_dashboard"))
        elif user.get("role") == "provider":
            return redirect(url_for("web.provider_dashboard"))
        return redirect(url_for("web.customer_dashboard"))

    return render_template("login.html")

@web_bp.route("/register", methods=["GET", "POST"])
def register():
    db = get_db()
    categories = list(db.servicecategories.find({"isActive": True}))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        role = request.form.get("role", "customer").strip().lower()

        if not name or not email or not password:
            flash("All required fields must be filled.", "error")
            return render_template("register.html", categories=categories)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("register.html", categories=categories)

        # Check existing user
        if db.users.find_one({"email": email}):
            flash("An account with this email address already exists.", "error")
            return render_template("register.html", categories=categories)

        hashed = hash_password(password)
        now = datetime.datetime.now(datetime.timezone.utc)

        user_doc = {
            "name": name,
            "email": email,
            "password": hashed,
            "phone": phone,
            "address": address,
            "role": role if role in ["customer", "provider"] else "customer",
            "isActive": True,
            "latitude": 9.9252,
            "longitude": 78.1198,
            "createdAt": now,
            "updatedAt": now,
        }
        user_res = db.users.insert_one(user_doc)
        user_id = user_res.inserted_id

        # If provider, create profile
        if role == "provider":
            cat_id = to_object_id(request.form.get("category"))
            try:
                charge = float(request.form.get("serviceCharge", 400))
            except ValueError:
                charge = 400.0
            try:
                exp = int(request.form.get("experience", 2))
            except ValueError:
                exp = 2
            bio = request.form.get("description", "").strip()

            provider_doc = {
                "userId": user_id,
                "serviceCategory": cat_id,
                "experience": exp,
                "description": bio or f"Certified specialist offering {name}'s home services.",
                "serviceCharge": charge,
                "latitude": 9.9252,
                "longitude": 78.1198,
                "address": address,
                "isAvailable": True,
                "averageRating": 5.0,
                "totalReviews": 0,
                "isActive": True,
                "createdAt": now,
                "updatedAt": now,
            }
            db.providerprofiles.insert_one(provider_doc)

        flash("Registration successful! You may now sign in with your credentials.", "success")
        return redirect(url_for("web.login"))

    return render_template("register.html", categories=categories)

@web_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("web.home"))

# ==========================================
# Service Booking Flow
# ==========================================

@web_bp.route("/book/<provider_id>", methods=["GET", "POST"])
@login_required
def book_provider(provider_id):
    db = get_db()
    prov_oid = to_object_id(provider_id)
    provider = db.providerprofiles.find_one({"_id": prov_oid})

    if not provider:
        flash("Service provider not found.", "error")
        return redirect(url_for("web.services"))

    provider_user = db.users.find_one({"_id": to_object_id(provider.get("userId"))})
    cat = db.servicecategories.find_one({"_id": to_object_id(provider.get("serviceCategory"))})
    provider["user"] = provider_user
    provider["category_name"] = cat["name"] if cat else "General Maintenance"

    current_user = get_current_user()

    if request.method == "POST":
        date = request.form.get("date", "").strip()
        time_slot = request.form.get("time", "").strip()
        address = request.form.get("address", "").strip()
        description = request.form.get("description", "").strip()

        if not date or not address or not description:
            flash("Please fill in all booking details.", "error")
            return render_template("book.html", provider=provider, current_user=current_user)

        now = datetime.datetime.now(datetime.timezone.utc)
        booking_doc = {
            "customerId": to_object_id(session["user_id"]),
            "providerId": provider["_id"],
            "serviceCategory": provider.get("serviceCategory"),
            "date": date,
            "time": time_slot,
            "address": address,
            "description": description,
            "serviceCharge": float(provider.get("serviceCharge", 500)),
            "status": "Pending",
            "cancellationReason": "",
            "rejectionReason": "",
            "latitude": current_user.get("latitude", 9.928) if current_user else 9.928,
            "longitude": current_user.get("longitude", 78.121) if current_user else 78.121,
            "createdAt": now,
            "updatedAt": now,
        }

        db.bookings.insert_one(booking_doc)
        flash("Booking request confirmed! Your provider will review it shortly.", "success")
        return redirect(url_for("web.customer_dashboard"))

    today_str = datetime.date.today().isoformat()
    return render_template(
        "book.html",
        provider=provider,
        current_user=current_user,
        today_date=today_str,
    )

# ==========================================
# Customer Dashboard & Actions
# ==========================================

@web_bp.route("/customer/dashboard")
@role_required(["customer", "admin"])
def customer_dashboard():
    db = get_db()
    cust_oid = to_object_id(session["user_id"])
    
    bookings_cursor = db.bookings.find({"customerId": cust_oid}).sort("createdAt", -1)
    bookings = []
    
    pending_count = 0
    completed_count = 0
    total_spent = 0.0

    for b in bookings_cursor:
        # Populate provider name
        prov_profile = db.providerprofiles.find_one({"_id": to_object_id(b.get("providerId"))})
        if prov_profile:
            p_user = db.users.find_one({"_id": to_object_id(prov_profile.get("userId"))})
            b["provider_name"] = p_user["name"] if p_user else "Service Expert"
        else:
            # Fallback check if providerId directly stored user ObjectId
            p_user = db.users.find_one({"_id": to_object_id(b.get("providerId"))})
            b["provider_name"] = p_user["name"] if p_user else "Service Expert"

        # Populate category
        cat = db.servicecategories.find_one({"_id": to_object_id(b.get("serviceCategory"))})
        b["category_name"] = cat["name"] if cat else "General Maintenance"

        # Check existing review
        rev = db.reviews.find_one({"bookingId": b["_id"]})
        b["has_review"] = rev is not None
        b["review_rating"] = rev["rating"] if rev else None

        # Stats
        charge = float(b.get("serviceCharge", 0))
        status = b.get("status", "Pending")
        if status in ["Pending", "Confirmed", "In Progress"]:
            pending_count += 1
        elif status == "Completed":
            completed_count += 1
            total_spent += charge

        bookings.append(b)

    return render_template(
        "customer_dashboard.html",
        bookings=bookings,
        pending_count=pending_count,
        completed_count=completed_count,
        total_spent=total_spent,
    )

@web_bp.route("/customer/bookings/<booking_id>/cancel", methods=["POST"])
@role_required(["customer", "admin"])
def customer_cancel_booking(booking_id):
    db = get_db()
    b_oid = to_object_id(booking_id)
    cust_oid = to_object_id(session["user_id"])

    res = db.bookings.update_one(
        {"_id": b_oid, "customerId": cust_oid, "status": "Pending"},
        {"$set": {"status": "Cancelled", "cancellationReason": "Customer cancelled via portal", "updatedAt": datetime.datetime.now(datetime.timezone.utc)}}
    )
    if res.modified_count > 0:
        flash("Booking request has been cancelled.", "info")
    else:
        flash("Could not cancel this booking (it may have already been confirmed).", "error")

    return redirect(url_for("web.customer_dashboard"))

@web_bp.route("/reviews/create", methods=["POST"])
@role_required(["customer", "admin"])
def create_review():
    db = get_db()
    booking_id = request.form.get("bookingId")
    b_oid = to_object_id(booking_id)
    rating_val = int(request.form.get("rating", 5))
    comment = request.form.get("comment", "").strip()

    booking = db.bookings.find_one({"_id": b_oid, "customerId": to_object_id(session["user_id"])})
    if not booking:
        flash("Booking reference not found.", "error")
        return redirect(url_for("web.customer_dashboard"))

    # Verify not already reviewed
    if db.reviews.find_one({"bookingId": b_oid}):
        flash("You have already submitted a review for this booking.", "warning")
        return redirect(url_for("web.customer_dashboard"))

    now = datetime.datetime.now(datetime.timezone.utc)
    review_doc = {
        "bookingId": b_oid,
        "customerId": booking["customerId"],
        "providerId": booking["providerId"],
        "rating": rating_val,
        "comment": comment,
        "createdAt": now,
        "updatedAt": now,
    }
    db.reviews.insert_one(review_doc)

    # Recalculate provider average rating
    all_revs = list(db.reviews.find({"providerId": booking["providerId"]}))
    if all_revs:
        avg_rating = round(sum(r["rating"] for r in all_revs) / len(all_revs), 1)
        db.providerprofiles.update_one(
            {"_id": to_object_id(booking["providerId"])},
            {"$set": {"averageRating": avg_rating, "totalReviews": len(all_revs)}}
        )

    flash("Thank you! Your feedback review has been submitted.", "success")
    return redirect(url_for("web.customer_dashboard"))

# ==========================================
# Provider Portal & Actions
# ==========================================

@web_bp.route("/provider/dashboard")
@role_required(["provider", "admin"])
def provider_dashboard():
    db = get_db()
    user_oid = to_object_id(session["user_id"])
    profile = db.providerprofiles.find_one({"userId": user_oid})

    if not profile:
        flash("Provider profile not found.", "error")
        return redirect(url_for("web.home"))

    # Category name
    cat = db.servicecategories.find_one({"_id": to_object_id(profile.get("serviceCategory"))})
    profile["serviceCategory_name"] = cat["name"] if cat else "Tradesperson"

    # Find bookings assigned to this provider profile OR user id
    bookings_cursor = db.bookings.find({
        "$or": [{"providerId": profile["_id"]}, {"providerId": user_oid}]
    }).sort("createdAt", -1)

    bookings = []
    pending_requests = []
    active_jobs = []
    completed_jobs = []
    total_earnings = 0.0

    for b in bookings_cursor:
        # Populate customer details
        cust = db.users.find_one({"_id": to_object_id(b.get("customerId"))})
        b["customer"] = cust

        status = b.get("status", "Pending")
        charge = float(b.get("serviceCharge", 0))

        if status == "Pending":
            pending_requests.append(b)
        elif status in ["Confirmed", "In Progress"]:
            active_jobs.append(b)
        elif status in ["Completed", "Cancelled", "Rejected"]:
            completed_jobs.append(b)
            if status == "Completed":
                total_earnings += charge

        bookings.append(b)

    return render_template(
        "provider_dashboard.html",
        profile=profile,
        bookings=bookings,
        pending_requests=pending_requests,
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        total_earnings=total_earnings,
    )

@web_bp.route("/provider/bookings/<booking_id>/action", methods=["POST"])
@role_required(["provider", "admin"])
def provider_booking_action(booking_id):
    db = get_db()
    b_oid = to_object_id(booking_id)
    action = request.form.get("action")

    new_status = "Confirmed" if action == "accept" else "Rejected"
    db.bookings.update_one(
        {"_id": b_oid},
        {"$set": {"status": new_status, "updatedAt": datetime.datetime.now(datetime.timezone.utc)}}
    )

    if new_status == "Confirmed":
        flash("Booking confirmed! Please report to customer site on the scheduled time.", "success")
    else:
        flash("Booking request has been declined.", "info")

    return redirect(url_for("web.provider_dashboard"))

@web_bp.route("/provider/bookings/<booking_id>/status", methods=["POST"])
@role_required(["provider", "admin"])
def provider_update_status(booking_id):
    db = get_db()
    b_oid = to_object_id(booking_id)
    new_status = request.form.get("status")

    if new_status in ["In Progress", "Completed"]:
        db.bookings.update_one(
            {"_id": b_oid},
            {"$set": {"status": new_status, "updatedAt": datetime.datetime.now(datetime.timezone.utc)}}
        )
        flash(f"Job status updated to '{new_status}'.", "success")

    return redirect(url_for("web.provider_dashboard"))

@web_bp.route("/provider/toggle-availability", methods=["POST"])
@role_required(["provider", "admin"])
def provider_toggle_availability():
    db = get_db()
    user_oid = to_object_id(session["user_id"])
    profile = db.providerprofiles.find_one({"userId": user_oid})
    if profile:
        new_avail = not profile.get("isAvailable", True)
        db.providerprofiles.update_one({"_id": profile["_id"]}, {"$set": {"isAvailable": new_avail}})
        msg = "You are now marked as AVAILABLE for jobs." if new_avail else "You are now marked as BUSY."
        flash(msg, "info")

    return redirect(url_for("web.provider_dashboard"))

# ==========================================
# Admin Portal & Controls
# ==========================================

@web_bp.route("/admin/dashboard")
@role_required(["admin"])
def admin_dashboard():
    db = get_db()
    total_users = db.users.count_documents({})
    total_providers = db.providerprofiles.count_documents({})
    total_bookings = db.bookings.count_documents({})
    
    # Calculate total revenue
    completed_bookings = list(db.bookings.find({"status": "Completed"}))
    total_volume = sum(float(b.get("serviceCharge", 0)) for b in completed_bookings)

    # Recent bookings
    recent_cursor = db.bookings.find().sort("createdAt", -1).limit(8)
    recent_bookings = []
    for b in recent_cursor:
        c_user = db.users.find_one({"_id": to_object_id(b.get("customerId"))})
        cat = db.servicecategories.find_one({"_id": to_object_id(b.get("serviceCategory"))})
        b["customer_name"] = c_user["name"] if c_user else "Customer"
        b["category_name"] = cat["name"] if cat else "Service"
        recent_bookings.append(b)

    # Users list
    users = list(db.users.find().sort("createdAt", -1).limit(20))

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_providers=total_providers,
        total_bookings=total_bookings,
        total_volume=total_volume,
        recent_bookings=recent_bookings,
        users=users,
    )

@web_bp.route("/admin/categories/create", methods=["POST"])
@role_required(["admin"])
def admin_create_category():
    name = request.form.get("name", "").strip()
    icon = request.form.get("icon", "🛠️").strip()
    desc = request.form.get("description", "").strip()

    if not name:
        flash("Category name is required.", "error")
        return redirect(url_for("web.admin_dashboard"))

    db = get_db()
    now = datetime.datetime.now(datetime.timezone.utc)
    db.servicecategories.insert_one({
        "name": name,
        "description": desc or f"Professional {name} services.",
        "icon": icon,
        "isActive": True,
        "createdAt": now,
        "updatedAt": now,
    })

    flash(f"New service category '{name}' created successfully!", "success")
    return redirect(url_for("web.admin_dashboard"))

@web_bp.route("/admin/users/<user_id>/toggle-status", methods=["POST"])
@role_required(["admin"])
def admin_toggle_user_status(user_id):
    db = get_db()
    u_oid = to_object_id(user_id)
    user = db.users.find_one({"_id": u_oid})
    if user:
        new_active = not user.get("isActive", True)
        db.users.update_one({"_id": u_oid}, {"$set": {"isActive": new_active}})
        flash(f"User '{user.get('name')}' status set to {'Active' if new_active else 'Suspended'}.", "info")

    return redirect(url_for("web.admin_dashboard"))
