from app.extensions import db
from app.models import User


def test_anonymous_cannot_create_event(client):
    assert client.get("/events/new").status_code == 302


def test_participant_forbidden_organizer_allowed(client, data, login):
    login("part")
    assert client.get("/events/new").status_code == 403
    client.post("/auth/logout")
    login("org")
    assert client.get("/events/new").status_code == 200


def test_only_owner_can_edit_event(client, data, login):
    login("org2")
    assert client.get(f"/events/{data['event']}/edit").status_code == 403
    client.post("/auth/logout")
    login("org")
    assert client.get(f"/events/{data['event']}/edit").status_code == 200


def test_admin_can_edit_any_event(client, data, login):
    login("admin")
    assert client.get(f"/events/{data['event']}/edit").status_code == 200


def test_admin_pages_restricted(client, data, login):
    login("org")
    assert client.get("/admin/users").status_code == 403
    client.post("/auth/logout")
    login("admin")
    assert client.get("/admin/users").status_code == 200


def test_admin_changes_role(app, client, data, login):
    login("admin")
    with app.app_context():
        part_id = User.query.filter_by(username="part").one().id
    resp = client.post(f"/admin/users/{part_id}/role", data={"role": "staff"})
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(User, part_id).role == "staff"


def test_admin_cannot_change_own_role(app, client, data, login):
    login("admin")
    with app.app_context():
        admin_id = User.query.filter_by(username="admin").one().id
    client.post(f"/admin/users/{admin_id}/role", data={"role": "participant"})
    with app.app_context():
        assert db.session.get(User, admin_id).role == "admin"


def test_draft_hidden_from_public(client, data, login):
    assert client.get(f"/events/{data['draft']}").status_code == 404
    login("org")
    assert client.get(f"/events/{data['draft']}").status_code == 200
