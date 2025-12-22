from flask import (
    Flask, render_template, request, abort,
    redirect, url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from datetime import timedelta
from functools import wraps
from pathlib import Path
import sqlite3

app = Flask(__name__)

# Flask session configuration
app.secret_key = "change-me-to-something-secret"
app.permanent_session_lifetime = timedelta(days=30)

# Resolve the SQLite database path relative to this file
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dormcart.db"

# Category data used for the Categories page + category routing
CATEGORIES = [
    {"slug": "dorm-and-room", "name": "Dorm & Room", "img": "/static/uploads/products/p1.png"},
    {"slug": "electronics",   "name": "Electronics", "img": "/static/uploads/products/p2.png"},
    {"slug": "books",         "name": "Books",       "img": "/static/uploads/products/p3.png"},
    {"slug": "clothing",      "name": "Clothing",    "img": "/static/uploads/products/p4.png"},
    {"slug": "kitchen",       "name": "Kitchen",     "img": "/static/uploads/products/p5.png"},
    {"slug": "transport",     "name": "Transport",   "img": "/static/uploads/products/p6.png"},
]

# Convenience lookup if needed later
CATEGORY_BY_SLUG = {c["slug"]: c for c in CATEGORIES}

# Maps URL slugs to the display names stored in the database
CATEGORY_MAP = {
    "dorm-and-room": "Dorm & Room",
    "electronics": "Electronics",
    "books": "Books",
    "clothing": "Clothing",
    "kitchen": "Kitchen",
    "transport": "Transport",
    "hobbies": "Hobbies",
}

def get_db():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    # Enables dict-like access in templates: row["title"] instead of row[0]
    conn.row_factory = sqlite3.Row
    return conn

# --------------------- Password Reset Helpers ---------------------

def get_serializer():
    """Create a serializer used to sign password reset tokens."""
    return URLSafeTimedSerializer(app.secret_key)

def generate_reset_token(user_id: int) -> str:
    """Create a signed token containing the user_id."""
    s = get_serializer()
    return s.dumps({"user_id": user_id}, salt="password-reset")

def verify_reset_token(token: str, max_age_seconds: int = 3600) -> int | None:
    """Return user_id if token is valid and not expired; otherwise None."""
    s = get_serializer()
    try:
        data = s.loads(token, salt="password-reset", max_age=max_age_seconds)
        return int(data["user_id"])
    except (SignatureExpired, BadSignature, KeyError, ValueError, TypeError):
        return None

# --------------------- Auth Helper ---------------------

def login_required(f):
    """Require a logged-in user for protected routes."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_user():
    """Expose current_user_id to all templates."""
    return {"current_user_id": session.get("user_id")}

# --------------------- Public Routes ---------------------

@app.route("/")
def landing():
    return render_template("landing.html", title="Landing")

@app.route("/about")
def about():
    return render_template("about.html", title="About")

@app.route("/contact_us")
def contact():
    return render_template("contact.html", title="Contact Us")

@app.route("/faq")
def faq():
    return render_template("faq.html", title="FAQs")

# --------------------- Signup/Login ---------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name  = request.form.get("last_name", "").strip()
        email      = request.form.get("email", "").strip().lower()
        password   = request.form.get("password")
        conpassword = request.form.get("conpassword")

        if not first_name or not last_name or not email or not password or not conpassword:
            return render_template("signup.html", title="Sign Up", error="Please fill out all fields.")

        if password != conpassword:
            return render_template("signup.html", title="Sign Up", error="Password and Confirm Password need to be the same!")

        # Store a password hash (never store raw passwords)
        hash_ = generate_password_hash(password)

        # Build a display name for the profile header
        display_name = f"{first_name} {last_name}".strip()

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO users (email, hash, first_name, last_name, display_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email, hash_, first_name, last_name, display_name)
            )
            conn.commit()
            user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("signup.html", title="Sign Up", error="An account with that email already exists.")

        conn.close()

        # Login immediately after signup
        session["user_id"] = user_id
        return redirect(url_for("homepage"))

    return render_template("signup.html", title="Sign Up")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember")

        if not email or not password:
            return render_template("login.html", title="Login", error="Please fill out all fields.")

        conn = get_db()
        cur = conn.cursor()
        row = cur.execute(
            "SELECT id, hash FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if row is None or not check_password_hash(row["hash"], password):
            return render_template("login.html", title="Login", error="Invalid email or password.")

        session["user_id"] = row["id"]
        # If "Remember me" is checked, cookie persists longer (based on app.permanent_session_lifetime)
        session.permanent = bool(remember)

        return redirect(url_for("homepage"))

    return render_template("login.html", title="Login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            flash("Please enter your email.", "error")
            return redirect(url_for("forgot_password"))

        conn = get_db()
        cur = conn.cursor()
        user = cur.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        # SECURITY: Always return the same message whether the email exists or not
        # so attackers cannot use this endpoint to confirm accounts.
        if user:
            token = generate_reset_token(user["id"])
            reset_link = url_for("reset_password", token=token, _external=True)

            # Demo-only: reset link is printed to terminal instead of emailing it.
            # (ChatGPT helped during development to debug token verification flow and redirect handling.)
            print("\n==== PASSWORD RESET LINK ====")
            print(reset_link)
            print("==== END RESET LINK ====\n")

        flash("If that email exists, you'll receive a reset link shortly.", "info")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user_id = verify_reset_token(token, max_age_seconds=3600)
    if not user_id:
        flash("That reset link is invalid or has expired. Try again.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not password or not confirmation:
            flash("Please fill out all fields.", "error")
            return redirect(url_for("reset_password", token=token))

        if password != confirmation:
            flash("Passwords do not match.", "error")
            return redirect(url_for("reset_password", token=token))

        hashed = generate_password_hash(password)

        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE users SET hash = ? WHERE id = ?", (hashed, user_id))
        conn.commit()
        conn.close()

        flash("Password updated. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")

# --------------------- Protected Routes ---------------------

@app.route("/home")
@login_required
def homepage():
    q = (request.args.get("q") or "").strip()

    conn = get_db()
    cur = conn.cursor()

    # Main query returns products not sold yet, including a "main_image" subquery.
    # "main_image" is computed using a correlated subquery so the homepage can show
    # one thumbnail without needing an extra query per product.
    #
    # (ChatGPT helped while debugging early SQL versions here, especially around
    # building the dynamic WHERE clause + parameters and making sure the query
    # still returned rows correctly when q is empty.)
    sql = """
        SELECT
            p.id,
            p.title,
            p.description,
            p.price,
            p.condition,
            p.category,
            (
                SELECT image_url
                FROM product_images pi
                WHERE pi.product_id = p.id
                ORDER BY pi.sort_order ASC, pi.id ASC
                LIMIT 1
            ) AS main_image
        FROM products p
        WHERE p.is_sold = 0
    """
    params = []

    # If the user searched, extend the WHERE clause with LIKE filters
    if q:
        sql += """
            AND (
                p.title LIKE ?
                OR p.description LIKE ?
                OR p.category LIKE ?
            )
        """
        like = f"%{q}%"
        params += [like, like, like]

    sql += """
        ORDER BY p.created_at DESC, p.id DESC
        LIMIT 60;
    """

    products = cur.execute(sql, params).fetchall()
    conn.close()

    return render_template("homepage.html", title="Home", products=products, q=q)

@app.route("/product/<int:product_id>")
@login_required
def product_detail(product_id):
    conn = get_db()
    cur = conn.cursor()

    product = cur.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if not product:
        conn.close()
        abort(404)

    images = cur.execute(
        """
        SELECT image_url
        FROM product_images
        WHERE product_id = ?
        ORDER BY sort_order, id
        """,
        (product_id,)
    ).fetchall()

    conn.close()
    return render_template("product_detail.html", title="Product", product=product, images=images)

@app.route("/categories")
@login_required
def categories():
    return render_template("categories.html", title="Categories", categories=CATEGORIES)

@app.route("/category/<slug>")
@login_required
def category_page(slug):
    category_name = CATEGORY_MAP.get(slug)
    if not category_name:
        abort(404)

    conn = get_db()
    cur = conn.cursor()

    products = cur.execute("""
        SELECT
            p.id,
            p.title,
            p.description,
            p.price,
            p.condition,
            p.color,
            p.category,
            (
                SELECT image_url
                FROM product_images
                WHERE product_id = p.id
                ORDER BY sort_order, id
                LIMIT 1
            ) AS main_image
        FROM products p
        WHERE p.is_sold = 0
          AND p.category = ?
        ORDER BY p.created_at DESC, p.id DESC
    """, (category_name,)).fetchall()

    conn.close()

    return render_template(
        "category_products.html",
        title=category_name,
        products=products,
        section_title=category_name
    )

@app.post("/cart/add/<int:product_id>")
@login_required
def cart_add(product_id):
    user_id = session["user_id"]
    conn = get_db()
    cur = conn.cursor()

    # Validate product existence and availability
    prod = cur.execute(
        "SELECT is_sold FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if not prod:
        conn.close()
        abort(404)

    if prod["is_sold"]:
        conn.close()
        flash("That item is no longer available.", "error")
        return redirect(request.referrer or url_for("homepage"))

    # Enforce "unique item" cart logic: each product can only appear once per user
    existed = cur.execute("""
        SELECT 1
        FROM cart_items
        WHERE user_id = ? AND product_id = ?
    """, (user_id, product_id)).fetchone()

    if existed:
        flash("Already in cart.", "info")
    else:
        cur.execute("""
            INSERT INTO cart_items (user_id, product_id, quantity)
            VALUES (?, ?, 1)
        """, (user_id, product_id))
        conn.commit()
        flash("Added to cart!", "success")

    conn.close()
    return redirect(request.referrer or url_for("homepage"))

@app.get("/cart")
@login_required
def cart():
    user_id = session["user_id"]
    conn = get_db()
    cur = conn.cursor()

    items = cur.execute("""
        SELECT
            p.id, p.title, p.price, p.condition, p.color, p.category,
            ci.quantity,
            (
                SELECT image_url
                FROM product_images
                WHERE product_id = p.id
                ORDER BY sort_order, id
                LIMIT 1
            ) AS main_image
        FROM cart_items ci
        JOIN products p ON p.id = ci.product_id
        WHERE ci.user_id = ?
        ORDER BY ci.created_at DESC
    """, (user_id,)).fetchall()

    subtotal = sum(row["price"] * row["quantity"] for row in items)
    fee = min(9.99, subtotal * 0.05) if items else 0
    total = subtotal + fee
    items_count = sum(row["quantity"] for row in items)

    conn.close()

    return render_template(
        "cart.html",
        title="Your Cart",
        items=items,
        total=total,
        subtotal=subtotal,
        fee=fee,
        items_count=items_count
    )

@app.post("/cart/incr/<int:product_id>")
@login_required
def cart_incr(product_id):
    # For this demo, cart quantities are disabled to keep "unique item" behavior simple
    flash("Quantity increases are disabled for unique items.", "info")
    return redirect(url_for("cart"))

@app.post("/cart/decr/<int:product_id>")
@login_required
def cart_decr(product_id):
    user_id = session["user_id"]
    conn = get_db()
    cur = conn.cursor()

    # Removing one item removes it entirely in the demo
    cur.execute("""
        DELETE FROM cart_items
        WHERE user_id = ? AND product_id = ?
    """, (user_id, product_id))

    conn.commit()
    conn.close()

    flash("Removed from cart.", "success")
    return redirect(url_for("cart"))

@app.post("/cart/remove/<int:product_id>")
@login_required
def cart_remove(product_id):
    user_id = session["user_id"]
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM cart_items
        WHERE user_id = ? AND product_id = ?
    """, (user_id, product_id))

    conn.commit()
    conn.close()

    flash("Removed from cart.", "success")
    return redirect(url_for("cart"))

