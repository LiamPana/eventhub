def test_staff_checkin_flow(client, data, login, buy_ticket):
    code = buy_ticket("part")[0]
    login("staff")
    resp = client.post("/events/checkin", data={"code": code})
    assert "Ingresso registrato" in resp.get_data(as_text=True)
    resp = client.post("/events/checkin", data={"code": code})
    assert "già usato" in resp.get_data(as_text=True)


def test_checkin_unknown_code(client, data, login):
    login("staff")
    resp = client.post("/events/checkin", data={"code": "inesistente"})
    assert "non trovato" in resp.get_data(as_text=True)


def test_participant_cannot_checkin(client, data, login):
    login("part")
    assert client.get("/events/checkin").status_code == 403


def test_other_organizer_cannot_checkin(client, data, login, buy_ticket):
    code = buy_ticket("part")[0]
    login("org2")
    resp = client.post("/events/checkin", data={"code": code})
    assert "Non puoi gestire" in resp.get_data(as_text=True)


def test_qr_only_for_owner_or_staff(client, data, login, buy_ticket):
    code = buy_ticket("part")[0]
    login("part")
    resp = client.get(f"/events/tickets/{code}/qr.png")
    assert resp.status_code == 200 and resp.mimetype == "image/png"
    assert resp.data.startswith(b"\x89PNG")
    client.post("/auth/logout")
    login("part2")
    assert client.get(f"/events/tickets/{code}/qr.png").status_code == 403
    client.post("/auth/logout")
    login("staff")
    assert client.get(f"/events/tickets/{code}/qr.png").status_code == 200
