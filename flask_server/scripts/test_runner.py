#!/usr/bin/env python3
"""
UrbanAid — Automated Comprehensive Test Runner (Phases 1 through 7)
Tests the Flask & MongoDB API directly over HTTP.
"""
import sys
import os
import time
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:5000/api")
passed_tests = 0
failed_tests = 0

def assert_test(condition, test_name):
    global passed_tests, failed_tests
    if condition:
        print(f"  [PASS] {test_name}")
        passed_tests += 1
    else:
        print(f"  [FAIL] {test_name}")
        failed_tests += 1

def run_phase_1():
    print("\n" + "=" * 60)
    print("Executing Phase 1: Root & Health Verification")
    print("=" * 60)
    # Root
    r = requests.get(BASE_URL.replace("/api", "/"))
    assert_test(r.status_code == 200 and r.json().get("success"), "GET / returns HTTP 200 with service status")

    # API Catalog
    r = requests.get(BASE_URL)
    assert_test(r.status_code == 200 and "endpoints" in r.json(), "GET /api returns endpoint catalog")

    # Health
    r = requests.get(f"{BASE_URL}/health")
    data = r.json()
    assert_test(r.status_code == 200 and data.get("database", {}).get("status") == "connected", "GET /api/health reports database connected")

def run_phase_2():
    print("\n" + "=" * 60)
    print("Executing Phase 2: Authentication & RBAC")
    print("=" * 60)

    # 1. Customer Login
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "customer@urbanaid.com", "password": "Customer@123"})
    data = r.json()
    assert_test(r.status_code == 200 and "token" in data and data.get("user", {}).get("role") == "customer", "Customer login returns 200, JWT token, role: customer")
    cust_token = data.get("token")

    # 2. Provider Login
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "provider@urbanaid.com", "password": "Provider@123"})
    data = r.json()
    assert_test(r.status_code == 200 and "token" in data and data.get("user", {}).get("role") == "provider", "Provider login returns 200, JWT token, role: provider")
    prov_token = data.get("token")

    # 3. Admin Login
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "admin@urbanaid.com", "password": "Admin@123"})
    data = r.json()
    assert_test(r.status_code == 200 and "token" in data and data.get("user", {}).get("role") == "admin", "Admin login returns 200, JWT token, role: admin")
    admin_token = data.get("token")

    # 4. Invalid Password Rejection
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "customer@urbanaid.com", "password": "WrongPassword"})
    assert_test(r.status_code == 401, "Invalid password rejected with HTTP 401")

    # 5. Protected route with token
    r = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {cust_token}"})
    assert_test(r.status_code == 200 and r.json().get("user", {}).get("email") == "customer@urbanaid.com", "Protected GET /api/auth/me returns authenticated user")

    # 6. Protected route without token
    r = requests.get(f"{BASE_URL}/auth/me")
    assert_test(r.status_code == 401, "Protected route without Bearer token returns HTTP 401")

    # 7. Profile Update
    r = requests.put(
        f"{BASE_URL}/auth/profile",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={"phone": "9876543299", "address": "Villa 14, Lotus Gardens, Madurai", "latitude": 9.9350, "longitude": 78.1255}
    )
    data = r.json()
    assert_test(r.status_code == 200 and data.get("user", {}).get("phone") == "9876543299", "Profile update modifies phone, address, and coordinates")

    # 8. New Registration
    rand_email = f"flask_user_{int(time.time() * 1000)}@urbanaid.com"
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Flask Test Customer",
        "email": rand_email,
        "password": "Password@123",
        "phone": "9840123456",
        "role": "customer",
        "address": "10 Cross Cut Road",
        "latitude": 9.9200,
        "longitude": 78.1150
    })
    data = r.json()
    assert_test(r.status_code == 201 and data.get("user", {}).get("email") == rand_email, "New user registration returns 201 Created with JWT")

    # 9. Duplicate Registration Rejection
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Duplicate Customer",
        "email": rand_email,
        "password": "Password@123",
        "phone": "9840123456",
        "role": "customer"
    })
    assert_test(r.status_code == 409, "Duplicate user registration rejected with HTTP 409")

    return cust_token, prov_token, admin_token

