from flask import abort, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.api import bp
from app.auth.decorators import role_required
from app.events.services import (CheckInError, can_manage_event,
                                 check_in_ticket, event_stats)
from app.extensions import db
from app.models import Event, EventStatus, Order, Role, Ticket
from app.utils import utcnow


def event_to_dict(event):
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "start_at": event.start_at.isoformat(),
        "end_at": event.end_at.isoformat(),
        "status": event.status,
        "capacity": event.capacity,
        "tickets_left": event.tickets_left,
        "organizer": event.organizer.username,
        "ticket_types": [
            {"id": tt.id, "name": tt.name, "price": str(tt.price),
             "quantity": tt.quantity, "available": tt.available}
            for tt in event.ticket_types
        ],
    }


@bp.route("/health")
def health():
    return jsonify(status="ok")


@bp.route("/events")
def list_events():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)
    query = Event.query.filter(Event.status == EventStatus.PUBLISHED, Event.end_at >= utcnow())
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Event.title.ilike(like), Event.location.ilike(like)))
    pagination = query.order_by(Event.start_at).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        items=[event_to_dict(e) for e in pagination.items],
        page=pagination.page, pages=pagination.pages, total=pagination.total,
    )


@bp.route("/events/<int:event_id>")
def get_event(event_id):
    event = db.get_or_404(Event, event_id)
    if event.status == EventStatus.DRAFT and not can_manage_event(current_user, event):
        abort(404)
    return jsonify(event_to_dict(event))


@bp.route("/events/<int:event_id>/stats")
@login_required
def get_stats(event_id):
    event = db.get_or_404(Event, event_id)
    if not can_manage_event(current_user, event):
        abort(403)
    stats = event_stats(event)
    stats["revenue"] = str(stats["revenue"])
    for t in stats["ticket_types"]:
        t["price"] = str(t["price"])
    return jsonify(stats)


@bp.route("/me/tickets")
@login_required
def my_tickets():
    tickets = (
        Ticket.query.join(Order, Ticket.order_id == Order.id)
        .filter(Order.user_id == current_user.id)
        .order_by(Ticket.id.desc())
        .all()
    )
    return jsonify(items=[
        {"code": t.code, "event": t.event.title, "type": t.ticket_type.name,
         "used": t.is_used} for t in tickets
    ])


@bp.route("/checkin", methods=["POST"])
@role_required(Role.STAFF, Role.ORGANIZER)
def checkin():
    if not request.is_json:
        return jsonify(error="Content-Type deve essere application/json."), 415
    code = (request.get_json(silent=True) or {}).get("code")
    if not code:
        return jsonify(error="Campo 'code' obbligatorio."), 400
    try:
        ticket = check_in_ticket(code, current_user)
    except CheckInError as exc:
        return jsonify(error=str(exc)), exc.status_code
    return jsonify(
        status="checked_in", event=ticket.event.title, ticket_type=ticket.ticket_type.name,
        holder=ticket.order.user.username, checked_in_at=ticket.checked_in_at.isoformat(),
    )
