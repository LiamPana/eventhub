from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError

from app.extensions import login_manager


def _wants_json():
    return request.path.startswith("/api/")


def register_error_handlers(app):
    @login_manager.unauthorized_handler
    def unauthorized():
        if _wants_json():
            return jsonify(error="Autenticazione richiesta."), 401
        flash(login_manager.login_message, "info")
        return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))

    def make_handler(code, message):
        def handler(error):
            if _wants_json():
                return jsonify(error=message), code
            return render_template(f"errors/{code}.html"), code
        return handler

    app.register_error_handler(403, make_handler(403, "Non hai i permessi necessari."))
    app.register_error_handler(404, make_handler(404, "Risorsa non trovata."))
    app.register_error_handler(400, make_handler(400, "Richiesta non valida."))

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        if _wants_json():
            return jsonify(error="Token CSRF non valido."), 400
        return render_template("errors/400.html"), 400
