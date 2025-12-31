import os
from werkzeug.utils import secure_filename
from flask import Flask, abort, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

# -------------------------------------------------
# APP CONFIG
# -------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "sareestore_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# -------------------------------------------------
# DATABASE
# -------------------------------------------------
db = SQLAlchemy(app)

# -------------------------------------------------
# LOGIN MANAGER
# -------------------------------------------------
login_manager = LoginManager(app)
login_manager.login_view = "login"

# -------------------------------------------------
# MODELS
# -------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    mrp = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    product = db.relationship("Product")


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    product = db.relationship("Product")

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    product = db.relationship("Product")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Integer, nullable=False)


# -------------------------------------------------
# USER LOADER
# -------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------------------------
# CONTEXT PROCESSOR
# -------------------------------------------------
@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        count = db.session.query(
            func.sum(CartItem.quantity)
        ).filter_by(user_id=current_user.id).scalar()
        return {"cart_count": count or 0}
    return {"cart_count": 0}

# -------------------------------------------------
# ROUTES
# -------------------------------------------------
@app.route("/")
def home():
    products = Product.query.all()
    return render_template("home.html", sarees=products)

# ---------- AUTH ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if User.query.filter_by(email=request.form["email"]).first():
            flash("Email already registered")
            return redirect(url_for("register"))
        

        user = User(
            name=request.form["name"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()

        if not user:
            flash("User not found")
            return redirect(url_for("login"))

        if not check_password_hash(user.password, request.form["password"]):
            flash("Incorrect password")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("home"))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ---------- PRODUCT ----------
@app.route("/product/<int:product_id>")
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product_details.html", product=product)

@app.route("/add-products")
def add_products():
    products = [
        Product(
            name="Kanjeevaram Silk Saree",
            mrp=3499,
            price=2499,
            stock=200,
            image="https://via.placeholder.com/300",
            description="Premium silk saree"
        ),
        Product(
            name="Banarasi Saree",
            mrp=2999,
            price=1999,
            stock=200,
            image="https://via.placeholder.com/300",
            description="Renowned for their luxurious silk and intricate zari work, Banarasi sarees are traditionally woven in Varanasi. Ideal for weddings and grand occasions, they often feature Mughal-inspired motifs like florals, bel, and jhallar."
        ),
        Product(
            name="Cotton Handloom Saree",
            mrp=1999,
            price=999,
            stock=200,
            image="https://via.placeholder.com/300",
            description="Homely Ware Sarees"
        ),
        Product(
            name="Designing Party Saree",
            mrp=4999,
            price=3999,
            stock=200,
            image="https://via.placeholder.com/300",
            description="Party Ware Sarees"
        ),
        Product(
            name="Phulkari Saree",
            mrp=2999,
            price=1999,
            stock=200,
            image="https://via.placeholder.com/300",
            description="Phulkari, meaning ‘flower work,’ is known for its colourful embroidery using silk threads. Originally a form of dupatta decoration, this style is now beautifully adapted into sarees."
        ),
        Product(
            name="Chanderi Saree",
            mrp=5999,
            price=4999,
            stock=200,
            image="https://via.placeholder.com/300",
            description="Chanderi sarees are known for their lightweight texture and intricate patterns. They are traditionally woven in the city of Chanderi, Madhya Pradesh, and are often made from silk or cotton."
        ),
        Product(
            name="Bhagalpuri Saree",
            mrp=9999,
            price=8999,
            stock=200,
            image="https://via.placeholder.com/300",
            description="Celebrated for their unique texture and natural sheen, Bhagalpuri sarees are handwoven in Bhagalpur, Bihar. Made from Tussar silk, these sarees often feature traditional motifs inspired by nature."
        ),
         Product(
            name="Bandhani Saree",
            mrp=10999,
            price=9999,
            stock=200,
            image="https://via.placeholder.com/300",
            description="Celebrated for their vibrant colors and intricate tie-dye patterns, Bandhani sarees are traditionally crafted in Rajasthan and Gujarat. The process involves tying small sections of fabric before dyeing, resulting in distinctive designs like dots, waves, and stripes."
        )
    ]

    db.session.add_all(products)
    db.session.commit()
    return "Products added"

# ---------- CART ----------
@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    qty = int(request.form.get("quantity", 1))

    item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product.id
    ).first()

    if item:
        item.quantity += qty
    else:
        db.session.add(CartItem(
            user_id=current_user.id,
            product_id=product.id,
            quantity=qty
        ))

    db.session.commit()
    flash("Added to cart")
    return redirect(url_for("product_details", product_id=product.id))

@app.route("/cart")
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(i.product.price * i.quantity for i in items)
    return render_template("cart.html", items=items, total=total)

# ---------- WISHLIST ----------
@app.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
@login_required
def toggle_wishlist(product_id):
    item = Wishlist.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()

    if item:
        db.session.delete(item)
    else:
        db.session.add(Wishlist(
            user_id=current_user.id,
            product_id=product_id
        ))

    db.session.commit()
    flash("Item Added to Wishlist" if not item else "Item Removed from Wishlist")
    return redirect(request.referrer)

@app.route("/wishlist")
@login_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=current_user.id).all()
    return render_template("wishlist.html", items=items)

# ---------- ORDERS ----------
@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(i.product.price * i.quantity for i in items)

    db.session.add(Order(
        user_id=current_user.id,
        total_amount=total
    ))

    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    flash("Order placed successfully")
    return redirect(url_for("orders"))

@app.route("/orders")
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template("orders.html", orders=orders)

# ---------- ADMIN ----------
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)

    products = Product.query.all()

    return render_template(
        "admin/dashboard.html",
        products=products
    )
def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)

@app.route("/admin/product/add", methods=["GET", "POST"])
@login_required
def admin_add_product():
    if not current_user.is_admin:
        abort(403)

    if request.method == "POST":
        name = request.form["name"]
        mrp = request.form["mrp"]
        price = request.form["price"]
        stock = request.form["stock"]
        description = request.form["description"]

        image = request.files["image"]
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        new_product = Product(
            name=name,
            mrp=mrp,
            price=price,
            stock=stock,
            image=filename,
            description=description
        )

        db.session.add(new_product)
        db.session.commit()

        flash("Product added successfully")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/add_product.html")

@app.route("/admin/product/edit/<int:id>", methods=["GET", "POST"])
@login_required
def admin_edit_product(id):
    if not current_user.is_admin:
        abort(403)

    product = Product.query.get_or_404(id)

    if request.method == "POST":
        product.name = request.form["name"]
        product.mrp = request.form["mrp"]
        product.price = request.form["price"]
        product.stock = request.form["stock"]
        product.description = request.form["description"]

        image_file = request.files.get("image")
        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(image_path)
            product.image = filename

        db.session.commit()
        flash("Product updated")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/edit_product.html", product=product)

@app.route("/admin/product/delete/<int:id>")
@login_required
def admin_delete_product(id):
    admin_required()
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/update-stock/<int:id>", methods=["POST"])
@login_required
def admin_update_stock(id):
    if not current_user.is_admin:
        abort(403)

    product = Product.query.get_or_404(id)
    product.stock = int(request.form["stock"])
    db.session.commit()

    flash("Stock updated successfully")
    return redirect(url_for("admin_dashboard"))

# -------------------------------------------------
# INIT DB
# -------------------------------------------------
with app.app_context():
    db.create_all()

# -------------------------------------------------
# RUN
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
