import time
import os
import datetime
from flask import Blueprint, jsonify
from flask_server.db import get_client, get_db

health_bp = Blueprint("health", __name__)
_START_TIME = time.time()

@health_bp.route("/", methods=["GET"])
@health_bp.route("/health", methods=["GET"])
def health_check():
    """Returns database connectivity and API runtime health metrics."""
    db_status = "disconnected"
    host_name = "127.0.0.1"
    db_name = "local_service_db"

    try:
        client = get_client()
        # Ping the server to check connectivity
        client.admin.command("ping")
        db_status = "connected"
        host_info = client.address
        if host_info:
            host_name = f"{host_info[0]}:{host_info[1]}"
        db = get_db()
        db_name = db.name
    except Exception as e:
        db_status = "error"

    uptime_sec = int(time.time() - _START_TIME)

    health_data = {
        "success": db_status == "connected",
        "message": "Local Service Booking & Workforce Management API is healthy",
        "system": {
            "appName": "UrbanAid Platform API",
            "version": "1.0.0",
            "environment": os.environ.get("NODE_ENV", "development"),
            "uptime": f"{uptime_sec} seconds",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "memory": {
                "rss": "N/A",
                "heapUsed": "N/A",
            },
        },
        "database": {
            "status": db_status,
            "host": host_name,
            "name": db_name,
        },
    }

    status_code = 200 if db_status == "connected" else 503
    return jsonify(health_data), status_code
