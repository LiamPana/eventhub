from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def role_required(*roles):
    """Richiede login e uno dei ruoli indicati (l'admin passa sempre).

    Non loggato -> 401/redirect al login; ruolo sbagliato -> 403.
    """
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not current_user.has_role(*roles):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator
