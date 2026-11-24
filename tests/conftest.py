from datetime import timedelta
from decimal import Decimal

import pytest

from app import create_app
from app.events.services import purchase_tickets
from app.extensions import db
from app.models import (DiscountCode, Event, EventStatus, Role, TicketType,
                        User)
from app.utils import utcnow
from config import TestingConfig

PASSWORD = "password123"


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _user(username, role):
    user = User(username=username, email=f"{username}@test.com", role=role)
    user.set_password(PASSWORD)
    db.session.add(user)
    return user


@pytest.fixture
def data(app):
    """Utenti di ogni ruolo, un evento pubblicato (cap. 10: 8 Standard + 2 VIP), una bozza."""
    with app.app_context():
        organizer = _user("org", Role.ORGANIZER)
        _user("org2", Role.ORGANIZER)
        _user("staff", Role.STAFF)
        _user("admin", Role.ADMIN)
        _user("part", Role.PARTICIPANT)
        _user("part2", Role.PARTICIPANT)
        db.session.flush()

        start = utcnow() + timedelta(days=10)
        event = Event(
            title="Rock Night", description="Concerto rock", location="Lugano",
            start_at=start, end_at=start + timedelta(hours=3), capacity=10,
            status=EventStatus.PUBLISHED, organizer_id=organizer.id,
        )
        draft = Event(
            title="Bozza Segreta", description="", location="Zurigo",
            start_at=start, end_at=start + timedelta(hours=3), capacity=5,
            status=EventStatus.DRAFT, organizer_id=organizer.id,
        )
        db.session.add_all([event, draft])
        db.session.flush()
        std = TicketType(name="Standard", price=Decimal("20.00"), quantity=8, event_id=event.id)
        vip = TicketType(name="VIP", price=Decimal("50.00"), quantity=2, event_id=event.id)
        db.session.add_all([
            std, vip,
            DiscountCode(code="SAVE10", percent=10, max_uses=1, event_id=event.id),
            DiscountCode(code="OLD", percent=50, max_uses=5, event_id=event.id,
                         expires_at=utcnow() - timedelta(days=1)),
        ])
        db.session.commit()
        return {"event": event.id, "draft": draft.id, "standard": std.id, "vip": vip.id}


@pytest.fixture
def login(client):
    def _login(username):
        return client.post(
            "/auth/login",
            data={"email": f"{username}@test.com", "password": PASSWORD},
            follow_redirects=True,
        )
    return _login


@pytest.fixture
def buy_ticket(app, data):
    """Acquista direttamente via servizio; ritorna i codici dei biglietti."""
    def _buy(username="part", qty=1, type_key="standard"):
        with app.app_context():
            user = User.query.filter_by(username=username).one()
            event = db.session.get(Event, data["event"])
            order = purchase_tickets(user, event, {data[type_key]: qty})
            return [t.code for t in order.tickets]
    return _buy
