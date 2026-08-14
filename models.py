import uuid

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def gen_uuid():
    """User's primary key. Random UUID4 -- this IS the auditor hash used in
    /dashboard/<id> URLs. Not derivable from anything, only obtainable by
    reading a profile page (or a real leak)."""
    return str(uuid.uuid4())


class Company(db.Model):
    __tablename__ = "company"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    users = db.relationship("User", backref="company", lazy=True)
    reports = db.relationship("Report", backref="company", lazy=True)


class User(db.Model):
    __tablename__ = "user"

    # Primary key IS the auditor hash -- used directly in /dashboard/<id>
    id = db.Column(
        db.String(36),
        primary_key=True,
        default=gen_uuid
    )

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(50),
        nullable=False
    )

    # Display name shown in the /team directory
    name = db.Column(
        db.String(80),
        nullable=False
    )

    role = db.Column(
        db.String(30),
        nullable=False,
        default="visitor"
    )

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id"),
        nullable=False
    )


class Report(db.Model):
    __tablename__ = "report"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id"),
        nullable=False
    )

    report_name = db.Column(
        db.String(100),
        nullable=False
    )

    report_path = db.Column(
        db.String(200),
        nullable=False
    )

    # Hidden reports (like "flag") aren't returned by the normal dropdown
    # listing on the dashboard -- only reachable via the export SQLi.
    hidden = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )