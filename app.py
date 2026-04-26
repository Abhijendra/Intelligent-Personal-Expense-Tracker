import math
import sqlite3
import functools
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email, insert_transactions
from services.excel_parser import parse_file

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-prod"

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
    register("Abhijendra", "abhijendra.work@outlook.com", "abhijendra")


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

    row = conn.execute(
        "SELECT SUM(withdraw_amount) AS total, COUNT(*) AS cnt FROM transactions"
    ).fetchone()
    total_spent       = row["total"] or 0.0
    transaction_count = row["cnt"]   or 0

    top_row = conn.execute(
        "SELECT category FROM transactions "
        "WHERE category != '' AND category IS NOT NULL "
        "GROUP BY category ORDER BY SUM(withdraw_amount) DESC LIMIT 1"
    ).fetchone()
    top_category = top_row["category"] if top_row else "N/A"

    stats = {
        "total_spent":       f"₹{total_spent:,.2f}",
        "transaction_count": transaction_count,
        "top_category":      top_category,
    }

    per_page = 6
    page = max(1, request.args.get("page", 1, type=int))
    total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    total_pages = max(1, math.ceil(total / per_page))
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    txn_rows = conn.execute(
        "SELECT date, txn_note, category, withdraw_amount "
        "FROM transactions ORDER BY date DESC LIMIT ? OFFSET ?",
        (per_page, offset),
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

    pagination = {
        "page":        page,
        "total_pages": total_pages,
        "has_prev":    page > 1,
        "has_next":    page < total_pages,
    }

    cat_rows = conn.execute(
        "SELECT category, SUM(withdraw_amount) AS total "
        "FROM transactions "
        "WHERE category != '' AND category IS NOT NULL "
        "GROUP BY category ORDER BY total DESC LIMIT 5"
    ).fetchall()

    overall = sum(r["total"] for r in cat_rows)
    categories = [
        {
            "name":   r["category"],
            "amount": f"₹{r['total']:,.2f}",
            "pct":    int(r["total"] / overall * 100) if overall else 0,
        }
        for r in cat_rows
    ]

    conn.close()
    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories,
                           pagination=pagination)


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("statement")
    if not file or not file.filename.endswith(".xlsx"):
        flash("Please upload a valid .xlsx file.", "error")
        return redirect(url_for("profile"))
    dest = UPLOAD_DIR / file.filename
    file.save(dest)
    rows = parse_file(dest)
    insert_transactions(rows)
    flash(f"{len(rows)} transactions imported successfully.", "success")
    return redirect(url_for("profile"))


@app.route("/category/add")
@login_required
def add_item_in_category():
    return "Add item"


if __name__ == "__main__":
    app.run(debug=True, port=5003)
    # print(register("Abhijendra", "abhijendra.work@outlook.com", "abhijendra"))
