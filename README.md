# UrbanAid — Local Service Booking & Workforce Management System
### Python Flask, Jinja2, HTML5, CSS3 & MongoDB Architecture

> **Academic Course Reference**: `23CS11E - Web Framework Using Python`  
> **Institution**: National Engineering College (Autonomous), Kovilpatti  
> **Tech Stack**: Pure **Python Flask**, **Jinja2 Templates**, **HTML5**, **CSS3**, and **MongoDB** (PyMongo) — **No React or Node.js required!**

---

## 🌟 Key Features

- **100% Python Flask & Jinja2 Server-Side Rendered (SSR)**: Clean, monolithic architecture adhering strictly to academic Web Framework curriculum requirements.
- **Pure HTML5 & Vanilla CSS3 Interface**: Custom modern design system featuring responsive grid layouts, card hover micro-animations, glassmorphism headers, and mobile optimization without third-party frontend frameworks.
- **MongoDB Database Engine**: Native integration via PyMongo for users, provider profiles, service taxonomies, booking lifecycles, and verified reviews.
- **Multi-Role Role-Based Access Control (RBAC)**: Dedicated interfaces and session-secured routes for:
  - 👤 **Customer Portal**: Search verified services, filter by trade, schedule doorstep visits, monitor appointment status, and submit star reviews.
  - 🛠️ **Service Provider Portal**: Manage live availability, inspect incoming service requests, accept/reject jobs, and advance workflow stages (`In Progress` → `Completed`).
  - ⚙️ **Platform Admin Console**: Real-time system analytics, user access control (Activate/Suspend), and dynamic service taxonomy creation.
- **One-Click Demo Authentication**: Instant pre-fill credentials buttons for seamless faculty demonstrations.
- **53/53 Automated Test Suite**: Built-in test runner validating authentication, booking state machine, and data consistency.

---

## 🏗️ Project Structure

```
forflask/
├── flask_server/                  # Python Flask Application Core
│   ├── app.py                     # Flask application factory & blueprint registry
│   ├── config.py                  # Environment & database configuration
│   ├── db.py                      # MongoDB connection & index manager
│   ├── middleware/                # Authentication & RBAC middleware
│   ├── routes/                    # Modular route handlers
│   │   ├── web_routes.py          # HTML/CSS Jinja2 Views (/, /services, /login, /dashboards)
│   │   ├── auth_routes.py         # REST Auth endpoints (/api/auth)
│   │   ├── booking_routes.py      # REST Booking endpoints (/api/bookings)
│   │   ├── provider_routes.py     # REST Provider endpoints (/api/providers)
│   │   ├── customer_routes.py     # REST Customer endpoints (/api/customers)
│   │   ├── category_routes.py     # REST Category endpoints (/api/categories)
│   │   ├── review_routes.py       # REST Review endpoints (/api/reviews)
│   │   ├── admin_routes.py        # REST Admin endpoints (/api/admin)
│   │   └── health_routes.py       # Health check endpoint (/api/health)
│   ├── static/                    # Static Assets (Pure CSS & Vanilla JS)
│   │   ├── css/
│   │   │   └── style.css          # Master CSS3 Design System & styling tokens
│   │   └── js/
│   │       └── main.js            # Vanilla JS (Modals, quick-logins, alerts)
│   ├── templates/                 # Jinja2 HTML5 Templates
│   │   ├── base.html              # Global navigation, alerts, layout shell & footer
│   │   ├── index.html             # Homepage, hero banner, category cards & top pros
│   │   ├── services.html          # Service catalog, category filters & provider cards
│   │   ├── book.html              # Service scheduling & appointment booking form
│   │   ├── login.html             # Role login form with 1-click demo buttons
│   │   ├── register.html          # Registration with customer/provider role toggle
│   │   ├── customer_dashboard.html# Customer bookings table, statuses & review modal
│   │   ├── provider_dashboard.html# Provider request inbox, job stages & earnings
│   │   └── admin_dashboard.html   # Admin system metrics, categories & user RBAC
│   ├── scripts/                   # Automated test runners & database seed scripts
│   │   ├── seed_db.py             # MongoDB seed script
│   │   └── test_runner.py         # Automated 53-test verification suite
│   └── utils/                     # Password hashing, JWT & serializers
│
├── run.py                         # Application entrypoint runner
├── requirements.txt               # Python package dependencies
├── UrbanAid_Micro_Project_Report.pdf # Comprehensive 21-page Academic Project Report
├── generate_report.py             # Academic PDF report generator script
└── README.md                      # Project documentation
```

---

## 🚀 How to Run the Application

### 1. Prerequisites
- **Python**: 3.10+ installed
- **MongoDB**: Community Server running on `127.0.0.1:27017`

### 2. Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Start the Flask Application
```powershell
python run.py
```

### 4. Open in Your Web Browser
Open your browser and navigate directly to:
👉 **[http://localhost:5000](http://localhost:5000)**

---

## 🔑 Demo Login Credentials

You can use the built-in **One-Click Demo Fill buttons** on the login page ([http://localhost:5000/login](http://localhost:5000/login)), or type the credentials manually:

| Role | Email | Password | Available Features |
| :--- | :--- | :--- | :--- |
| **Customer** | `customer@urbanaid.com` | `Customer@123` | Book services, view appointments, leave star reviews |
| **Provider** | `provider@urbanaid.com` | `Provider@123` | Accept/reject booking requests, update job stage, toggle availability |
| **Admin** | `admin@urbanaid.com` | `Admin@123` | Platform volume & stats, category management, suspend/activate users |

---

## 🧪 Running Automated Tests

To verify all backend routes and database operations:
```powershell
python flask_server/scripts/test_runner.py
```
*Expected Output: `Total Passed Tests: 53 | Total Failed Tests: 0`*
