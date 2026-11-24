
from app.extensions import db
from app.utils import utcnow

class OrderStatus:
    PAID = "paid"
    CANCELLED = "cancelled"
   


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=OrderStatus.PAID)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False, index=True)
    discount_code_id = db.Column(db.Integer, db.ForeignKey("discount_codes.id"), nullable=True)

    user = db.relationship("User", backref=db.backref("orders", lazy="dynamic"))
    event = db.relationship("Event", back_populates="orders")
    discount_code = db.relationship("DiscountCode", back_populates="orders")
    tickets = db.relationship(
        "Ticket", back_populates="order",
        cascade="all, delete-orphan", order_by="Ticket.id",
    )
    def __repr__(self):
        return f"<Order {self.id} - {self.status}>"
