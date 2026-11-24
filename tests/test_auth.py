from app.extensions import db
from app.models import Role, User


def test_register_creates_user(app, client):
    resp = client.post("/auth/register", data={
        "username": "mario", "email": "Mario@Test.com", "password": "password123",
        "confirm": "password123", "role": "participant",
    })
    assert resp.status_code == 302
    with app.app_context():
        user = User.query.filter_by(username="mario").one()
        assert user.email == "mario@test.com"
        assert user.password_hash != "password123"


def test_register_rejects_duplicate_email(client, data):
    resp = client.post("/auth/register", data={
        "username": "nuovo", "email": "part@test.com", "password": "password123",
        "confirm": "password123", "role": "participant",
    })
    assert resp.status_code == 200
    assert "Email già registrata" in resp.get_data(as_text=True)


def test_cannot_register_as_admin(app, client):
    resp = client.post("/auth/register", data={
        "username": "hacker", "email": "h@test.com", "password": "password123",
        "confirm": "password123", "role": Role.ADMIN,
    })
    assert resp.status_code == 200
    with app.app_context():
        assert User.query.filter_by(username="hacker").first() is None


def test_login_and_logout(client, data, login):
    resp = login("part")
    assert "part (participant)" in resp.get_data(as_text=True)
    resp = client.post("/auth/logout", follow_redirects=True)
    assert "Accedi" in resp.get_data(as_text=True)


def test_wrong_password(client, data):
    resp = client.post("/auth/login", data={"email": "part@test.com", "password": "sbagliata"})
    assert resp.status_code == 401
    assert "Credenziali non valide" in resp.get_data(as_text=True)


def test_protected_page_redirects_to_login(client):
    resp = client.get("/events/my-tickets")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_login_blocks_open_redirect(client, data):
    resp = client.post("/auth/login?next=http://evil.com", data={
        "email": "part@test.com", "password": "password123",
    })
    assert resp.status_code == 302
    assert "evil.com" not in resp.headers["Location"]
