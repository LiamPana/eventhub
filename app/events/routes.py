import io

import qrcode
from flask import (abort, flash, redirect, render_template, request,
                   send_file, url_for)
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.auth.decorators import role_required
from app.events import bp
from app.events.forms import (CheckInForm, DiscountForm, EventForm,
                              TicketTypeForm)
from app.events.services import (CheckInError, PurchaseError, can_manage_event,
                                 check_in_ticket, event_stats,
                                 purchase_tickets)
from app.extensions import db
from app.models import (DiscountCode, Event, EventStatus, Order, Role, Ticket,
                        TicketType)
from app.utils import utcnow


def get_managed_event(event_id):
    event = db.get_or_404(Event, event_id)
    if not can_manage_event(current_user, event):
        abort(403)
    return event


def get_visible_event(event_id):
    """Le bozze sono visibili solo a chi gestisce l'evento."""
    event = db.get_or_404(Event, event_id)
    if event.status == EventStatus.DRAFT and not can_manage_event(current_user, event):
        abort(404)
    return event


# ---------------------------------------------------------------- pubbliche
@bp.route("/")
def list_events():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Event.query.filter(
        Event.status == EventStatus.PUBLISHED, Event.end_at >= utcnow()
    )
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Event.title.ilike(like), Event.location.ilike(like)))
    pagination = query.order_by(Event.start_at).paginate(page=page, per_page=9, error_out=False)
    return render_template("events/list.html", pagination=pagination, q=q)


@bp.route("/<int:event_id>")
def detail(event_id):
    event = get_visible_event(event_id)
    return render_template(
        "events/detail.html", event=event,
        can_manage=can_manage_event(current_user, event),
    )


# ------------------------------------------------------------------ acquisti
@bp.route("/<int:event_id>/buy", methods=["POST"])
@login_required
def buy(event_id):
    event = get_visible_event(event_id)
    quantities = {
        tt.id: max(request.form.get(f"qty_{tt.id}", 0, type=int), 0)
        for tt in event.ticket_types
    }
    try:
        order = purchase_tickets(current_user, event, quantities, request.form.get("discount_code"))
    except PurchaseError as exc:
        flash(str(exc), "error")
        return redirect(url_for("events.detail", event_id=event.id))
    flash(f"Acquisto completato: {len(order.tickets)} biglietti, totale € {order.total:.2f}.", "success")
    return redirect(url_for("events.my_tickets"))


@bp.route("/my-tickets")
@login_required
def my_tickets():
    tickets = (
        Ticket.query.join(Order, Ticket.order_id == Order.id)
        .filter(Order.user_id == current_user.id)
        .order_by(Ticket.id.desc())
        .all()
    )
    return render_template("events/my_tickets.html", tickets=tickets)


@bp.route("/tickets/<code>/qr.png")
@login_required
def ticket_qr(code):
    ticket = Ticket.query.filter_by(code=code).first_or_404()
    if ticket.order.user_id != current_user.id and not current_user.has_role(Role.STAFF):
        abort(403)
    buffer = io.BytesIO()
    qrcode.make(ticket.code).save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")


# ------------------------------------------------------------ check-in (staff)
@bp.route("/checkin", methods=["GET", "POST"])
@role_required(Role.STAFF, Role.ORGANIZER)
def checkin():
    form = CheckInForm()
    ticket = None
    if form.validate_on_submit():
        try:
            ticket = check_in_ticket(form.code.data, current_user)
            flash("Ingresso registrato.", "success")
            form.code.data = ""
        except CheckInError as exc:
            flash(str(exc), "error")
    return render_template("events/checkin.html", form=form, ticket=ticket)


# ------------------------------------------------- gestione (organizzatore)
@bp.route("/mine")
@role_required(Role.ORGANIZER)
def manage():
    query = Event.query
    if current_user.role != Role.ADMIN:
        query = query.filter_by(organizer_id=current_user.id)
    return render_template("events/manage.html", events=query.order_by(Event.start_at.desc()).all())


