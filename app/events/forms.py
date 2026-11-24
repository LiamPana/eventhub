from flask_wtf import FlaskForm
from wtforms import (DateTimeLocalField, DecimalField, IntegerField,
                     StringField, SubmitField, TextAreaField)
from wtforms.validators import (DataRequired, Length, NumberRange, Optional,
                                ValidationError)

DT_FORMAT = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]


class EventForm(FlaskForm):
    title = StringField("Titolo", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Descrizione", validators=[Length(max=5000)])
    location = StringField("Luogo", validators=[DataRequired(), Length(max=200)])
    start_at = DateTimeLocalField("Inizio", format=DT_FORMAT, validators=[DataRequired()])
    end_at = DateTimeLocalField("Fine", format=DT_FORMAT, validators=[DataRequired()])
    capacity = IntegerField("Capienza totale", validators=[DataRequired(), NumberRange(1, 100000)])
    submit = SubmitField("Salva")

    def validate_end_at(self, field):
        if self.start_at.data and field.data and field.data <= self.start_at.data:
            raise ValidationError("La fine deve essere successiva all'inizio.")


class TicketTypeForm(FlaskForm):
    name = StringField("Nome (es. Standard, VIP)", validators=[DataRequired(), Length(max=80)])
    price = DecimalField("Prezzo (€)", places=2, validators=[NumberRange(min=0, max=100000)])
    quantity = IntegerField("Quantità disponibile", validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField("Aggiungi")


def _upper(value):
    return value.strip().upper() if value else value


class DiscountForm(FlaskForm):
    code = StringField("Codice", validators=[DataRequired(), Length(3, 32)], filters=[_upper])
    percent = IntegerField("Sconto (%)", validators=[DataRequired(), NumberRange(1, 100)])
    max_uses = IntegerField("Utilizzi massimi", validators=[DataRequired(), NumberRange(min=1)])
    expires_at = DateTimeLocalField("Scadenza (facoltativa)", format=DT_FORMAT, validators=[Optional()])
    submit = SubmitField("Crea codice")


class CheckInForm(FlaskForm):
    code = StringField("Codice biglietto", validators=[DataRequired(), Length(max=64)])
    submit = SubmitField("Verifica e registra ingresso")
