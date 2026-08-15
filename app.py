import os
import sqlite3

from flask import (
    Flask, render_template, request, redirect,
    url_for, send_file, abort, jsonify
)
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required,
    get_jwt_identity, decode_token
)
from models import db, User, Company, Report

from flask_jwt_extended import verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError


app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app.secret_key = "L3M0N_CTF"
app.config["JWT_SECRET_KEY"] = "L3M0N_CTF"
app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
jwt = JWTManager(app)


def force_logout_redirect(error=None):
    resp = redirect(url_for("login", error=error) if error else url_for("login"))
    resp.delete_cookie(app.config["JWT_ACCESS_COOKIE_NAME"])
    return resp


@jwt.expired_token_loader
def handle_expired_token(jwt_header, jwt_payload):
    return force_logout_redirect("Your session has expired. Please log in again.")


@jwt.invalid_token_loader
def handle_invalid_token(reason):
    return force_logout_redirect("Invalid session. Please log in again.")


@jwt.unauthorized_loader
def handle_missing_token(reason):
    return force_logout_redirect("Please log in to continue.")


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
with app.app_context():
    print("===================================")
    print("DATABASE PATH:", DB_PATH)
    print("DATABASE EXISTS BEFORE:", os.path.exists(DB_PATH))

    db.create_all()

    print("DATABASE EXISTS AFTER:", os.path.exists(DB_PATH))
    print("USERS:", User.query.count())
    print("COMPANIES:", Company.query.count())
    print("REPORTS:", Report.query.count())

    if User.query.count() == 0:
        print("SEEDING DATABASE...")
        # ---------------------------------------------------------------
        # Companies
        # ---------------------------------------------------------------
        asterion = Company(name="Asterion Systems")
        bluepeak = Company(name="BluePeak Industries")
        cinderlabs = Company(name="CinderLabs")
        northstar = Company(name="Northstar Logistics")
        redwood = Company(name="Redwood Analytics")
        lemon_co = Company(name="L3M0N_corp")
        auditor_co = Company(name="Auditor Co")  # home company for self-registered visitors

        db.session.add_all([
            asterion,
            bluepeak,
            cinderlabs,
            northstar,
            redwood,
            lemon_co,
            auditor_co,
        ])
        db.session.commit()

        # ---------------------------------------------------------------
        # Users -- id is no longer passed manually; models.py generates a
        # UUID automatically for each User via default=generate_uuid
        # ---------------------------------------------------------------
        asterion_users = [
            User(
                username="jake", password="jake123", name="Jake",
                role="Assistant Auditor", chief="Alex", company_id=asterion.id,
            ),
            User(
                username="sarah", password="sarah123", name="Sarah",
                role="Senior Auditor", chief="Alex", company_id=asterion.id,
            ),
            User(
                username="alex", password="alex123", name="Alex",
                role="Chief Auditor", chief=None, company_id=asterion.id,
            ),
        ]

        bluepeak_users = [
            User(
                username="ryan", password="ryan123", name="Ryan",
                role="Assistant Auditor", chief="Brian", company_id=bluepeak.id,
            ),
            User(
                username="olivia", password="olivia123", name="Olivia",
                role="Senior Auditor", chief="Brian", company_id=bluepeak.id,
            ),
            User(
                username="brian", password="brian123", name="Brian",
                role="Chief Auditor", chief=None, company_id=bluepeak.id,
            ),
        ]

        cinder_users = [
            User(
                username="daniel", password="daniel123", name="Daniel",
                role="Assistant Auditor", chief="Chris", company_id=cinderlabs.id,
            ),
            User(
                username="maya", password="maya123", name="Maya",
                role="Senior Auditor", chief="Chris", company_id=cinderlabs.id,
            ),
            User(
                username="chris", password="chris123", name="Chris",
                role="Chief Auditor", chief=None, company_id=cinderlabs.id,
            ),
        ]

        northstar_users = [
            User(
                username="sam", password="sam123", name="Sam",
                role="Assistant Auditor", chief="David", company_id=northstar.id,
            ),
            User(
                username="laura", password="laura123", name="Laura",
                role="Senior Auditor", chief="David", company_id=northstar.id,
            ),
            User(
                username="david", password="david123", name="David",
                role="Chief Auditor", chief=None, company_id=northstar.id,
            ),
        ]

        redwood_users = [
            User(
                username="lily", password="lily123", name="Lily",
                role="Assistant Auditor", chief="Emma", company_id=redwood.id,
            ),
            User(
                username="noah", password="noah123", name="Noah",
                role="Senior Auditor", chief="Emma", company_id=redwood.id,
            ),
            User(
                username="emma", password="emma123", name="Emma",
                role="Chief Auditor", chief=None, company_id=redwood.id,
            ),
        ]

        # L3M0N Corp
        lemon_users = [
            User(
                username="mia", password="mia123", name="Mia",
                role="Assistant Auditor", chief="John", company_id=lemon_co.id,
            ),
            User(
                username="victor", password="victor123", name="Victor",
                role="Senior Auditor", chief="John", company_id=lemon_co.id,
            ),
            User(
                username="john", password="john123", name="John",
                role="Chief Auditor", chief=None, company_id=lemon_co.id,
            ),
        ]

        all_users = (
            asterion_users
            + bluepeak_users
            + cinder_users
            + northstar_users
            + redwood_users
            + lemon_users
        )

        db.session.add_all(all_users)
        db.session.commit()

        # ---------------------------------------------------------------
        # Reports
        # ---------------------------------------------------------------
        FOLDER_TO_COMPANY = {
            "Asterion_Systems": asterion,
            "BluePeak_Industries": bluepeak,
            "CinderLabs": cinderlabs,
            "Northstar_Logistics": northstar,
            "Redwood_Analytics": redwood,
            "L3M0N_corp": lemon_co,
            "Auditor_Co": auditor_co,
        }

        HIDDEN_NAMES = {"flag.txt"}

        data_dir = os.path.join(BASE_DIR, "data")

        for folder_name, company in FOLDER_TO_COMPANY.items():
            folder_path = os.path.join(data_dir, folder_name)
            print("Checking:", folder_path)

            if not os.path.isdir(folder_path):
                print("Missing data folder:", folder_path)
                continue

            for filename in os.listdir(folder_path):
                if not filename.endswith(".txt"):
                    continue

                file_path = os.path.join(folder_path, filename)

                db.session.add(
                    Report(
                        report_name=filename,
                        report_path=file_path,
                        company_id=company.id,
                        hidden=filename in HIDDEN_NAMES,
                    )
                )

        db.session.commit()

        print("SEEDING COMPLETE")
        print("USERS AFTER SEED:", User.query.count())
        print("COMPANIES AFTER SEED:", Company.query.count())
        print("REPORTS AFTER SEED:", Report.query.count())


