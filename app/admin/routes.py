from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin import bp
from app.auth.decorators import role_required
from app.extensions import db
from app.models import Role, User


@bp.route("/users")
@role_required(Role.ADMIN)
def users():
    all_users = User.query.order_by(User.id).all()
    return render_template("admin/users.html", users=all_users, roles=Role.ALL)


@bp.route("/users/<int:user_id>/role", methods=["POST"])
@role_required(Role.ADMIN)
def set_role(user_id):
    user = db.get_or_404(User, user_id)
    role = request.form.get("role")
    if role not in Role.ALL:
        flash("Ruolo non valido.", "error")
    elif user.id == current_user.id:
        flash("Non puoi modificare il tuo stesso ruolo.", "error")
    else:
        user.role = role
        db.session.commit()
        flash(f"Ruolo di {user.username} aggiornato a «{role}».", "success")
    return redirect(url_for("admin.users"))
