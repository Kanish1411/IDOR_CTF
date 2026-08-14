import os
import sqlite3

from flask import (
    Flask, render_template, request, redirect,
    url_for, send_file, abort, jsonify
)
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required,
    get_jwt_identity
)

from models import db, User, Company, Report

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
# Seed data (unchanged)
# ---------------------------------------------------------------------------
with app.app_context():
    db.create_all()

    if User.query.count() == 0:
        # ---------------------------------------------------------------
        # Companies
        # ---------------------------------------------------------------
        asterion = Company(name="Asterion Systems")
        bluepeak = Company(name="BluePeak Industries")
        cinderlabs = Company(name="CinderLabs")
        northstar = Company(name="Northstar Logistics")
        redwood = Company(name="Redwood Analytics")
        lemon_co = Company(name="L3M0N_corp")

        db.session.add_all([
            asterion,
            bluepeak,
            cinderlabs,
            northstar,
            redwood,
            lemon_co
        ])
        db.session.commit()

        # ---------------------------------------------------------------
        # Users
        # ---------------------------------------------------------------
        asterion_user = User(
            username="alex",
            password="alex123",
            name="Alex",
            company_id=asterion.id,
        )

        bluepeak_user = User(
            username="brian",
            password="brian123",
            name="Brian",
            company_id=bluepeak.id,
        )

        cinder_user = User(
            username="chris",
            password="chris123",
            name="Chris",
            company_id=cinderlabs.id,
        )

        northstar_user = User(
            username="david",
            password="david123",
            name="David",
            company_id=northstar.id,
        )

        redwood_user = User(
            username="emma",
            password="emma123",
            name="Emma",
            company_id=redwood.id,
        )

        # Main L3M0N auditor
        lemon_user = User(
            username="john",
            password="john123",
            name="John",
            company_id=lemon_co.id,
        )

        db.session.add_all([
            asterion_user,
            bluepeak_user,
            cinder_user,
            northstar_user,
            redwood_user,
            lemon_user
        ])
        db.session.commit()

        # ---------------------------------------------------------------
        # Auto-discover reports from the data/ directory.
        #
        # Folder name -> Company mapping.
        # Every .txt file inside a mapped folder becomes a Report row.
        #
        # flag.txt is hidden from the normal dashboard listing.
        # ---------------------------------------------------------------
        FOLDER_TO_COMPANY = {
            "Asterion_Systems": asterion,
            "BluePeak_Industries": bluepeak,
            "CinderLabs": cinderlabs,
            "Northstar_Logistics": northstar,
            "Redwood_Analytics": redwood,
            "L3M0N_corp": lemon_co,
        }

        HIDDEN_NAMES = {
            "flag.txt"
        }

        data_dir = os.path.join(BASE_DIR, "data")
        for folder_name, company in FOLDER_TO_COMPANY.items():
            folder_path = os.path.join(data_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue

            for filename in sorted(os.listdir(folder_path)):
                file_path = os.path.join(folder_path, filename)
                if not os.path.isfile(file_path):
                    continue
                if not filename.endswith(".txt"):
                    continue

                db.session.add(Report(
                    company_id=company.id,
                    report_name=filename,
                    report_path=file_path,
                    hidden=(filename in HIDDEN_NAMES),
                ))

        db.session.commit()

# ---------------------------------------------------------------------------
# Helper: kill the session and bounce to login
# ---------------------------------------------------------------------------
def force_logout_redirect(error=None):
    resp = redirect(url_for("login"))
    resp.delete_cookie(app.config["JWT_ACCESS_COOKIE_NAME"])
    if error:
        resp = redirect(url_for("login", error=error))
    return resp


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
            token = create_access_token(identity=user.id)
            resp = redirect(url_for("dashboard", auditor_hash=user.id))
            resp.set_cookie("access_token", token)
            return resp
        return render_template("login.html", error="Invalid username or password.")

    # GET: may have arrived here via a redirect carrying an error message
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

    # Profile-lookup mode: a specific auditor was requested
    if username or company:
        user = None
        if username:
            user = User.query.filter_by(username=username).first()
        elif company:
            user = User.query.join(Company).filter(Company.name.ilike(company)).first()

        if not user:
            abort(404)

        # INTENTIONAL: no check that get_jwt_identity() == this user -- any
        # logged-in auditor can look up any other auditor's profile, including
        # their id (the real auditor hash) and company.
        return render_template(
            "profile.html",
            name=user.name,
            auditor_hash=user.id,
            company=user.company.name,
            role=user.role,
            hash=current_user_id,
        )

    auditors = (
        User.query
        .join(Company)
        .filter(Company.name != "L3M0N_corp")
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
    return render_template(
        "dashboard.html",
        auditor_hash=auditor_hash,
        company=user.company.name,
        reports=reports,
    )


@app.route("/dashboard/<auditor_hash>/show", methods=["POST"])
@jwt_required()
def show_report(auditor_hash):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    target_user = User.query.get(auditor_hash)
    if not current_user or not target_user:
        abort(404)

    # FORBIDDEN ACCESS: caller's company doesn't match the dashboard's
    # company -> kill the session and send them back to login, instead of
    # just redirecting while leaving them logged in.
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
    return jsonify({"report_name": report.report_name, "content": content})


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

    if len(rows) > 1:
        return jsonify([
            {"report_name": r["report_name"]} for r in rows
        ])

    row = rows[0]
    return send_file(row["report_path"], as_attachment=True,
                      download_name=row["report_name"])


if __name__ == "__main__":
    app.run(debug=True)