# ---------------------------------------------------------------------------
# Root -> always login
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            token = create_access_token(identity=user.id)  # already a UUID string
            resp = redirect(url_for("dashboard", auditor_hash=user.id))
            resp.set_cookie("access_token", token)
            return resp
        return render_template("login.html", error="Invalid username or password.")

    error = request.args.get("error")
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    return force_logout_redirect()


@app.route("/team")
@jwt_required()
def team():
    current_user_id = get_jwt_identity()

    username = request.args.get("username")
    company = request.args.get("company")

    if username or company:
        user = None
        if username:
            username=username.strip().lower()
            user = User.query.filter_by(username=username).filter(User.role != "Visitor").first()
        elif company:
            company=company.strip().lower()
            user = User.query.join(Company).filter(Company.name.ilike(company)).first()

        if not user:
            return render_template(
                "profile.html",
                empty=True,
                query_value="company=" + (username or company),
            )

        return render_template(
            "profile.html",
            name=user.name,
            auditor_hash=user.id,
            company=user.company.name,
            role=user.role,
            chief=user.chief,
            hash=current_user_id,
        )

    auditors = (
        User.query
        .join(Company)
        .filter(Company.name != "L3M0N_corp").filter(User.role != "Visitor")
        .with_entities(User.name, User.username, User.id)
        .order_by(User.name)
        .all()
    )
    return render_template(
        "team.html",
        auditors=[{"name": a.name, "username": a.username, "hash": a.id} for a in auditors],
        hash=current_user_id,
    )

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard/<auditor_hash>")
@jwt_required()
def dashboard(auditor_hash):
    user = User.query.get(auditor_hash)
    if not user:
        abort(404)
    reports = Report.query.filter_by(company_id=user.company_id, hidden=False).all()
    token = request.cookies.get(app.config["JWT_ACCESS_COOKIE_NAME"])
    return render_template(
        "dashboard.html",
        auditor_hash=auditor_hash,
        company=user.company.name,
        reports=reports,
        token=token,
    )