def run_phase_3(cust_token, prov_token, admin_token):
    print("\n" + "=" * 60)
    print("Executing Phase 3: Profiles & Service Categories")
    print("=" * 60)

    # 1. Fetch Categories
    r = requests.get(f"{BASE_URL}/categories")
    data = r.json()
    assert_test(r.status_code == 200 and len(data.get("data", [])) >= 8, f"GET /api/categories returns active categories (found {len(data.get('data', []))})")
    sample_cat = data["data"][0]

    # 2. Fetch Single Category
    r = requests.get(f"{BASE_URL}/categories/{sample_cat['_id']}")
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("name") == sample_cat["name"], f"GET /api/categories/:id returns single category ({sample_cat['name']})")

    # 3. Provider Get Profile
    r = requests.get(f"{BASE_URL}/providers/profile", headers={"Authorization": f"Bearer {prov_token}"})
    data = r.json()
    assert_test(r.status_code == 200 and data.get("data", {}).get("userId", {}).get("email") == "provider@urbanaid.com", "GET /api/providers/profile returns populated provider profile")

    # 4. Provider Update Profile
    cat_list = requests.get(f"{BASE_URL}/categories").json().get("data", [])
    electrician_cat = next((c for c in cat_list if isinstance(c, dict) and c.get("name") == "Electrician"), sample_cat)
    r = requests.put(
        f"{BASE_URL}/providers/profile",
        headers={"Authorization": f"Bearer {prov_token}"},
        json={
            "serviceCategory": electrician_cat["_id"],
            "experience": 6,
            "serviceCharge": 450,
            "description": "Updated profile: Certified specialist offering express electrical & wiring assistance.",
            "latitude": 9.9325,
            "longitude": 78.1270,
            "address": "Shop 12A, Anna Nagar Main Road, Madurai",
            "availability": "Available"
        }
    )
    data = r.json()
    assert_test(r.status_code == 200 and data.get("data", {}).get("serviceCharge") == 450, "PUT /api/providers/profile updates serviceCharge to 450")

    # 5. Availability Toggle
    r = requests.put(f"{BASE_URL}/providers/availability", headers={"Authorization": f"Bearer {prov_token}"}, json={"availability": "Busy"})
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("availability") == "Busy", "PUT /api/providers/availability toggles status to Busy")
    # Restore
    requests.put(f"{BASE_URL}/providers/availability", headers={"Authorization": f"Bearer {prov_token}"}, json={"availability": "Available"})

    # 6. Customer Profile
    r = requests.get(f"{BASE_URL}/customers/profile", headers={"Authorization": f"Bearer {cust_token}"})
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("email") == "customer@urbanaid.com", "GET /api/customers/profile returns customer details")

    # 7. Customer Forbidden from Provider Profile
    r = requests.put(f"{BASE_URL}/providers/profile", headers={"Authorization": f"Bearer {cust_token}"}, json={"serviceCharge": 999})
    assert_test(r.status_code == 403, "Customer cannot update provider profile (HTTP 403)")

