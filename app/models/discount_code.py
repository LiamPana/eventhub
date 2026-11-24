from app.extensions import db


class DiscountCode(db.Model):
    __tablename__ = "discount_codes"
    __table_args__ = (
        db.CheckConstraint("percent BETWEEN 1 AND 100", name="ck_discount_percent"),
    )

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    percent = db.Column(db.Integer, nullable=False)
    max_uses = db.Column(db.Integer, nullable=False)
    used_count = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime, nullable=True)

    event_id = db.Column(
        db.Integer, db.ForeignKey("events.id"), nullable=False, index=True
    )
    event = db.relationship("Event", back_populates="discount_codes")
    orders = db.relationship("Order", back_populates="discount_code")

    def __repr__(self):
        return f"<DiscountCode {self.code} -{self.percent}%>"