@app.post("/checkout")
@login_required
def checkout():
    flash("Checkout is unavailable in this demo.", "info")
    return redirect(url_for("cart"))

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        flash("This feature is not available in this demo.", "info")
        return redirect(url_for("sell"))
    return render_template("sell.html", title="Sell an Item")

@app.route("/best_deals")
@login_required
def best_deals():
    conn = get_db()
    cur = conn.cursor()

    base_query = """
        SELECT
            p.id,
            p.title,
            p.price,
            p.condition,
            p.color,
            p.category,
            (
                SELECT image_url
                FROM product_images pi
                WHERE pi.product_id = p.id
                ORDER BY pi.sort_order, pi.id
                LIMIT 1
            ) AS main_image
        FROM products p
        WHERE p.is_sold = 0
    """

    under_5 = cur.execute(
        base_query + " AND p.price < 5 ORDER BY p.price ASC LIMIT 6"
    ).fetchall()

    under_10 = cur.execute(
        base_query + " AND p.price >= 5 AND p.price < 10 ORDER BY p.price ASC LIMIT 6"
    ).fetchall()

    under_25 = cur.execute(
        base_query + " AND p.price >= 10 AND p.price < 25 ORDER BY p.price ASC LIMIT 6"
    ).fetchall()

    conn.close()

    return render_template(
        "best_deals.html",
        title="Best Deals",
        under_5=under_5,
        under_10=under_10,
        under_25=under_25
    )