from flask_jwt_extended import decode_token
from flask_jwt_extended.exceptions import JWTDecodeError
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError


@app.route("/dashboard/<auditor_hash>/show", methods=["POST"])
def show_report(auditor_hash):
    token = request.form.get("token")
    if not token:
        return jsonify({
            "error": "Missing 'token' field. This endpoint requires the JWT to be sent explicitly in the request body."
        }), 401

    try:
        decoded = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError, JWTDecodeError):
        return force_logout_redirect("Invalid or expired token. Please log in again.")

    current_user_id = decoded["sub"]
    current_user = User.query.get(current_user_id)
    target_user = User.query.get(auditor_hash)
    if not current_user or not target_user:
        abort(404)

    if current_user.company_id != target_user.company_id:
        return force_logout_redirect("You don't have access to that company's dashboard.")

    report_name = request.form.get("report_name", "")
    report = Report.query.filter_by(
        company_id=target_user.company_id, report_name=report_name, hidden=False
    ).first()
    if not report:
        abort(404)

    with open(report.report_path) as f:
        content = f.read()

    return render_template(
        "report_view.html",
        report_name=report.report_name,
        content=content,
        auditor_hash=auditor_hash,
    )


@app.route("/dashboard/<auditor_hash>/export", methods=["POST"])
@jwt_required()
def export_report(auditor_hash):
    # BUG 1 (broken access control): only checks that the JWT is valid,
    # never that the caller's company matches the dashboard's company.
    target_user = User.query.get(auditor_hash)
    if not target_user:
        abort(404)

    docname = request.form.get("docname", "")

    # BUG 2 (SQL injection): docname spliced directly into the query.
    query = (
        "SELECT id, report_name, report_path FROM report "
        "WHERE company_id = {cid} AND report_name = '{name}'"
    ).format(cid=target_user.company_id, name=docname)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query).fetchall()
    except sqlite3.Error as e:
        conn.close()
        return jsonify({"error": str(e)}), 400
    conn.close()

    if not rows:
        abort(404)

    for row in rows:
        if row["report_name"] == "flag.txt":
            if target_user.role != "Chief Auditor":
                return jsonify({
                    "error": "This report is restricted to the Chief Auditor"
                }), 403

    if len(rows) > 1:
        return jsonify([
            {"report_name": r["report_name"]} for r in rows
        ])

    row = rows[0]
    return send_file(row["report_path"], as_attachment=True,
                      download_name=row["report_name"])


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        if not username or not password or not name:
            return render_template("register.html", error="All fields are required.")

        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="That username is already taken.")

        auditor_co = Company.query.filter_by(name="Auditor Co").first()
        if not auditor_co:
            return render_template("register.html", error="Registration is temporarily unavailable.")

        new_user = User(
            username=username,
            password=password,
            name=name,
            role="Visitor",
            chief=None,
            company_id=auditor_co.id,
        )
        db.session.add(new_user)
        db.session.commit()

        token = create_access_token(identity=new_user.id)
        resp = redirect(url_for("dashboard", auditor_hash=new_user.id))
        resp.set_cookie("access_token", token)
        return resp

    return render_template("register.html", error=None)


if __name__ == "__main__":
    app.run(debug=True)