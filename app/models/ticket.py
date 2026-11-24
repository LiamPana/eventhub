import secrets

from app.extensions import db


def generate_ticket_code():
    return secrets.token_urlsafe(16)


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(
        db.String(64), unique=True, nullable=False, index=True,
        default=generate_ticket_code,
    )
    checked_in_at = db.Column(db.DateTime, nullable=True)

    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    ticket_type_id = db.Column(
        db.Integer, db.ForeignKey("ticket_types.id"), nullable=False, index=True
    )
    checked_in_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    order = db.relationship("Order", back_populates="tickets")
    ticket_type = db.relationship("TicketType", back_populates="tickets")
    checked_in_by = db.relationship("User", foreign_keys=[checked_in_by_id])

    @property
    def is_used(self):
        return self.checked_in_at is not None

    @property
    def event(self):
        return self.ticket_type.event

    def __repr__(self):
        return f"<Ticket {self.code[:6]}…>"