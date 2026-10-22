#!/usr/bin/env python3
"""
UrbanAid — Database Seeder Script (Python / MongoDB)
Seeds core trade categories, primary test accounts, and workforce provider profiles.
"""
import sys
import os
import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask_server.db import get_db, init_indexes
from flask_server.utils.security import hash_password

CATEGORIES = [
    {
        "name": "Electrician",
        "description": "Expert residential & commercial electrical repairs, wiring, switches, and appliance installations.",
        "icon": "Zap",
    },
    {
        "name": "Plumber",
        "description": "Pipe leakage repairs, sanitary fixture installations, drain unblocking, and water tank setups.",
        "icon": "Droplet",
    },
    {
        "name": "Carpenter",
        "description": "Custom furniture assembly, door locks, modular kitchen fittings, and precision woodwork.",
        "icon": "Hammer",
    },
    {
        "name": "AC Technician",
        "description": "Air conditioner servicing, gas refilling, filter cleaning, cooling diagnostics, and installation.",
        "icon": "Wind",
    },
    {
        "name": "Appliance Repair",
        "description": "Diagnosis and repair of refrigerators, washing machines, microwaves, and domestic appliances.",
        "icon": "Tv",
    },
    {
        "name": "Painter",
        "description": "Interior and exterior wall painting, waterproof coatings, surface sanding, and texture design.",
        "icon": "Paintbrush",
    },
    {
        "name": "Cleaning",
        "description": "Deep home cleaning, kitchen degreasing, bathroom sanitization, and sofa shampooing.",
        "icon": "Sparkles",
    },
    {
        "name": "Mechanic",
        "description": "Two-wheeler and four-wheeler roadside assistance, periodic servicing, and brake repairs.",
        "icon": "Wrench",
    },
]

USERS = [
    {
        "name": "Platform Administrator",
        "email": "admin@urbanaid.com",
        "password": "Admin@123",
        "phone": "9876543210",
        "role": "admin",
        "address": "UrbanAid Headquarters, Central Plaza",
        "latitude": 9.9252,
        "longitude": 78.1198,
        "isActive": True,
    },
    {
        "name": "Rahul Sharma",
        "email": "customer@urbanaid.com",
        "password": "Customer@123",
        "phone": "9876543211",
        "role": "customer",
        "address": "Flat 302, Green Valley Apartments, Madurai",
        "latitude": 9.9280,
        "longitude": 78.1210,
        "isActive": True,
    },
    {
        "name": "Karthik Electrician",
        "email": "provider@urbanaid.com",
        "password": "Provider@123",
        "phone": "9876543212",
        "role": "provider",
        "address": "Shop 12, Anna Nagar Main Road, Madurai",
        "latitude": 9.9320,
        "longitude": 78.1265,
        "isActive": True,
    },
]

ADDITIONAL_PROVIDERS = [
    {
        "user": {
            "name": "Ramesh Plumber",
            "email": "ramesh.plumber@urbanaid.com",
            "password": "Provider@123",
            "phone": "9876543220",
            "role": "provider",
            "address": "14 KK Nagar, Madurai",
            "latitude": 9.9230,
            "longitude": 78.1400,
            "isActive": True,
        },
        "categoryName": "Plumber",
        "profile": {
            "experience": 7,
            "serviceCharge": 350.0,
            "description": "Specialist in bathroom plumbing, geyser fittings, high-pressure line leakages, and drainage cleaning.",
            "latitude": 9.9230,
            "longitude": 78.1400,
            "address": "14 KK Nagar, Madurai",
            "availability": "Available",
            "isAvailable": True,
            "averageRating": 4.7,
            "totalReviews": 19,
        },
    },
    {
        "user": {
            "name": "Arun Carpenter",
            "email": "arun.carpenter@urbanaid.com",
            "password": "Provider@123",
            "phone": "9876543221",
            "role": "provider",
            "address": "52 Simmakkal Main Road, Madurai",
            "latitude": 9.9380,
            "longitude": 78.1180,
            "isActive": True,
        },
        "categoryName": "Carpenter",
        "profile": {
            "experience": 10,
            "serviceCharge": 500.0,
            "description": "Master carpenter for modular wardrobes, solid wood repairs, lock installations, and customized shelving.",
            "latitude": 9.9380,
            "longitude": 78.1180,
            "address": "52 Simmakkal Main Road, Madurai",
            "availability": "Available",
            "isAvailable": True,
            "averageRating": 4.9,
            "totalReviews": 32,
        },
    },
    {
        "user": {
            "name": "Vignesh AC Expert",
            "email": "vignesh.ac@urbanaid.com",
            "password": "Provider@123",
            "phone": "9876543222",
            "role": "provider",
            "address": "7 Kalavasal Junction, Madurai",
            "latitude": 9.9310,
            "longitude": 78.0990,
            "isActive": True,
        },
        "categoryName": "AC Technician",
        "profile": {
            "experience": 4,
            "serviceCharge": 600.0,
            "description": "Split and window AC installation, jet pump deep servicing, gas leak checks, and compressor repairs.",
            "latitude": 9.9310,
            "longitude": 78.0990,
            "address": "7 Kalavasal Junction, Madurai",
            "availability": "Available",
            "isAvailable": True,
            "averageRating": 4.6,
            "totalReviews": 15,
        },
    },
]

