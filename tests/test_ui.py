def test_home(client, data):
    html = client.get("/").get_data(as_text=True)
    assert "Benvenuto su EventHub" in html and "Rock Night" in html


def test_events_page_hides_draft(client, data):
    html = client.get("/events/").get_data(as_text=True)
    assert "Rock Night" in html and "Bozza Segreta" not in html


def test_event_detail_shows_ticket_types(client, data):
    html = client.get(f"/events/{data['event']}").get_data(as_text=True)
    assert "Standard" in html and "VIP" in html and "€ 50.00" in html
    assert "Accedi" in html  # anonimo: invito al login


def test_custom_404(client):
    resp = client.get("/pagina-che-non-esiste")
    assert resp.status_code == 404 and "Pagina non trovata" in resp.get_data(as_text=True)


def test_register_and_login_pages(client):
    assert client.get("/auth/register").status_code == 200
    assert client.get("/auth/login").status_code == 200


def test_my_tickets_page_shows_qr(client, data, login, buy_ticket):
    buy_ticket("part")
    login("part")
    html = client.get("/events/my-tickets").get_data(as_text=True)
    assert "qr.png" in html
