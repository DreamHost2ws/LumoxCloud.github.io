from app import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    oauth_provider = db.Column(db.String(20))
    oauth_id = db.Column(db.String(200), unique=True)
    is_admin = db.Column(db.Boolean, default=False)  # admin flag
    plans = db.relationship('PlanPurchase', backref='user', lazy=True)

class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    type = db.Column(db.String(10))  # MC or VPS
    price = db.Column(db.Float)
    resources = db.Column(db.String(200))  # JSON or text
    duration = db.Column(db.Integer)  # in days

class PlanPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'))
    status = db.Column(db.String(20), default="pending")  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
