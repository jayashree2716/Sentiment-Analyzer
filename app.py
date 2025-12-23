from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from datetime import datetime 
import os
import json
import time



app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"

# ---------- DATABASE ----------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="abc123",          
        database="ecommerce"    
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
                cursor.close()
                db.close()
                return redirect(url_for("home"))

            except mysql.connector.Error as e:
                if e.errno == 1062:
                    errors.append("Email already registered.")
                else:
                    errors.append("Database error.")

    return render_template("register.html", errors=errors)

# LOGIN
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

@app.route('/mobiles')
def mobiles():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Fetch mobiles
    cursor.execute("SELECT * FROM products WHERE category='Mobiles' ORDER BY id DESC")
    products = cursor.fetchall()

    cursor.close()
  
    db.close()

    return render_template('mobile.html', products=products)

@app.route("/product/<int:product_id>", methods=["GET", "POST"])
def product_details(product_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Fetch product
    cursor.execute("SELECT * FROM products WHERE id=%s LIMIT 1", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close()
        db.close()
        return "Product not found."

    # Decode JSON images
    try:
        product['images'] = json.loads(product['images'])
    except:
        product['images'] = ["placeholder.png"]

    # Calculate price after discount
    price = float(product.get("price", 0))
    discount = float(product.get("discount", 0))
    price_after = round(price - (price * discount / 100), 2)

    # Handle review submission
    review_err = ""
    if request.method == "POST" and "user_id" in session:
        rating = int(request.form.get("rating", 5))
        comment = request.form.get("comment", "").strip()
        if comment:
            cursor.execute(
                "INSERT INTO reviews (product_id, user_id, rating, comment, created_at) VALUES (%s,%s,%s,%s,%s)",
                (product_id, session["user_id"], rating, comment, datetime.now())
            )
            db.commit()
            return redirect(url_for("product_details", product_id=product_id))
        else:
            review_err = "Comment cannot be empty."

    # Fetch reviews
    cursor.execute("""
        SELECT r.*, u.name 
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.product_id=%s
        ORDER BY r.created_at DESC
    """, (product_id,))
    reviews = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "product_details.html",
        product=product,
        images=product['images'],
        price=price,
        discount=discount,
        price_after=price_after,
        reviews=reviews,
        review_err=review_err
    )



@app.route('/admin_add_product')
def admin_add_product():
     if 'admin_id' not in session:
        flash("Unauthorized access")
        return redirect(url_for('login'))
     return render_template('admin_add_product.html')


@app.route('/save_product', methods=['POST'])
def save_product():
    if 'admin_id' not in session:
        flash("Unauthorized access")
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()

    category = request.form.get('category')
    title = request.form.get('title')
    brand = request.form.get('brand')
    price = float(request.form.get('price', 0))
    discount = float(request.form.get('discount', 0))
    short_desc = request.form.get('short_desc')
    long_desc = request.form.get('long_desc')
    specifications = request.form.get('specifications')

    final_price = price - ((price * discount) / 100)

    # Handle uploaded images
    uploaded_files = []
    images = request.files.getlist('images')
    for f in images:
        if f.filename:
            filename = f"{int(time.time())}_{f.filename}"
            filepath = os.path.join('static/images', filename)
            f.save(filepath)
            uploaded_files.append(filename)

    image_json = json.dumps(uploaded_files)

    cursor.execute("""
        INSERT INTO products 
        (category, title, brand, price, discount, final_price, short_desc, long_desc, specifications, images)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (category, title, brand, price, discount, final_price, short_desc, long_desc, specifications, image_json))

    db.commit()
    cursor.close()
    db.close()
    flash("Product added successfully!")
    return redirect(url_for('admin_add_product'))

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()

    user_id = session['user_id']
    username = session['user_name']
    product_id = int(request.form.get('product_id', 0))
    comment = request.form.get('comment', '').strip()

    if not comment:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for('product_details', id=product_id))

    

    sql = "INSERT INTO comments (product_id, user_id, username, comment) VALUES (%s, %s, %s, %s)"
    cursor.execute(sql, (product_id, user_id, username, comment,datetime.now()))
    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for('product_details', id=product_id))


if __name__ == "__main__":
    app.run(debug=True ,port=5001)
