"""Logica di business: acquisto, check-in e statistiche.

Tenuta fuori dalle route così è riutilizzabile (UI e API) e testabile.
"""
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select

from app.extensions import db
from app.models import (DiscountCode, Event, EventStatus, Order, OrderStatus,
                        Role, Ticket, TicketType)
from app.utils import utcnow

MAX_TICKETS_PER_ORDER = 10
CENT = Decimal("0.01")


class PurchaseError(Exception):
    pass


class CheckInError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def can_manage_event(user, event):
    """Admin o organizzatore proprietario dell'evento."""
    return user.is_authenticated and (
        user.role == Role.ADMIN or event.organizer_id == user.id
    )


def purchase_tickets(user, event, quantities, discount_code=None):
    """Acquista biglietti per un evento (pagamento simulato).

    quantities: {ticket_type_id: quantità}.
    Il lock sulla riga dell'evento (SELECT ... FOR UPDATE su MySQL) serializza gli
    acquisti concorrenti: due utenti non possono superare insieme la capienza.
    """
    try:
        return _purchase(user, event, quantities, discount_code)
    except PurchaseError:
        db.session.rollback()  # rilascia il lock
        raise


def _purchase(user, event, quantities, discount_code):
    quantities = {tid: q for tid, q in quantities.items() if q > 0}
    if not quantities:
        raise PurchaseError("Seleziona almeno un biglietto.")
    if sum(quantities.values()) > MAX_TICKETS_PER_ORDER:
        raise PurchaseError(f"Puoi acquistare al massimo {MAX_TICKETS_PER_ORDER} biglietti per ordine.")

    locked = db.session.execute(
        select(Event).where(Event.id == event.id).with_for_update()
    ).scalar_one()
    if locked.status != EventStatus.PUBLISHED:
        raise PurchaseError("Questo evento non è acquistabile.")
    if locked.is_over:
        raise PurchaseError("L'evento è già terminato.")

    types = TicketType.query.filter(
        TicketType.event_id == locked.id, TicketType.id.in_(list(quantities))
    ).all()
    if len(types) != len(quantities):
        raise PurchaseError("Tipo di biglietto non valido.")

    requested = sum(quantities.values())
    if requested > locked.tickets_left:
        raise PurchaseError(f"Capienza insufficiente: restano {locked.tickets_left} posti.")
    for tt in types:
        if quantities[tt.id] > tt.available:
            raise PurchaseError(f"Biglietti «{tt.name}» insufficienti: ne restano {tt.available}.")

    subtotal = sum((tt.price * quantities[tt.id] for tt in types), Decimal("0"))
    discount_amount = Decimal("0")
    code_obj = None
    if discount_code and discount_code.strip():
        code_obj = (
            DiscountCode.query.filter_by(code=discount_code.strip().upper(), event_id=locked.id)
            .with_for_update()
            .first()
        )
        if code_obj is None:
            raise PurchaseError("Codice sconto non valido.")
        if code_obj.expires_at and code_obj.expires_at < utcnow():
            raise PurchaseError("Il codice sconto è scaduto.")
        if code_obj.used_count >= code_obj.max_uses:
            raise PurchaseError("Il codice sconto ha esaurito gli utilizzi.")
        discount_amount = (subtotal * code_obj.percent / 100).quantize(CENT, ROUND_HALF_UP)
        code_obj.used_count += 1

    order = Order(
        user_id=user.id, event_id=locked.id, subtotal=subtotal,
        discount_amount=discount_amount, total=subtotal - discount_amount,
        status=OrderStatus.PAID, discount_code=code_obj,
    )
    for tt in types:
        for _ in range(quantities[tt.id]):
            order.tickets.append(Ticket(ticket_type_id=tt.id))
    db.session.add(order)
    db.session.commit()
    return order


def check_in_ticket(code, operator):
    """Registra l'ingresso. Lo staff può operare su ogni evento, l'organizzatore solo sui propri."""
    try:
        return _check_in(code, operator)
    except CheckInError:
        db.session.rollback()
        raise


def _check_in(code, operator):
    ticket = Ticket.query.filter_by(code=(code or "").strip()).with_for_update().first()
    if ticket is None:
        raise CheckInError("Biglietto non trovato.", 404)
    event = ticket.event
    if operator.role == Role.ORGANIZER and event.organizer_id != operator.id:
        raise CheckInError("Non puoi gestire gli ingressi di questo evento.", 403)
    if event.status == EventStatus.CANCELLED:
        raise CheckInError("L'evento è stato annullato.", 409)
    if ticket.is_used:
        raise CheckInError(f"Biglietto già usato il {ticket.checked_in_at:%d/%m/%Y alle %H:%M}.", 409)
    ticket.checked_in_at = utcnow()
    ticket.checked_in_by_id = operator.id
    db.session.commit()
    return ticket


def event_stats(event):
    rows = (
        db.session.query(
            TicketType.id, TicketType.name, TicketType.price, TicketType.quantity,
            func.count(Ticket.id), func.count(Ticket.checked_in_at),
        )
        .outerjoin(Ticket, Ticket.ticket_type_id == TicketType.id)
        .filter(TicketType.event_id == event.id)
        .group_by(TicketType.id, TicketType.name, TicketType.price, TicketType.quantity)
        .order_by(TicketType.id)
        .all()
    )
    types = [
        {"id": r[0], "name": r[1], "price": Decimal(r[2]), "quantity": r[3],
         "sold": r[4], "checked_in": r[5]}
        for r in rows
    ]
    revenue = db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(
        Order.event_id == event.id, Order.status == OrderStatus.PAID
    ).scalar()
    sold = sum(t["sold"] for t in types)
    checked_in = sum(t["checked_in"] for t in types)
    return {
        "capacity": event.capacity,
        "sold": sold,
        "checked_in": checked_in,
        "revenue": Decimal(str(revenue)).quantize(CENT),
        "occupancy_percent": round(sold * 100 / event.capacity, 1) if event.capacity else 0,
        "ticket_types": types,
    }
