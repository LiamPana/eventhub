from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                ValidationError)

from app.models import Role, User


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(3, 64)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(8, 128)])
    confirm = PasswordField(
        "Conferma password",
        validators=[DataRequired(), EqualTo("password", "Le password non coincidono.")],
    )
    # staff e admin non si scelgono in registrazione: li assegna un admin
    role = SelectField(
        "Voglio",
        choices=[(Role.PARTICIPANT, "Partecipare agli eventi"),
                 (Role.ORGANIZER, "Organizzare eventi")],
        default=Role.PARTICIPANT,
    )
    submit = SubmitField("Registrati")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError("Username già in uso.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("Email già registrata.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Resta connesso")
    submit = SubmitField("Accedi")
