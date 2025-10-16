import os
from flask import Flask, render_template, redirect, url_for, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from dotenv import load_dotenv
from functools import wraps
from payments import create_payment

load_dotenv()

# ------------------------
# Flask App Initialization
# ------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lumoxcloud.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ------------------------
# Import Models
# ------------------------
from models import User, Plan, PlanPurchase

# ------------------------
# OAuth Setup - Google
# ------------------------
google_bp = make_google_blueprint(
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    redirect_url="/login/google/authorized",
    scope=["profile", "email"]
)
app.register_blueprint(google_bp, url_prefix="/login")

# ------------------------
# Login Manager
# ------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------
# Admin Decorator
# ------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# ------------------------
# Routes
# ------------------------
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
        user = User(
            name=info["name"],
            email=info["email"],
            oauth_provider="google",
            oauth_id=info["id"]
        )
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


# ------------------------
# Purchase Plan Route
# ------------------------
@app.route('/purchase/<int:plan_id>')
@login_required
def purchase_plan(plan_id):
    qr_path, payment_url = create_payment(current_user.id, plan_id)
    if not qr_path:
        return "Plan not found", 404
    return render_template('purchase_plan.html', qr_path=qr_path, payment_url=payment_url)


# ------------------------
# Payment Success Route
# ------------------------
@app.route('/payment_success')
def payment_success():
    user_id = request.args.get("user_id")
    plan_id = request.args.get("plan_id")
    
    purchase = PlanPurchase.query.filter_by(
        user_id=user_id, plan_id=plan_id, status="pending"
    ).first()
    if purchase:
        purchase.status = "completed"
        db.session.commit()
    
    return redirect(url_for("dashboard"))


# ------------------------
# Admin Panel Routes
# ------------------------
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    users = User.query.all()
    plans = Plan.query.all()
    payments = PlanPurchase.query.all()
    return render_template('admin_panel.html', users=users, plans=plans, payments=payments)


@app.route('/admin/add_plan', methods=['GET', 'POST'])
@login_required
@admin_required
def add_plan():
    if request.method == 'POST':
        name = request.form.get('name')
        plan_type = request.form.get('type')
        price = float(request.form.get('price'))
        resources = request.form.get('resources')
        duration = int(request.form.get('duration'))

        plan = Plan(name=name, type=plan_type, price=price, resources=resources, duration=duration)
        db.session.add(plan)
        db.session.commit()
        return redirect(url_for('admin_panel'))
    return render_template('add_plan.html')


@app.route('/admin/delete_plan/<int:plan_id>')
@login_required
@admin_required
def delete_plan(plan_id):
    plan = Plan.query.get(plan_id)
    if plan:
        db.session.delete(plan)
        db.session.commit()
    return redirect(url_for('admin_panel'))


@app.route('/admin/complete_payment/<int:purchase_id>')
@login_required
@admin_required
def complete_payment(purchase_id):
    purchase = PlanPurchase.query.get(purchase_id)
    if purchase:
        purchase.status = "completed"
        db.session.commit()
    return redirect(url_for('admin_panel'))


# ------------------------
# Run App
# ------------------------
if __name__ == '__main__':
    app.run(debug=True)
