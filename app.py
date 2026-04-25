import sqlite3
import functools
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-prod"


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


with app.app_context():
    init_db()
    seed_db()


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


# @app.route("/register", methods=["GET", "POST"])
# def register():
#     if session.get("user_id"):
#         return redirect(url_for("landing"))
#     if request.method == "POST":
#         name = request.form["name"]
#         email = request.form["email"]
#         password = request.form["password"]
#         try:
#             user_id = create_user(name, email, generate_password_hash(password))
#         except sqlite3.IntegrityError:
#             return render_template("register.html", error="An account with that email already exists.")
#         session["user_id"] = user_id
#         session["user_name"] = name
#         return redirect(url_for("landing"))
#     return render_template("register.html")


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
    user = {
        "name": "Alex Morgan",
        "email": "alex@example.com",
        "joined": "January 2024",
        "initials": "AM",
    }
    stats = {
        "total_spent": "Rs. 1,284.50",
        "transaction_count": 18,
        "top_category": "Groceries",
    }
    transactions = [
        {"date": "24 Apr 2025", "description": "Tesco Metro",   "category": "Groceries",     "amount": "Rs. 42.30"},
        {"date": "23 Apr 2025", "description": "Netflix",        "category": "Subscriptions", "amount": "Rs. 17.99"},
        {"date": "22 Apr 2025", "description": "TfL Top-up",    "category": "Transport",     "amount": "Rs. 20.00"},
        {"date": "20 Apr 2025", "description": "Pret a Manger", "category": "Eating Out",    "amount": "Rs. 8.75"},
        {"date": "18 Apr 2025", "description": "Amazon Prime",  "category": "Subscriptions", "amount": "Rs. 8.99"},
    ]
    categories = [
        {"name": "Groceries",     "amount": "Rs. 480.20", "pct": 74, "bar_class": "mock-bar"},
        {"name": "Eating Out",    "amount": "Rs. 230.00", "pct": 56, "bar_class": "mock-bar-2"},
        {"name": "Transport",     "amount": "Rs. 185.50", "pct": 44, "bar_class": "mock-bar-3"},
        {"name": "Subscriptions", "amount": "Rs. 388.80", "pct": 60, "bar_class": "mock-bar-4"},
    ]
    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories)


@app.route("/expenses/add")
@login_required
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
@login_required
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
@login_required
def delete_expense(id):
    return "Delete expense — coming in Step 9"

def register(name, email, password):
    try:
        user_id = create_user(name, email, generate_password_hash(password))
    except sqlite3.IntegrityError:
        return "An account with that email already exists."
    return f"success: {user_id} created"

if __name__ == "__main__":
    app.run(debug=True, port=5003)
    # print(register("Abhijendra", "abhijendra.work@outlook.com", "abhijendra"))
