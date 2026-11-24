from decimal import Decimal

from app.models import DiscountCode, Order, Ticket
from app.extensions import db


def buy(client, data, **fields):
    form = {f"qty_{data['standard']}": 0, f"qty_{data['vip']}": 0}
    form.update(fields)
    return client.post(f"/events/{data['event']}/buy", data=form, follow_redirects=True)


def test_anonymous_cannot_buy(client, data):
    resp = client.post(f"/events/{data['event']}/buy", data={f"qty_{data['standard']}": 1})
    assert resp.status_code == 302 and "/auth/login" in resp.headers["Location"]


def test_purchase_creates_tickets_and_total(app, client, data, login):
    login("part")
    resp = buy(client, data, **{f"qty_{data['standard']}": 2, f"qty_{data['vip']}": 1})
    assert "Acquisto completato" in resp.get_data(as_text=True)
    with app.app_context():
        order = Order.query.one()
        assert order.total == Decimal("90.00")
        assert Ticket.query.count() == 3
        assert len({t.code for t in Ticket.query.all()}) == 3


def test_ticket_type_sold_out(app, client, data, login):
    login("part")
    resp = buy(client, data, **{f"qty_{data['vip']}": 3})
    assert "insufficienti" in resp.get_data(as_text=True)
    with app.app_context():
        assert Ticket.query.count() == 0


def test_event_capacity_is_enforced(app, client, data, login, buy_ticket):
    buy_ticket("part", 8, "standard")
    buy_ticket("part2", 2, "vip")
    login("part")
    resp = buy(client, data, **{f"qty_{data['standard']}": 1})
    assert "Capienza insufficiente" in resp.get_data(as_text=True) or "insufficienti" in resp.get_data(as_text=True)
    with app.app_context():
        assert Ticket.query.count() == 10


def test_max_tickets_per_order(client, data, login):
    login("part")
    resp = buy(client, data, **{f"qty_{data['standard']}": 11})
    assert "al massimo 10" in resp.get_data(as_text=True)


def test_nothing_selected(client, data, login):
    login("part")
    assert "almeno un biglietto" in buy(client, data).get_data(as_text=True)


def test_discount_applied_and_single_use(app, client, data, login):
    login("part")
    resp = buy(client, data, **{f"qty_{data['standard']}": 1, "discount_code": "save10"})
    assert "Acquisto completato" in resp.get_data(as_text=True)
    with app.app_context():
        order = Order.query.one()
        assert order.total == Decimal("18.00")
        assert order.discount_amount == Decimal("2.00")
        assert DiscountCode.query.filter_by(code="SAVE10").one().used_count == 1
    resp = buy(client, data, **{f"qty_{data['standard']}": 1, "discount_code": "SAVE10"})
    assert "esaurito gli utilizzi" in resp.get_data(as_text=True)
    with app.app_context():
        assert Order.query.count() == 1


def test_expired_and_unknown_discount(client, data, login):
    login("part")
    resp = buy(client, data, **{f"qty_{data['standard']}": 1, "discount_code": "OLD"})
    assert "scaduto" in resp.get_data(as_text=True)
    resp = buy(client, data, **{f"qty_{data['standard']}": 1, "discount_code": "BOH"})
    assert "non valido" in resp.get_data(as_text=True)


def test_cannot_buy_draft_event(client, data, login):
    login("part")
    resp = client.post(f"/events/{data['draft']}/buy", data={})
    assert resp.status_code == 404