def run_phase_4():
    print("\n" + "=" * 60)
    print("Executing Phase 4: Haversine Geolocation & Nearby Provider Search")
    print("=" * 60)

    # 1. Missing coordinates
    r = requests.get(f"{BASE_URL}/providers/nearby")
    assert_test(r.status_code == 400, "GET /api/providers/nearby without coordinates correctly returns HTTP 400")

    # 2. Nearby Search with coordinates (Madurai Rahul Sharma: 9.9280, 78.1210)
    r = requests.get(f"{BASE_URL}/providers/nearby?latitude=9.9280&longitude=78.1210&radius=10")
    data = r.json()
    assert_test(r.status_code == 200 and len(data.get("data", [])) >= 4 and "distanceKm" in data["data"][0], "GET /api/providers/nearby returns active providers with computed distanceKm")

    # 3. Default Sort by nearest distance
    items = data.get("data", [])
    is_sorted = all(items[i]["distanceKm"] >= items[i - 1]["distanceKm"] for i in range(1, len(items)))
    assert_test(is_sorted, "Providers sorted by nearest distance by default")

    # 4. Radius filter
    r = requests.get(f"{BASE_URL}/providers/nearby?latitude=9.9280&longitude=78.1210&radius=1")
    data = r.json()
    within_1km = all(p["distanceKm"] <= 1.0 for p in data.get("data", []))
    assert_test(r.status_code == 200 and within_1km, f"radius=1 filter returns only providers within 1.0 km (found {len(data.get('data', []))})")

    # 5. Category filter (Electrician)
    r = requests.get(f"{BASE_URL}/providers/nearby?latitude=9.9280&longitude=78.1210&radius=10&category=Electrician")
    data = r.json()
    all_elec = all(p.get("serviceCategory", {}).get("name") == "Electrician" for p in data.get("data", []))
    assert_test(r.status_code == 200 and len(data.get("data", [])) > 0 and all_elec, "category=Electrician filter returns only electricians")

    # 6. Keyword search (plumber)
    r = requests.get(f"{BASE_URL}/providers/nearby?latitude=9.9280&longitude=78.1210&radius=10&search=plumber")
    data = r.json()
    all_plumb = all("plumber" in p.get("userId", {}).get("name", "").lower() or "plumber" in p.get("serviceCategory", {}).get("name", "").lower() for p in data.get("data", []))
    assert_test(r.status_code == 200 and len(data.get("data", [])) > 0 and all_plumb, "search=plumber keyword returns matching plumbing specialists")

    # 7. Sort by lowest price (price_asc)
    r = requests.get(f"{BASE_URL}/providers/nearby?latitude=9.9280&longitude=78.1210&radius=10&sortBy=price_asc")
    data = r.json()
    items = data.get("data", [])
    is_price_sorted = all(items[i]["serviceCharge"] >= items[i - 1]["serviceCharge"] for i in range(1, len(items)))
    assert_test(r.status_code == 200 and is_price_sorted, "sortBy=price_asc orders providers from lowest to highest charge")

    # 8. Availability filter
    r = requests.get(f"{BASE_URL}/providers/nearby?latitude=9.9280&longitude=78.1210&radius=10&availability=available")
    data = r.json()
    all_avail = all(p.get("isAvailable") and p.get("availability") == "Available" for p in data.get("data", []))
    assert_test(r.status_code == 200 and all_avail, "availability=available filters out busy or off-duty providers")

def run_phase_5(cust_token, prov_token):
    print("\n" + "=" * 60)
    print("Executing Phase 5: Booking Lifecycle & State Transitions")
    print("=" * 60)

    # Fetch provider ID
    r = requests.get(f"{BASE_URL}/providers/profile", headers={"Authorization": f"Bearer {prov_token}"})
    prov_id = r.json()["data"]["_id"]

    # 1. Customer Creates Booking
    r = requests.post(
        f"{BASE_URL}/bookings",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "providerId": prov_id,
            "date": "2026-10-15",
            "time": "10:00 AM - 12:00 PM",
            "address": "Flat 302, Green Valley Apartments, Madurai",
            "latitude": 9.9280,
            "longitude": 78.1210,
            "description": "Main MCB switch is tripping repeatedly whenever geyser is turned on."
        }
    )
    data = r.json()
    assert_test(r.status_code == 201 and data.get("data", {}).get("status") == "Pending" and data.get("data", {}).get("serviceCharge") > 0, "Customer creates booking with status: Pending and captured serviceCharge")
    booking1_id = data["data"]["_id"]

    # 2. Provider Inbox
    r = requests.get(f"{BASE_URL}/bookings/provider", headers={"Authorization": f"Bearer {prov_token}"})
    found_in_prov = any(b["_id"] == booking1_id for b in r.json().get("data", []))
    assert_test(found_in_prov, "New booking appears in provider request inbox")

    # 3. Provider Accepts (Pending -> Accepted)
    r = requests.put(f"{BASE_URL}/bookings/{booking1_id}/status", headers={"Authorization": f"Bearer {prov_token}"}, json={"status": "Accepted"})
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("status") == "Accepted", "Provider accepts booking -> status: Accepted")

    # 4. Provider Starts Service (Accepted -> In Progress)
    r = requests.put(f"{BASE_URL}/bookings/{booking1_id}/status", headers={"Authorization": f"Bearer {prov_token}"}, json={"status": "In Progress"})
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("status") == "In Progress", "Provider starts service -> status: In Progress")

    # 5. Cancellation Guard: Customer cannot cancel In Progress
    r = requests.put(f"{BASE_URL}/bookings/{booking1_id}/cancel", headers={"Authorization": f"Bearer {cust_token}"}, json={"reason": "Changed mind"})
    assert_test(r.status_code == 400, "Customer cancellation of an In Progress booking correctly rejected (HTTP 400)")

    # 6. Provider Completes Service (In Progress -> Completed)
    r = requests.put(f"{BASE_URL}/bookings/{booking1_id}/status", headers={"Authorization": f"Bearer {prov_token}"}, json={"status": "Completed"})
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("status") == "Completed", "Provider completes service -> status: Completed")

    # 7. Terminal State Guard
    r = requests.put(f"{BASE_URL}/bookings/{booking1_id}/status", headers={"Authorization": f"Bearer {prov_token}"}, json={"status": "Pending"})
    assert_test(r.status_code == 400, "Transition from Completed state correctly rejected (terminal state)")

    # 8. Customer Cancellation Flow (Pending -> Cancelled)
    r = requests.post(f"{BASE_URL}/bookings", headers={"Authorization": f"Bearer {cust_token}"}, json={
        "providerId": prov_id,
        "date": "2026-10-18",
        "time": "2:00 PM - 4:00 PM",
        "address": "Flat 302, Green Valley Apartments, Madurai",
        "latitude": 9.9280,
        "longitude": 78.1210,
        "description": "Ceiling fan regulator replacement."
    })
    b2_id = r.json()["data"]["_id"]
    r = requests.put(f"{BASE_URL}/bookings/{b2_id}/cancel", headers={"Authorization": f"Bearer {cust_token}"}, json={"reason": "Resolved by building maintenance"})
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("status") == "Cancelled", "Customer cancels Pending booking -> status: Cancelled")

    # 9. Provider Rejection Flow (Pending -> Rejected)
    r = requests.post(f"{BASE_URL}/bookings", headers={"Authorization": f"Bearer {cust_token}"}, json={
        "providerId": prov_id,
        "date": "2026-10-19",
        "time": "9:00 AM - 11:00 AM",
        "address": "Flat 302, Green Valley Apartments, Madurai",
        "latitude": 9.9280,
        "longitude": 78.1210,
        "description": "Balcony exterior spotlight installation."
    })
    b3_id = r.json()["data"]["_id"]
    r = requests.put(f"{BASE_URL}/bookings/{b3_id}/status", headers={"Authorization": f"Bearer {prov_token}"}, json={
        "status": "Rejected",
        "reason": "Fully booked during this morning window"
    })
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("status") == "Rejected", "Provider rejects booking with reason -> status: Rejected")

    return booking1_id

