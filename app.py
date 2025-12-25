from flask import Flask, render_template, redirect, url_for, request, flash
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

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)  # NEW
    image = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)

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
    return User.query.get(int(user_id))

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

@app.route("/add-products")
def add_products():
    products = [
        Product(
            name="Kanjeevaram Silk Saree",
            price=2499,
            stock=100,
            image="https://via.placeholder.com/300",
            description="Premium silk saree"
        ),
        Product(
            name="Banarasi Saree",
            price=1999,
            stock=100,
            image="https://via.placeholder.com/300",
            description="Wedding saree"
        ),
        Product(
            name="Cotton Handloom Saree",
            price=999,
            stock=100,
            image="https://via.placeholder.com/300",
            description="Homely Ware Sarees"
        ),
        Product(
            name="Designing Party Saree",
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

@app.route("/product/<int:id>")
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template("product_detail.html", product=product)


@app.route("/cart")
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()

    total = sum(item.product.price * item.quantity for item in items)
    return render_template("cart.html", items=items, total=total)

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
