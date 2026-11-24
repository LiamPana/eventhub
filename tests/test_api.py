def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_events_list_only_published(client, data):
    body = client.get("/api/events").get_json()
    titles = [e["title"] for e in body["items"]]
    assert titles == ["Rock Night"]
    assert body["total"] == 1


def test_events_search(client, data):
    assert client.get("/api/events?q=lugano").get_json()["total"] == 1
    assert client.get("/api/events?q=nulla").get_json()["total"] == 0


def test_event_detail_structure(client, data):
    body = client.get(f"/api/events/{data['event']}").get_json()
    assert body["tickets_left"] == 10
    assert {t["name"] for t in body["ticket_types"]} == {"Standard", "VIP"}
    assert body["ticket_types"][0]["price"] == "20.00"


def test_draft_detail_is_404_json(client, data):
    resp = client.get(f"/api/events/{data['draft']}")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_stats_permissions(client, data, login):
    url = f"/api/events/{data['event']}/stats"
    assert client.get(url).status_code == 401
    login("part")
    assert client.get(url).status_code == 403
    client.post("/auth/logout")
    login("org2")
    assert client.get(url).status_code == 403
    client.post("/auth/logout")
    login("org")
    assert client.get(url).status_code == 200


def test_stats_values(client, data, login, buy_ticket):
    buy_ticket("part", 2, "standard")
    buy_ticket("part2", 1, "vip")
    login("org")
    body = client.get(f"/api/events/{data['event']}/stats").get_json()
    assert body["sold"] == 3
    assert body["revenue"] == "90.00"
    assert body["checked_in"] == 0


def test_api_checkin(client, data, login, buy_ticket):
    code = buy_ticket("part")[0]
    assert client.post("/api/checkin", json={"code": code}).status_code == 401
    login("part")
    assert client.post("/api/checkin", json={"code": code}).status_code == 403
    client.post("/auth/logout")
    login("staff")
    assert client.post("/api/checkin", data="x").status_code == 415
    assert client.post("/api/checkin", json={}).status_code == 400
    assert client.post("/api/checkin", json={"code": "boh"}).status_code == 404
    ok = client.post("/api/checkin", json={"code": code})
    assert ok.status_code == 200 and ok.get_json()["holder"] == "part"
    assert client.post("/api/checkin", json={"code": code}).status_code == 409


def test_my_tickets(client, data, login, buy_ticket):
    buy_ticket("part", 2)
    login("part")
    items = client.get("/api/me/tickets").get_json()["items"]
    assert len(items) == 2 and items[0]["event"] == "Rock Night"
