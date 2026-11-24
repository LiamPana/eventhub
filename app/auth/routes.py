from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.auth import bp
from app.auth.forms import LoginForm, RegisterForm
from app.extensions import db
from app.models import User


def _is_safe_next(target):
    """Accetta solo percorsi interni (evita l'open redirect)."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc and target.startswith("/")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            role=form.role.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Registrazione completata: ora puoi accedere.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash("Credenziali non valide.", "error")
            return render_template("auth/login.html", form=form), 401
        login_user(user, remember=form.remember.data)
        next_url = request.args.get("next")
        return redirect(next_url if _is_safe_next(next_url) else url_for("main.index"))
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Sei uscito dall'account.", "info")
    return redirect(url_for("main.index"))
