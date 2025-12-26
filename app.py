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
# USER MODEL
# -------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # ✅ NEW

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    mrp = db.Column(db.Integer, nullable=False)      # NEW
    price = db.Column(db.Integer, nullable=False)    # Sale price
    stock = db.Column(db.Integer, nullable=False)  # NEW
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

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    quantity = db.Column(db.Integer, nullable=False)

    user = db.relationship("User")
    product = db.relationship("Product")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Integer, nullable=False)


# -------------------------------------------------
# LOAD USER
# -------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        count = (
            db.session.query(db.func.sum(CartItem.quantity))
            .filter(CartItem.user_id == current_user.id)
            .scalar()
        )
        return {"cart_count": count or 0}
    return {"cart_count": 0}

# -------------------------------------------------
# HOME PAGE
# -------------------------------------------------
@app.route("/")
def home():
    products = Product.query.all()
    return render_template("home.html", sarees=products)

# -------------------------------------------------
# REGISTER
# -------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        user = User(
            name=name,
            email=email,
            password=hashed_password
        )
        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")

# -------------------------------------------------
# LOGIN
# -------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password")

    return render_template("login.html")


@app.route("/product/<int:id>")
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template("product_detail.html", product=product)

@app.route("/add-products")
def add_products():
    products = [
        Product(
            name="Kanjeevaram Silk Saree",
            mrp=3499,
            price=2499,
            stock=100,
            image="https://via.placeholder.com/300",
            description="Premium silk saree"
        ),
        Product(
            name="Banarasi Saree",
            mrp=2999,
            price=1999,
            stock=100,
            image="https://via.placeholder.com/300",
            description="Wedding saree"
        ),
        Product(
            name="Cotton Handloom Saree",
            mrp=1999,
            price=999,
            stock=100,
            image="https://via.placeholder.com/300",
            description="Homely Ware Sarees"
        ),
        Product(
            name="Designing Party Saree",
            mrp=4999,
            price=3999,
            stock=100,
            image="https://via.placeholder.com/300",
            description="Party Ware Sarees"
        )
    ]

    db.session.add_all(products)
    db.session.commit()
    return "Products added"

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get("quantity", 1))

    # ❌ Edge case: invalid quantity
    if quantity <= 0:
        flash("Invalid quantity")
        return redirect(url_for("home"))

    # ❌ Edge case: stock exceeded
    if quantity > product.stock:
        flash("Not enough stock available")
        return redirect(url_for("product_detail", id=product.id))

    cart_item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product.id
    ).first()

    if cart_item:
        if cart_item.quantity + quantity > product.stock:
            flash("Stock limit exceeded")
            return redirect(url_for("product_detail", id=product.id))
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product.id,
            quantity=quantity
        )
        db.session.add(cart_item)

    db.session.commit()
    flash("Item added to cart")
    return redirect(url_for("cart"))

@app.route("/cart")
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()

    total = sum(item.product.price * item.quantity for item in items)
    return render_template("cart.html", items=items, total=total)


@app.route("/update-cart/<int:cart_id>", methods=["POST"])
@login_required
def update_cart(cart_id):
    cart_item = CartItem.query.get_or_404(cart_id)
    new_qty = int(request.form.get("quantity"))

    # ❌ Security check
    if cart_item.user_id != current_user.id:
        flash("Unauthorized access")
        return redirect(url_for("cart"))

    # ❌ Invalid quantity
    if new_qty <= 0:
        flash("Quantity must be at least 1")
        return redirect(url_for("cart"))

    # ❌ Stock limit
    if new_qty > cart_item.product.stock:
        flash("Quantity exceeds available stock")
        return redirect(url_for("cart"))

    cart_item.quantity = new_qty
    db.session.commit()

    flash("Cart updated")
    return redirect(url_for("cart"))

@app.route("/remove-from-cart/<int:cart_id>")
@login_required
def remove_from_cart(cart_id):
    cart_item = CartItem.query.get_or_404(cart_id)

    if cart_item.user_id != current_user.id:
        flash("Unauthorized action")
        return redirect(url_for("cart"))

    db.session.delete(cart_item)
    db.session.commit()

    flash("Item removed from cart")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not items:
        flash("Cart is empty")
        return redirect(url_for("cart"))

    total = 0

    # 🔒 TRANSACTION SAFETY
    try:
        for item in items:
            product = item.product

            # ❌ Edge case: stock changed
            if item.quantity > product.stock:
                flash(f"Not enough stock for {product.name}")
                return redirect(url_for("cart"))

            product.stock -= item.quantity
            total += product.price * item.quantity

        order = Order(
            user_id=current_user.id,
            total_amount=total
        )
        db.session.add(order)

        # Clear cart
        CartItem.query.filter_by(user_id=current_user.id).delete()

        db.session.commit()
        flash("Order placed successfully (Dummy Checkout)")

    except Exception:
        db.session.rollback()
        flash("Checkout failed. Try again.")

    return redirect(url_for("home"))


@app.route("/orders")
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template("orders.html", orders=user_orders)

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)

    products = Product.query.all()
    return render_template("admin/dashboard.html", products=products)

# -------------------------------------------------
# LOGOUT
# -------------------------------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# -------------------------------------------------
# CREATE DATABASE
# -------------------------------------------------
with app.app_context():
    db.create_all()

# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
    