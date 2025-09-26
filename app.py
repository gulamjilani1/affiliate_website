import os
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
)
from dotenv import load_dotenv
from models import db, User, Product, Click
from utils import allowed_file, save_image
from sqlalchemy import func
from datetime import datetime, timedelta

# Load .env
load_dotenv()

# Config
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///affiliate.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join("static", "images")
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

# Security best practices
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False  # local test, set True in production
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_app(app)

# DB init & default admin
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")
        admin.set_password(admin_password)   # ✅ यहीं set_password() use करना है
        db.session.add(admin)
        db.session.commit()
        print(f"Created default admin with username=admin and password={admin_password}")

# ---------- Routes ----------

# Change password (only for logged-in admin)
@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == 'POST':
        new_password = request.form['new_password']
        user = User.query.filter_by(username=session.get("username")).first()
        if user:
            user.set_password(new_password)   # ✅ यहाँ भी set_password() use करना है
            db.session.commit()
            flash("Password updated successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("User not found!", "danger")

    return '''
        <form method="post">
            <label>New Password:</label><br>
            <input type="password" name="new_password"><br><br>
            <input type="submit" value="Change Password">
        </form>
    '''

@app.route("/")
def home():
    products = Product.query.order_by(Product.created_at.desc()).limit(6).all()
    return render_template("home.html", products=products)

@app.route("/products")
def products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if category:
        query = query.filter_by(category=category)
    items = query.order_by(Product.created_at.desc()).all()
    categories = sorted({p.category for p in Product.query.all() if p.category})
    return render_template("products.html", products=items, categories=categories)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    p = Product.query.get_or_404(product_id)
    return render_template("product_details.html", product=p)

@app.route("/track/<int:product_id>")
def track(product_id):
    p = Product.query.get_or_404(product_id)
    click = Click(product_id=p.id)
    db.session.add(click)
    db.session.commit()
    return redirect(p.link)

# Authentication
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form["username"]).first()
        if u and u.check_password(request.form["password"]):
            session["username"] = u.username
            session["role"] = u.role
            flash("Logged in", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("home"))

# Dashboard & Admin
def admin_required():
    return session.get("role") == "admin"

@app.route("/dashboard")
def dashboard():
    if not admin_required():
        return redirect(url_for("login"))
    products = Product.query.order_by(Product.created_at.desc()).all()
    categories = sorted({p.category for p in products if p.category})
    return render_template("dashboard.html", products=products, categories=categories)

@app.route("/product/add", methods=["GET", "POST"])
@app.route("/product/edit/<int:product_id>", methods=["GET", "POST"])
def add_edit_product(product_id=None):
    if not admin_required():
        return redirect(url_for("login"))
    product = Product.query.get(product_id) if product_id else None
    if request.method == "POST":
        name = request.form["name"]
        price = float(request.form.get("price") or 0)
        category = request.form.get("category")
        link = request.form["link"]
        description = request.form.get("description")
        sku = request.form.get("sku")
        source = request.form.get("source")
        availability = request.form.get("availability")
        filename = None
        img = request.files.get("image")
        img_url = request.form.get("image_url")
        if img and img.filename and allowed_file(img.filename):
            filename = save_image(img)
        elif img_url:
            filename = img_url
        if product:
            product.name = name
            product.price = price
            product.category = category
            product.link = link
            product.description = description
            product.sku = sku
            product.source = source
            product.availability = availability
            if filename:
                product.image = filename
        else:
            product = Product(
                name=name, price=price, category=category, link=link,
                description=description, sku=sku, source=source,
                availability=availability, image=filename
            )
            db.session.add(product)
        db.session.commit()
        flash("Product saved", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_edit_product.html", product=product, action=("Edit" if product else "Add"))

@app.route("/product/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if not admin_required():
        return redirect(url_for("login"))
    p = Product.query.get_or_404(product_id)
    db.session.delete(p)
    db.session.commit()
    flash("Deleted", "info")
    return redirect(url_for("dashboard"))

# CSV import
@app.route("/import", methods=["GET", "POST"])
def import_products():
    if not admin_required():
        return redirect(url_for("login"))
    errors = []
    success = None
    if request.method == "POST":
        f = request.files.get("csv")
        if not f:
            flash("No file uploaded", "danger")
            return redirect(url_for("import_products"))
        import csv, io
        try:
            text = io.TextIOWrapper(f, encoding="utf-8")
            reader = csv.DictReader(text)
            for i, row in enumerate(reader, start=1):
                try:
                    p = Product(
                        name=row.get("name") or f"row-{i}",
                        price=float(row.get("price") or 0),
                        category=row.get("category"),
                        link=row.get("link") or "#",
                        description=row.get("description"),
                        image=row.get("image_url"),
                        sku=row.get("sku"),
                        source=row.get("source"),
                        availability=row.get("availability")
                    )
                    db.session.add(p)
                except Exception as e:
                    errors.append(f"Row {i}: {e}")
            if errors:
                db.session.rollback()
                flash("Some rows failed to import", "warning")
            else:
                db.session.commit()
                success = "Imported successfully"
                flash(success, "success")
        except Exception as e:
            flash("CSV parse error: " + str(e), "danger")
    return render_template("import_products.html", errors=errors, success=success)

# Analytics
@app.route("/analytics")
def analytics():
    if not admin_required():
        return redirect(url_for("login"))
    last_week = datetime.utcnow() - timedelta(days=7)
    results = db.session.query(Product.id, Product.name, func.count(Click.id)) \
        .outerjoin(Click).filter(Click.timestamp >= last_week).group_by(Product.id).all()
    total = sum([c for _, _, c in results])
    return render_template("analytics.html", results=results, last_week_clicks=total)

# Jobs page (placeholders for scheduling)
@app.route("/jobs")
def jobs():
    if not admin_required():
        return redirect(url_for("login"))
    return render_template("jobs.html", last_price_sync=None, next_price_sync=None,
                           last_auto_import=None, last_auto_delete=None)

# Static image route
@app.route("/static/images/<path:filename>")
def images(filename):
    return send_from_directory(os.path.join(app.root_path, "static", "images"), filename)

# Main entry
if __name__ == "__main__":
    app.run(debug=True)
