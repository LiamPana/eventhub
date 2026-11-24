from flask import render_template

from app.main import bp
from app.models import Event, EventStatus
from app.utils import utcnow


@bp.route("/")
def index():
    upcoming = (
        Event.query.filter(Event.status == EventStatus.PUBLISHED, Event.end_at >= utcnow())
        .order_by(Event.start_at)
        .limit(3)
        .all()
    )
    return render_template("index.html", events=upcoming)
