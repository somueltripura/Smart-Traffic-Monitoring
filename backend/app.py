import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from backend.config import Config
from backend.database.db import init_database
from backend.routes.analytics import analytics_bp
from backend.routes.api import api_bp
from backend.routes.cameras import cameras_bp
from backend.routes.stream import stream_bp
from backend.utils.logger import setup_logger

logger = setup_logger("App")


def create_app() -> Flask:
    """Application factory for Smart Traffic Monitoring System."""
    frontend_dir = Config.BASE_DIR / "frontend"

    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path="",
    )

    # Configuration
    app.config.from_object(Config)

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Database
    try:
        init_database()
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)

    # Register Blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(cameras_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(analytics_bp)

    # Serve Frontend UI
    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    # Global Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Resource not found",
            "message": str(error),
            "status_code": 404,
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("Internal Server Error: %s", error)
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the server.",
            "status_code": 500,
        }), 500

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": "Bad Request",
            "message": str(error),
            "status_code": 400,
        }), 400

    logger.info("Smart Traffic Monitoring Flask Application initialized.")
    return app


if __name__ == "__main__":
    app = create_app()
    port = Config.PORT
    host = Config.HOST
    logger.info("Starting Traffic Monitoring Server on http://%s:%d", host, port)
    app.run(host=host, port=port, debug=Config.DEBUG, threaded=True)