@bp.route("/new", methods=["GET", "POST"])
@role_required(Role.ORGANIZER)
def create():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(organizer_id=current_user.id)
        form.populate_obj(event)
        event.description = event.description or ""
        db.session.add(event)
        db.session.commit()
        flash("Evento creato come bozza: aggiungi i tipi di biglietto e pubblicalo.", "success")
        return redirect(url_for("events.detail", event_id=event.id))
    return render_template("events/event_form.html", form=form, title="Nuovo evento")


@bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@role_required(Role.ORGANIZER)
def edit(event_id):
    event = get_managed_event(event_id)
    form = EventForm(obj=event)
    if form.validate_on_submit():
        if form.capacity.data < event.allocated_quantity:
            form.capacity.errors.append(
                f"I tipi di biglietto definiti sommano {event.allocated_quantity} posti."
            )
        else:
            form.populate_obj(event)
            event.description = event.description or ""
            db.session.commit()
            flash("Evento aggiornato.", "success")
            return redirect(url_for("events.detail", event_id=event.id))
    return render_template("events/event_form.html", form=form, title="Modifica evento")


@bp.route("/<int:event_id>/status", methods=["POST"])
@role_required(Role.ORGANIZER)
def change_status(event_id):
    event = get_managed_event(event_id)
    action = request.form.get("action")
    if action == "publish":
        if event.status != EventStatus.DRAFT:
            flash("Solo le bozze possono essere pubblicate.", "error")
        elif not event.ticket_types:
            flash("Aggiungi almeno un tipo di biglietto prima di pubblicare.", "error")
        else:
            event.status = EventStatus.PUBLISHED
            db.session.commit()
            flash("Evento pubblicato.", "success")
    elif action == "cancel":
        if event.status == EventStatus.CANCELLED:
            flash("L'evento è già annullato.", "error")
        else:
            event.status = EventStatus.CANCELLED
            db.session.commit()
            flash("Evento annullato.", "info")
    else:
        flash("Azione non valida.", "error")
    return redirect(url_for("events.detail", event_id=event.id))


@bp.route("/<int:event_id>/ticket-types/new", methods=["GET", "POST"])
@role_required(Role.ORGANIZER)
def add_ticket_type(event_id):
    event = get_managed_event(event_id)
    form = TicketTypeForm()
    if form.validate_on_submit():
        remaining = event.capacity - event.allocated_quantity
        if form.quantity.data > remaining:
            form.quantity.errors.append(f"Capienza residua da assegnare: {remaining}.")
        else:
            db.session.add(TicketType(
                event_id=event.id, name=form.name.data.strip(),
                price=form.price.data, quantity=form.quantity.data,
            ))
            db.session.commit()
            flash("Tipo di biglietto aggiunto.", "success")
            return redirect(url_for("events.detail", event_id=event.id))
    return render_template("events/ticket_type_form.html", form=form, event=event)


@bp.route("/<int:event_id>/ticket-types/<int:type_id>/delete", methods=["POST"])
@role_required(Role.ORGANIZER)
def delete_ticket_type(event_id, type_id):
    event = get_managed_event(event_id)
    tt = TicketType.query.filter_by(id=type_id, event_id=event.id).first_or_404()
    if tt.sold:
        flash("Non puoi eliminare un tipo di biglietto già venduto.", "error")
    else:
        db.session.delete(tt)
        db.session.commit()
        flash("Tipo di biglietto eliminato.", "info")
    return redirect(url_for("events.detail", event_id=event.id))


@bp.route("/<int:event_id>/discounts/new", methods=["GET", "POST"])
@role_required(Role.ORGANIZER)
def add_discount(event_id):
    event = get_managed_event(event_id)
    form = DiscountForm()
    if form.validate_on_submit():
        if DiscountCode.query.filter_by(code=form.code.data).first():
            form.code.errors.append("Codice già esistente.")
        else:
            db.session.add(DiscountCode(
                event_id=event.id, code=form.code.data, percent=form.percent.data,
                max_uses=form.max_uses.data, expires_at=form.expires_at.data,
            ))
            db.session.commit()
            flash("Codice sconto creato.", "success")
            return redirect(url_for("events.detail", event_id=event.id))
    return render_template("events/discount_form.html", form=form, event=event)


@bp.route("/<int:event_id>/report")
@role_required(Role.ORGANIZER)
def report(event_id):
    event = get_managed_event(event_id)
    return render_template("events/report.html", event=event, stats=event_stats(event))
