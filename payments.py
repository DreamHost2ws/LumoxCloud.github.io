import qrcode
import stripe
import os
from app import db
from models import PlanPurchase, Plan

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")  # your Stripe secret key

def create_payment(user_id, plan_id):
    plan = Plan.query.get(plan_id)
    if not plan:
        return None, None
    
    # Create Stripe Payment Link
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": plan.name},
                "unit_amount": int(plan.price * 100),  # cents
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url="http://localhost:5000/payment_success?user_id={}&plan_id={}".format(user_id, plan.id),
        cancel_url="http://localhost:5000/dashboard",
    )
    
    # Generate QR Code
    img = qrcode.make(session.url)
    qr_path = f"static/qr/{user_id}_{plan.id}.png"
    img.save(qr_path)
    
    # Create pending PlanPurchase
    purchase = PlanPurchase(user_id=user_id, plan_id=plan.id, status="pending")
    db.session.add(purchase)
    db.session.commit()
    
    return qr_path, session.url

