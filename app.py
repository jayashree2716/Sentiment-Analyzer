from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"

# ---------- DATABASE ----------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",          # change if needed
        database="shop_db"    # your database name
    )

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    errors = []

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        # validations
        if not name or not email or not password:
            errors.append("All fields required.")
        if "@" not in email:
            errors.append("Invalid email.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if len(password) < 6:
            errors.append("Password at least 6 chars.")

        if not errors:
            hashed = generate_password_hash(password)

            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                    (name, email, hashed)
                )
                db.commit()

                # auto login
                session["user_id"] = cursor.lastrowid
                session["user_name"] = name

                db.close()
                return redirect(url_for("home"))

            except mysql.connector.Error as e:
                if e.errno == 1062:
                    errors.append("Email already registered.")
                else:
                    errors.append("Database error.")

    return render_template("register.html", errors=errors)

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    errors = []

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            errors.append("Enter email & password.")

        if not errors:
            db = get_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, name, password_hash FROM users WHERE email=%s LIMIT 1",
                (email,)
            )
            user = cursor.fetchone()
            db.close()

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                return redirect(url_for("home"))
            else:
                errors.append("Wrong credentials.")

    return render_template("login.html", errors=errors)

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))




if __name__ == "__main__":
    app.run(debug=True ,port=5001)
