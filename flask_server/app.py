import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_server.config import Config
from flask_server.db import init_indexes
from flask_server.routes.health_routes import health_bp
from flask_server.routes.auth_routes import auth_bp
from flask_server.routes.category_routes import category_bp
from flask_server.routes.provider_routes import provider_bp
from flask_server.routes.customer_routes import customer_bp
from flask_server.routes.booking_routes import booking_bp
from flask_server.routes.review_routes import review_bp
from flask_server.routes.admin_routes import admin_bp
from flask_server.routes.web_routes import web_bp

def create_app(config_class=Config):
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    
    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
    )
    app.config.from_object(config_class)
    app.secret_key = config_class.SECRET_KEY

    # Enable CORS for API clients
    allowed_origins = [
        config_class.CLIENT_URL,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:3000",
    ]
    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins + ["*"]}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    )

    # Initialize database indexes
    with app.app_context():
        init_indexes()

    # Register HTML & CSS Web Routes (Jinja2 SSR Frontend)
    app.register_blueprint(web_bp)

    # API base catalog route
    @app.route("/api", methods=["GET"])
    @app.route("/api/", methods=["GET"])
    def api_catalog():
        return jsonify({
            "success": True,
            "message": "Welcome to UrbanAid Local Service Booking API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/api/health",
                "auth": "/api/auth",
                "categories": "/api/categories",
                "providers": "/api/providers",
                "customers": "/api/customers",
                "bookings": "/api/bookings",
                "reviews": "/api/reviews",
                "admin": "/api/admin",
            },
        }), 200

    # Register modular REST Blueprints
    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(category_bp, url_prefix="/api/categories")
    app.register_blueprint(provider_bp, url_prefix="/api/providers")
    app.register_blueprint(customer_bp, url_prefix="/api/customers")
    app.register_blueprint(booking_bp, url_prefix="/api/bookings")
    app.register_blueprint(review_bp, url_prefix="/api/reviews")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    # Centralized Error Handlers
    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith("/api"):
            return jsonify({
                "success": False,
                "message": f"Resource not found: {request.method} {request.path}",
            }), 404
        return f"<div style='font-family: sans-serif; text-align: center; padding: 4rem;'><h2>404 - Page Not Found</h2><p>The requested page {request.path} could not be found.</p><a href='/'>&larr; Return to UrbanAid Home</a></div>", 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        if request.path.startswith("/api"):
            return jsonify({
                "success": False,
                "message": f"Method {request.method} not allowed for {request.path}",
            }), 405
        return f"<div style='font-family: sans-serif; text-align: center; padding: 4rem;'><h2>405 - Method Not Allowed</h2><a href='/'>&larr; Return Home</a></div>", 405

    @app.errorhandler(Exception)
    def handle_exception(e):
        if request.path.startswith("/api"):
            return jsonify({
                "success": False,
                "message": str(e) or "An internal server error occurred",
            }), 500
        return f"<div style='font-family: sans-serif; text-align: center; padding: 4rem;'><h2>Server Error</h2><p>{str(e)}</p><a href='/'>&larr; Return Home</a></div>", 500

    return app

if __name__ == "__main__":
    app = create_app()
    port = Config.PORT
    print(f"[Server] UrbanAid Flask Web App starting on http://localhost:{port}...")
    app.run(host="0.0.0.0", port=port, debug=Config.DEBUG)
