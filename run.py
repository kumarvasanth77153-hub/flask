#!/usr/bin/env python3
"""
UrbanAid — Local Service Booking & Workforce Management System
Flask & MongoDB Backend Runner
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask_server.app import create_app
from flask_server.config import Config

app = create_app()

if __name__ == "__main__":
    port = Config.PORT
    print("=" * 70)
    print("[*] UrbanAid Flask & MongoDB Backend Service")
    print(f"   Listening on: http://127.0.0.1:{port}")
    print(f"   Health Check: http://127.0.0.1:{port}/api/health")
    print(f"   Environment : {Config.NODE_ENV}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=Config.DEBUG)