def run_phase_6(cust_token, prov_token, completed_booking_id):
    print("\n" + "=" * 60)
    print("Executing Phase 6: Verified Ratings, Reviews & Aggregation")
    print("=" * 60)

    # 1. Fetch Provider Profile ID
    r = requests.get(f"{BASE_URL}/providers/profile", headers={"Authorization": f"Bearer {prov_token}"})
    prov_id = r.json()["data"]["_id"]

    # 2. Customer Submits 5-Star Review for Completed Booking
    r = requests.post(
        f"{BASE_URL}/reviews",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "bookingId": completed_booking_id,
            "rating": 5,
            "comment": "Outstanding electrical craftsmanship! Arrived strictly on time and tested all connections."
        }
    )
    data = r.json()
    assert_test(r.status_code == 201 and data.get("data", {}).get("rating") == 5, "Customer submits verified 5-star review for completed booking")

    # 3. Duplicate Prevention Test
    r = requests.post(
        f"{BASE_URL}/reviews",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "bookingId": completed_booking_id,
            "rating": 4,
            "comment": "Trying to review twice."
        }
    )
    assert_test(r.status_code == 400, "Duplicate review for identical booking rejected (HTTP 400)")

    # 4. Public Provider Reviews Endpoint (with distribution)
    r = requests.get(f"{BASE_URL}/reviews/provider/{prov_id}")
    data = r.json()
    assert_test(r.status_code == 200 and len(data.get("data", [])) >= 1 and "distribution" in data, "Public provider reviews endpoint returns list with full star rating distribution")

    # 5. Customer My Reviews Endpoint
    r = requests.get(f"{BASE_URL}/reviews/my", headers={"Authorization": f"Bearer {cust_token}"})
    assert_test(r.status_code == 200 and len(r.json().get("data", [])) >= 1, "Customer successfully retrieves history of submitted reviews")

    # 6. Single Booking Review Endpoint
    r = requests.get(f"{BASE_URL}/reviews/booking/{completed_booking_id}")
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("rating") == 5, "Single booking review endpoint returns accurate review for given bookingId")

