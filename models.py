import uuid

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def generate_uuid():
    return str(uuid.uuid4())


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    users = db.relationship(
        "User",
        back_populates="company"
    )


class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)

    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)

    role = db.Column(db.String(50), nullable=False)
    chief = db.Column(db.String(120), nullable=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id"),
        nullable=False
    )

    company = db.relationship(
        "Company",
        back_populates="users"
    )


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    report_name = db.Column(db.String(200), nullable=False)
    report_path = db.Column(db.String(500), nullable=False)

    hidden = db.Column(db.Boolean, default=False)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id"),
        nullable=False
    )

    company = db.relationship(
        "Company",
        backref="reports"
    )