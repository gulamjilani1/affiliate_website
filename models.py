import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="admin", nullable=False)

    # Set password (hashing)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    # Check password (verify hash)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    __tablename__ = "product"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, default=0.0, nullable=False)
    category = db.Column(db.String(120))
    link = db.Column(db.String(1000), nullable=False)
    image = db.Column(db.String(500))
    description = db.Column(db.Text)
    sku = db.Column(db.String(120), index=True)
    source = db.Column(db.String(120))
    availability = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_synced = db.Column(db.DateTime)


class Click(db.Model):
    __tablename__ = "click"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ip_address = db.Column(db.String(100))
    user_agent = db.Column(db.String(300))

    product = db.relationship("Product", backref="clicks", lazy=True)
