from datetime import timedelta

from app.utils import utcnow
from app.models import DiscountCode, Event, EventStatus, TicketType
from app.extensions import db


def future(days):
    return (utcnow() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M")


def test_organizer_creates_event_as_draft(app, client, data, login):
    login("org")
    resp = client.post("/events/new", data={
        "title": "Workshop Flask", "description": "Corso", "location": "Bellinzona",
        "start_at": future(5), "end_at": future(6), "capacity": 30,
    })
    assert resp.status_code == 302
    with app.app_context():
        event = Event.query.filter_by(title="Workshop Flask").one()
        assert event.status == EventStatus.DRAFT


def test_end_must_follow_start(client, data, login):
    login("org")
    resp = client.post("/events/new", data={
        "title": "X", "location": "Y", "start_at": future(6), "end_at": future(5), "capacity": 5,
    })
    assert resp.status_code == 200
    assert "successiva all&#39;inizio" in resp.get_data(as_text=True)


def test_ticket_types_cannot_exceed_capacity(app, client, data, login):
    login("org")
    resp = client.post(f"/events/{data['event']}/ticket-types/new",
                       data={"name": "Extra", "price": "10", "quantity": 1})
    assert resp.status_code == 200
    assert "Capienza residua" in resp.get_data(as_text=True)


def test_cannot_publish_without_ticket_types(app, client, data, login):
    login("org")
    client.post("/events/new", data={
        "title": "Vuoto", "location": "L", "start_at": future(3), "end_at": future(4), "capacity": 5,
    })
    with app.app_context():
        event_id = Event.query.filter_by(title="Vuoto").one().id
    resp = client.post(f"/events/{event_id}/status", data={"action": "publish"}, follow_redirects=True)
    assert "almeno un tipo di biglietto" in resp.get_data(as_text=True)


def test_publish_and_cancel(app, client, data, login):
    login("org")
    with app.app_context():
        draft = db.session.get(Event, data["draft"])
        db.session.add(TicketType(name="Std", price=5, quantity=5, event_id=draft.id))
        db.session.commit()
    client.post(f"/events/{data['draft']}/status", data={"action": "publish"})
    with app.app_context():
        assert db.session.get(Event, data["draft"]).status == EventStatus.PUBLISHED
    client.post(f"/events/{data['draft']}/status", data={"action": "cancel"})
    with app.app_context():
        assert db.session.get(Event, data["draft"]).status == EventStatus.CANCELLED


def test_cannot_delete_sold_ticket_type(app, client, data, login, buy_ticket):
    buy_ticket("part")
    login("org")
    client.post(f"/events/{data['event']}/ticket-types/{data['standard']}/delete")
    with app.app_context():
        assert db.session.get(TicketType, data["standard"]) is not None


def test_create_discount_code_uppercased(app, client, data, login):
    login("org")
    client.post(f"/events/{data['event']}/discounts/new",
                data={"code": "summer20", "percent": 20, "max_uses": 5})
    with app.app_context():
        assert DiscountCode.query.filter_by(code="SUMMER20").one().percent == 20


def test_report_access(client, data, login, buy_ticket):
    buy_ticket("part", 2)
    login("org")
    resp = client.get(f"/events/{data['event']}/report")
    assert resp.status_code == 200 and "€ 40.00" in resp.get_data(as_text=True)
    client.post("/auth/logout")
    login("org2")
    assert client.get(f"/events/{data['event']}/report").status_code == 403
