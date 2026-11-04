from flask import jsonify


def register_blueprints(app):
    from app.routes import auth, dev, google_oauth, habits, tasks, users

    for module in (auth, google_oauth, dev, users, habits, tasks):
        app.register_blueprint(module.bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})
