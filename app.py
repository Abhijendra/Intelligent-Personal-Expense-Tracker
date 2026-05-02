import sqlite3
import functools
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, insert_transactions
from services.excel_parser import parse_file
from services.categoriser import categorise_transactions, recategorise_all_transactions
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("root")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "dev-secret-change-in-prod" 

UPLOAD_DIR = Path("data/uploads")


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def register(name, email, password):
    try:
        user_id = create_user(name, email, generate_password_hash(password))
    except sqlite3.IntegrityError:
        return "An account with that email already exists."
    return f"success: {user_id} created"

with app.app_context():
    init_db()
    # seed_db()
    dev_username = os.environ.get("DEV_USER_NAME")
    dev_email = os.environ.get("DEV_USER_EMAIL")
    dev_password = os.environ.get("DEV_USER_PASSWORD")
    if dev_email and dev_password:
        register(dev_username or "Dev", dev_email, dev_password)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))
    return render_template("login.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
@login_required
def profile():
    conn = get_db()

    user_row = conn.execute("SELECT * FROM users LIMIT 1").fetchone()
    if not user_row:
        conn.close()
        return redirect(url_for("login"))

    user = {
        "name":     user_row["name"],
        "email":    user_row["email"],
        "joined":   user_row["created_at"],
        "initials": "".join(w[0].upper() for w in user_row["name"].split() if w),
    }

    start_date = request.args.get("start_date", "").strip()
    end_date   = request.args.get("end_date",   "").strip()

    clauses, date_params = [], []
    if start_date:
        clauses.append("date >= ?")
        date_params.append(start_date)
    if end_date:
        clauses.append("date <= ?")
        date_params.append(end_date)
    date_filter = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cat_where = date_filter + (" AND " if date_filter else "WHERE ") + \
                "category != '' AND category IS NOT NULL"

    row = conn.execute(
        f"SELECT SUM(withdraw_amount) AS total, COUNT(*) AS cnt FROM transactions {date_filter}",
        date_params,
    ).fetchone()
    total_spent       = row["total"] or 0.0
    transaction_count = row["cnt"]   or 0

    top_row = conn.execute(
        f"SELECT category FROM transactions {cat_where} "
        "GROUP BY category ORDER BY SUM(withdraw_amount) DESC LIMIT 1",
        date_params,
    ).fetchone()
    top_category = top_row["category"] if top_row else "N/A"

    stats = {
        "total_spent":       f"₹{total_spent:,.2f}",
        "transaction_count": transaction_count,
        "top_category":      top_category,
    }

    txn_rows = conn.execute(
        f"SELECT date, txn_note, category, withdraw_amount "
        f"FROM transactions {date_filter} ORDER BY date DESC",
        date_params,
    ).fetchall()


    transactions = [
        {
            "date":        r["date"],
            "txn_note":    r["txn_note"],
            "category":    r["category"] or "Uncategorised",
            "amount":      f"₹{r['withdraw_amount']:,.2f}",
        }
        for r in txn_rows
    ]

    misc_parts = list(clauses) + ["withdraw_amount > 0"]
    misc_where = "WHERE " + " AND ".join(misc_parts)

    cat_rows = conn.execute(
        f"SELECT COALESCE(category, 'Miscellaneous') AS category, "
        f"SUM(withdraw_amount) AS total "
        f"FROM transactions {misc_where} "
        "GROUP BY COALESCE(category, 'Miscellaneous')",
        date_params,
    ).fetchall()

    misc_row = next((r for r in cat_rows if r["category"] == "Miscellaneous"), None)
    regular  = sorted(
        [r for r in cat_rows if r["category"] != "Miscellaneous"],
        key=lambda r: r["total"], reverse=True,
    )
    ordered = regular + ([misc_row] if misc_row else [])

    overall = sum(r["total"] for r in ordered)
    categories = [
        {
            "name":    r["category"],
            "amount":  f"₹{r['total']:,.2f}",
            "pct":     int(r["total"] / overall * 100) if overall else 0,
            "is_misc": r["category"] == "Miscellaneous",
        }
        for r in ordered
    ]

    conn.close()
    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories,
                           start_date=start_date, end_date=end_date)


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("statement")
    suffix = Path(file.filename).suffix.lower() if file else ""
    if suffix not in (".xls", ".xlsx"):
        flash("Please upload a valid Excel file (.xls or .xlsx).", "error")
        return redirect(url_for("profile"))
    dest = UPLOAD_DIR / file.filename
    file.save(dest)
    try:
        rows = parse_file(dest)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("profile"))
    result = insert_transactions(rows)
    categorise_transactions(result["ids"])
    if result["skipped"]:
        flash(f"{result['inserted']} transactions imported. {result['skipped']} duplicates skipped.", "success")
    else:
        flash(f"{result['inserted']} transactions imported successfully.", "success")
    return redirect(url_for("profile"))


@app.route("/refresh-categories", methods=["POST"])
@login_required
def refresh_categories():
    updated = recategorise_all_transactions()
    return {"status": "ok", "updated": updated}


@app.route("/category/add")
@login_required
def add_item_in_category():
    return "Add item"


if __name__ == "__main__":
    app.run(debug=True, port=5003)
