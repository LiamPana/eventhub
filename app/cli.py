import os
from datetime import timedelta
from decimal import Decimal

import click

from app.extensions import db
from app.models import (DiscountCode, Event, EventStatus, Role, TicketType,
                        User)
from app.utils import utcnow


def register_cli(app):
    @app.cli.command("create-admin")
    def create_admin():
        """Crea il primo amministratore (valori da .env o chiesti a terminale)."""
        username = os.environ.get("ADMIN_USERNAME") or click.prompt("Username")
        email = os.environ.get("ADMIN_EMAIL") or click.prompt("Email")
        password = os.environ.get("ADMIN_PASSWORD") or click.prompt(
            "Password", hide_input=True, confirmation_prompt=True
        )
        if User.query.filter((User.email == email) | (User.username == username)).first():
            click.echo("Esiste già un utente con questo username o email.")
            return
        user = User(username=username, email=email.lower(), role=Role.ADMIN)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Amministratore '{username}' creato.")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Carica dati di prova (SOLO per sviluppo): utenti, un evento e uno sconto."""
        if User.query.filter_by(username="organizer").first():
            click.echo("I dati demo esistono già.")
            return
        users = {}
        for name, role in (("organizer", Role.ORGANIZER), ("staff", Role.STAFF),
                           ("participant", Role.PARTICIPANT)):
            u = User(username=name, email=f"{name}@demo.local", role=role)
            u.set_password("Demo1234!")
            db.session.add(u)
            users[name] = u
        db.session.flush()

        start = utcnow() + timedelta(days=14)
        event = Event(
            title="Notte di Jazz", location="Teatro Sociale, Lugano",
            description="Una serata di jazz dal vivo con tre band ospiti.",
            start_at=start, end_at=start + timedelta(hours=4), capacity=100,
            status=EventStatus.PUBLISHED, organizer_id=users["organizer"].id,
        )
        db.session.add(event)
        db.session.flush()
        db.session.add_all([
            TicketType(name="Standard", price=Decimal("20.00"), quantity=80, event_id=event.id),
            TicketType(name="VIP", price=Decimal("50.00"), quantity=20, event_id=event.id),
            DiscountCode(code="JAZZ10", percent=10, max_uses=50, event_id=event.id),
        ])
        db.session.commit()
        click.echo("Dati demo creati. Utenti: organizer, staff, participant (password: Demo1234!).")
