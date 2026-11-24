from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db
from app.utils import utcnow


class EventStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    location = db.Column(db.String(200), nullable=False)
    start_at = db.Column(db.DateTime, nullable=False, index=True)
    end_at = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=EventStatus.DRAFT)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    organizer_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    organizer = db.relationship("User", back_populates="events")
    ticket_types = db.relationship(
        "TicketType", back_populates="event", cascade="all, delete-orphan"
    )
    discount_codes = db.relationship(
        "DiscountCode", back_populates="event", cascade="all, delete-orphan"
    )
    orders = db.relationship("Order", back_populates="event")

    @property
    def tickets_sold(self):
        from app.models.ticket import Ticket
        from app.models.ticket_type import TicketType
        return (
            db.session.query(func.count(Ticket.id))
            .join(TicketType, Ticket.ticket_type_id == TicketType.id)
            .filter(TicketType.event_id == self.id)
            .scalar()
        )

    @property
    def tickets_left(self):
        return max(self.capacity - self.tickets_sold, 0)

    @property
    def allocated_quantity(self):
        """Somma delle quantità dei tipi di biglietto già definiti."""
        return sum(tt.quantity for tt in self.ticket_types)

    @property
    def is_over(self):
        return self.end_at < utcnow()

    def __repr__(self):
        return f"<Event {self.title}>"