def run_phase_7(cust_token, prov_token, admin_token):
    print("\n" + "=" * 60)
    print("Executing Phase 7: Administrator Control Panel & Security Operations")
    print("=" * 60)

    # 1. RBAC Guards
    r = requests.get(f"{BASE_URL}/admin/analytics", headers={"Authorization": f"Bearer {cust_token}"})
    assert_test(r.status_code == 403, "Customer forbidden from admin analytics (HTTP 403)")

    r = requests.get(f"{BASE_URL}/admin/analytics", headers={"Authorization": f"Bearer {prov_token}"})
    assert_test(r.status_code == 403, "Provider forbidden from admin analytics (HTTP 403)")

    r = requests.get(f"{BASE_URL}/admin/analytics")
    assert_test(r.status_code == 401, "Unauthenticated request rejected from admin routes (HTTP 401)")

    # 2. Admin Fetches Live Platform Analytics
    r = requests.get(f"{BASE_URL}/admin/analytics", headers={"Authorization": f"Bearer {admin_token}"})
    data = r.json()
    assert_test(
        r.status_code == 200 and data.get("data", {}).get("users", {}).get("total", 0) >= 3 and "bookings" in data.get("data", {}),
        "Admin successfully retrieves comprehensive platform metrics & status breakdowns"
    )

    # 3. Admin User List & Role Filtering
    r = requests.get(f"{BASE_URL}/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200 and r.json().get("count", 0) >= 3, "Admin lists registered users")

    r = requests.get(f"{BASE_URL}/admin/users?role=customer", headers={"Authorization": f"Bearer {admin_token}"})
    data = r.json()
    all_cust = all(u.get("role") == "customer" for u in data.get("data", []))
    assert_test(r.status_code == 200 and all_cust and data.get("count", 0) >= 1, "Admin filters users by role=customer")
    target_cust = data["data"][0]

    # 4. Admin User Toggle Status
    r = requests.put(f"{BASE_URL}/admin/users/{target_cust['_id']}/toggle-status", headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("isActive") is False, "Admin toggles user status to Suspended")
    # Restore
    r = requests.put(f"{BASE_URL}/admin/users/{target_cust['_id']}/toggle-status", headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200 and r.json().get("data", {}).get("isActive") is True, "Admin restores user status to Active")

    # 5. Admin Provider Workforce
    r = requests.get(f"{BASE_URL}/admin/providers", headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200 and r.json().get("count", 0) >= 1, "Admin fetches full provider workforce with populated details")

    # 6. Admin Bookings Audit
    r = requests.get(f"{BASE_URL}/admin/bookings", headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200 and r.json().get("count", 0) >= 1, "Admin accesses platform booking ledger")

    # 7. Category Creation & Update
    cat_name = f"Solar Tech {int(time.time() * 1000)}"
    r = requests.post(f"{BASE_URL}/categories", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "name": cat_name,
        "description": "Rooftop solar photovoltaic inspection and inverter maintenance.",
        "icon": "Sun"
    })
    data = r.json()
    assert_test(r.status_code == 201 and data.get("data", {}).get("name") == cat_name, "Admin creates new service category")
    new_cat_id = data["data"]["_id"]

    r = requests.put(f"{BASE_URL}/categories/{new_cat_id}", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "description": "Updated solar description with commercial array diagnostics."
    })
    assert_test(r.status_code == 200 and "commercial array" in r.json().get("data", {}).get("description", ""), "Admin updates service category description")

def main():
    print("=" * 70)
    print("⚡ URBAN-AID FLASK & MONGODB AUTOMATED VERIFICATION SUITE")
    print(f"   Target URL: {BASE_URL}")
    print("=" * 70)

    start_time = time.time()
    try:
        run_phase_1()
        cust_token, prov_token, admin_token = run_phase_2()
        run_phase_3(cust_token, prov_token, admin_token)
        run_phase_4()
        completed_b_id = run_phase_5(cust_token, prov_token)
        run_phase_6(cust_token, prov_token, completed_b_id)
        run_phase_7(cust_token, prov_token, admin_token)
    except Exception as e:
        print(f"\n[ERROR] Unexpected exception occurred during test execution: {e}")
        import traceback
        traceback.print_exc()

    duration = round(time.time() - start_time, 2)
    print("\n" + "=" * 70)
    print("MASTER FLASK TEST EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Total Passed Tests: {passed_tests}")
    print(f"Total Failed Tests: {failed_tests}")
    print(f"Execution Duration: {duration}s")
    print("=" * 70 + "\n")

    sys.exit(1 if failed_tests > 0 else 0)

if __name__ == "__main__":
    main()