def seed_database():
    print("=" * 60)
    print("[*] Seeding UrbanAid MongoDB Database...")
    print("=" * 60)

    db = get_db()
    init_indexes()
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Seed Categories
    category_map = {}
    for cat in CATEGORIES:
        existing = db.servicecategories.find_one({"name": cat["name"]})
        if not existing:
            cat_doc = {**cat, "isActive": True, "createdAt": now, "updatedAt": now}
            ins = db.servicecategories.insert_one(cat_doc)
            category_map[cat["name"]] = ins.inserted_id
            print(f"  [+] Created category: {cat['name']}")
        else:
            category_map[cat["name"]] = existing["_id"]
            print(f"  [.] Category exists: {cat['name']}")

    # 2. Seed Primary Users
    user_map = {}
    for u in USERS:
        email = u["email"].lower()
        existing = db.users.find_one({"email": email})
        if not existing:
            doc = {
                **u,
                "email": email,
                "password": hash_password(u["password"]),
                "createdAt": now,
                "updatedAt": now,
            }
            ins = db.users.insert_one(doc)
            user_map[email] = ins.inserted_id
            print(f"  [+] Created user: {u['name']} ({u['role']})")
        else:
            user_map[email] = existing["_id"]
            # Ensure password is valid bcrypt
            db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {"password": hash_password(u["password"]), "updatedAt": now}}
            )
            print(f"  [.] User exists (updated password): {u['email']}")

    # 3. Seed ProviderProfile for Karthik Electrician
    karthik_id = user_map.get("provider@urbanaid.com")
    if karthik_id:
        existing_karthik_profile = db.providerprofiles.find_one({"userId": karthik_id})
        if not existing_karthik_profile:
            karthik_profile = {
                "userId": karthik_id,
                "serviceCategory": category_map["Electrician"],
                "experience": 5,
                "serviceCharge": 400.0,
                "description": "Certified residential & commercial electrician with 5 years experience in circuit wiring, DB box setup, inverter installations, and short-circuit troubleshooting.",
                "latitude": 9.9320,
                "longitude": 78.1265,
                "address": "Shop 12, Anna Nagar Main Road, Madurai",
                "availability": "Available",
                "isAvailable": True,
                "averageRating": 4.8,
                "totalReviews": 24,
                "isActive": True,
                "createdAt": now,
                "updatedAt": now,
            }
            db.providerprofiles.insert_one(karthik_profile)
            print("  [+] Created ProviderProfile for Karthik Electrician")
        else:
            print("  [.] ProviderProfile exists for Karthik Electrician")

    # 4. Seed Additional Providers
    for item in ADDITIONAL_PROVIDERS:
        u_info = item["user"]
        email = u_info["email"].lower()
        prov_user = db.users.find_one({"email": email})
        if not prov_user:
            u_doc = {
                **u_info,
                "email": email,
                "password": hash_password(u_info["password"]),
                "createdAt": now,
                "updatedAt": now,
            }
            ins = db.users.insert_one(u_doc)
            user_id = ins.inserted_id
            print(f"  [+] Created provider user: {u_info['name']}")
        else:
            user_id = prov_user["_id"]
            db.users.update_one(
                {"_id": user_id},
                {"$set": {"password": hash_password(u_info["password"]), "updatedAt": now}}
            )
            print(f"  [.] Provider user exists: {email}")

        prof_doc = db.providerprofiles.find_one({"userId": user_id})
        if not prof_doc:
            p_data = {
                **item["profile"],
                "userId": user_id,
                "serviceCategory": category_map[item["categoryName"]],
                "isActive": True,
                "createdAt": now,
                "updatedAt": now,
            }
            db.providerprofiles.insert_one(p_data)
            print(f"  [+] Created ProviderProfile for {u_info['name']} ({item['categoryName']})")
        else:
            print(f"  [.] ProviderProfile exists for {u_info['name']}")

    print("\n[OK] Seeding complete! Database is primed and ready.")

if __name__ == "__main__":
    seed_database()