@app.get("/profile")
@login_required
def profile():
    user_id = session["user_id"]
    conn = get_db()
    cur = conn.cursor()

    user = cur.execute("""
        SELECT id, email, first_name, last_name, display_name, created_at
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    if not user:
        conn.close()
        abort(404)

    stats = cur.execute("""
        SELECT
            COUNT(*) AS total_listings,
            SUM(CASE WHEN is_sold = 0 THEN 1 ELSE 0 END) AS active_listings,
            SUM(CASE WHEN is_sold = 1 THEN 1 ELSE 0 END) AS sold_listings
        FROM products
        WHERE seller_id = ?
    """, (user_id,)).fetchone()

    rating_stats = cur.execute("""
        SELECT
            COALESCE(ROUND(AVG(rating), 1), 0) AS avg_rating,
            COUNT(*) AS rating_count
        FROM seller_ratings
        WHERE seller_id = ?
    """, (user_id,)).fetchone()

    recent_products = cur.execute("""
        SELECT
            p.id, p.title, p.price, p.is_sold, p.created_at,
            (SELECT image_url
             FROM product_images pi
             WHERE pi.product_id = p.id
             ORDER BY pi.sort_order, pi.id
             LIMIT 1) AS main_image
        FROM products p
        WHERE p.seller_id = ?
        ORDER BY p.created_at DESC, p.id DESC
        LIMIT 6
    """, (user_id,)).fetchall()

    conn.close()

    # Fallbacks ensure the profile always displays something readable
    display_name = (
        user["display_name"]
        or f"{(user['first_name'] or '').strip()} {(user['last_name'] or '').strip()}".strip()
        or user["email"]
    )

    return render_template(
        "profile.html",
        title="Profile",
        user=user,
        display_name=display_name,
        stats=stats,
        rating_stats=rating_stats,
        recent_products=recent_products
    )

if __name__ == "__main__":
    app.run(debug=True)