from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, timedelta
from models import db, User, License, Payment
from utils.decorators import login_required
from services.mpesa import MPesaService

licensing_bp = Blueprint('licensing', __name__, url_prefix='/licensing')


@licensing_bp.route('/subscription')
@login_required
def subscription():
    user = User.query.get(session['user_id'])
    license = user.license

    if not license and not user.is_admin:
        license = License(
            user_id=user.id,
            subscription_type='trial',
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
            is_active=True
        )
        db.session.add(license)
        db.session.commit()

    payments = Payment.query.filter_by(license_id=license.id).order_by(Payment.created_at.desc()).all() if license else []

    return render_template('licensing/subscription.html',
                         license=license,
                         payments=payments,
                         current_user=user)


@licensing_bp.route('/initiate-payment', methods=['POST'])
@login_required
def initiate_payment():
    user = User.query.get(session['user_id'])
    data = request.form

    phone_number = data.get('phone_number')
    subscription_type = data.get('subscription_type')

    prices = {
        'monthly': 2000,
        'yearly': 20000
    }

    amount = prices.get(subscription_type, 2000)

    payment = Payment(
        license_id=user.license.id if user.license else None,
        amount=amount,
        phone_number=phone_number,
        subscription_type=subscription_type,
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()

    mpesa_service = MPesaService()
    result = mpesa_service.stk_push(
        phone_number=phone_number,
        amount=amount,
        account_reference=f'SUB-{user.id}',
        description=f'{subscription_type.capitalize()} Subscription'
    )

    if result.get('ResponseCode') == '0':
        payment.checkout_request_id = result.get('CheckoutRequestID')
        db.session.commit()

        flash('Payment request sent! Please enter your M-Pesa PIN.', 'success')
        return redirect(url_for('licensing.check_payment', payment_id=payment.id))
    else:
        payment.status = 'failed'
        db.session.commit()
        flash(f'Payment failed: {result.get("CustomerMessage", "Unknown error")}', 'error')
        return redirect(url_for('licensing.subscription'))


@licensing_bp.route('/check-payment/<int:payment_id>')
@login_required
def check_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    user = User.query.get(session['user_id'])

    if payment.license.user_id != user.id and not user.is_admin:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('licensing.subscription'))

    return render_template('licensing/check_payment.html', payment=payment)


@licensing_bp.route('/payment-status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    user = User.query.get(session['user_id'])

    if payment.license.user_id != user.id and not user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'status': payment.status,
        'mpesa_receipt': payment.mpesa_receipt,
        'completed_at': payment.completed_at.isoformat() if payment.completed_at else None
    })


@licensing_bp.route('/mpesa-callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()

    result_code = data['Body']['stkCallback']['ResultCode']
    checkout_request_id = data['Body']['stkCallback']['CheckoutRequestID']

    payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()

    if not payment:
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Payment not found'}), 404

    if result_code == 0:
        callback_metadata = data['Body']['stkCallback']['CallbackMetadata']['Item']
        mpesa_receipt = next((item['Value'] for item in callback_metadata if item['Name'] == 'MpesaReceiptNumber'), None)

        payment.status = 'completed'
        payment.mpesa_receipt = mpesa_receipt
        payment.completed_at = datetime.utcnow()

        license = payment.license
        if not license:
            license = License(user_id=payment.license.user_id)
            db.session.add(license)

        if payment.subscription_type == 'monthly':
            days = 30
        else:
            days = 365

        if license.end_date and license.end_date > datetime.utcnow():
            license.end_date += timedelta(days=days)
        else:
            license.start_date = datetime.utcnow()
            license.end_date = datetime.utcnow() + timedelta(days=days)

        license.subscription_type = payment.subscription_type
        license.is_active = True

        db.session.commit()

        return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'}), 200
    else:
        payment.status = 'failed'
        db.session.commit()

        return jsonify({'ResultCode': 1, 'ResultDesc': 'Payment failed'}), 200