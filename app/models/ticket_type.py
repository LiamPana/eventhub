from sqlalchemy import func

from app.extensions import db


class TicketType(db.Model):
    __tablename__ = "ticket_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    event_id = db.Column(
        db.Integer, db.ForeignKey("events.id"), nullable=False, index=True
    )
    event = db.relationship("Event",back_populates="ticket_types" )
    tickets = db.relationship("Ticket",back_populates="ticket_type")
    @property
    def sold(self):
        from app.models.ticket import Ticket
        return (
            db.session.query(func.count(Ticket.id))
            .filter(Ticket.ticket_type_id == self.id)
            .scalar()
        )

    @property
    def available(self):
        return max(self.quantity - self.sold, 0)
    
    def __repr__(self):
        return f"<TicketType {self.name} - {self.price}>"
