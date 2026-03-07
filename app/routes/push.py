import json
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import PushSubscription, db

bp = Blueprint('push', __name__, url_prefix='/api/push')

@bp.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    """Register a new push subscription for the current user."""
    subscription_info = request.get_json()
    
    if not subscription_info:
        return jsonify({'error': 'Invalid subscription info JSON.'}), 400
        
    endpoint = subscription_info.get('endpoint')
    keys = subscription_info.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return jsonify({'error': 'Missing required subscription fields.'}), 400

    # Ensure no duplicates for this exact endpoint
    existing_sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    
    if existing_sub:
        if existing_sub.user_id != current_user.id:
            db.session.delete(existing_sub)
            db.session.commit()
        else:
            return jsonify({'message': 'Subscription already exists.'}), 200

    new_sub = PushSubscription(
        user_id=current_user.id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth
    )
    
    db.session.add(new_sub)
    db.session.commit()

    return jsonify({'message': 'Subscription saved safely.'}), 201

@bp.route('/vapid_public_key', methods=['GET'])
def vapid_public_key():
    """Return the VAPID public key needed by the frontend to subscribe."""
    public_key = current_app.config.get('VAPID_PUBLIC_KEY')
    if not public_key:
        return jsonify({'error': 'VAPID public key not configured.'}), 500
    return jsonify({'public_key': public_key}), 200
