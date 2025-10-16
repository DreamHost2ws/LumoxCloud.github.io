from flask import Flask, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_dance.contrib.google import make_google_blueprint, google
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lumoxcloud.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# OAuth Blueprint
google_bp = make_google_blueprint(
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    redirect_url="/login/google/authorized",
    scope=["profile", "email"]
)
app.register_blueprint(google_bp, url_prefix="/login")

from models import User, Plan, PlanPurchase

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ROUTES
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login')
def login():
    return redirect(url_for("google.login"))

@app.route('/login/google/authorized')
def google_authorized():
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return redirect(url_for("home"))
    info = resp.json()
    
    user = User.query.filter_by(oauth_id=info["id"]).first()
    if not user:
        user = User(name=info["name"], email=info["email"], oauth_provider="google", oauth_id=info["id"])
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for("dashboard"))

@app.route('/dashboard')
@login_required
def dashboard():
    user_plans = current_user.plans
    plans = Plan.query.all()
    return render_template('dashboard.html', user=current_user, user_plans=user_plans, plans=plans)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)

