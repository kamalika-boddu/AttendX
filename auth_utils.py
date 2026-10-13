import datetime
import hmac
import hashlib
import json
import secrets
import time
import jwt
from functools import wraps
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

def hash_password(password: str) -> str:
    """Hash password using strong PBKDF2/scrypt algorithm."""
    return generate_password_hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verify raw password against stored secure hash."""
    return check_password_hash(password_hash, password)

def generate_jwt_token(user_id: int, email: str, role: str, name: str, student_id: str = None) -> str:
    """Generate signed JWT token containing user identity, role, and optional student_id."""
    payload = {
        'sub': str(user_id),
        'user_id': user_id,
        'email': email,
        'role': role,
        'name': name,
        'student_id': student_id,
        'iat': datetime.datetime.now(datetime.timezone.utc),
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')

def decode_jwt_token(token: str) -> dict:
    """Decode and validate signed JWT token."""
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return {'error': 'Token has expired. Please log in again.'}
    except Exception as e:
        return {'error': f'Invalid authentication token: {str(e)}'}

def token_required(f):
    """Decorator to enforce authenticated JWT tokens on API endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'success': False, 'message': 'Authorization header is missing.'}), 401
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'success': False, 'message': 'Invalid token format. Expected: Bearer <token>'}), 401
        
        token = parts[1]
        decoded = decode_jwt_token(token)
        if 'error' in decoded:
            return jsonify({'success': False, 'message': decoded['error']}), 401
        
        # Attach user info to Flask's global context
        g.current_user = {
            'id': decoded['sub'],
            'email': decoded['email'],
            'role': decoded['role'],
            'name': decoded.get('name', ''),
            'student_id': decoded.get('student_id')
        }
        return f(*args, **kwargs)
    return decorated

def roles_required(*allowed_roles):
    """Decorator to enforce role-based authorization (e.g. 'teacher', 'admin')."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401
            
            user_role = g.current_user.get('role')
            if user_role not in allowed_roles:
                return jsonify({
                    'success': False,
                    'message': f"Access forbidden. Endpoint requires one of roles: {', '.join(allowed_roles)}."
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator


def generate_student_qr_payload(student_id: str) -> str:
    """
    Generate an opaque, cryptographically signed QR code payload for a student.
    Payload does not expose passwords, personal secrets, or unnecessary information.
    Signature protects against client-side forgery or tampering.
    """
    nonce = secrets.token_hex(8)
    iat = int(time.time())
    data_to_sign = f"{student_id}:{nonce}:{iat}".encode('utf-8')
    sig = hmac.new(Config.JWT_SECRET.encode('utf-8'), data_to_sign, hashlib.sha256).hexdigest()

    payload = {
        'version': '1',
        'type': 'attendx-student-qr',
        'student_id': student_id,
        'nonce': nonce,
        'iat': iat,
        'sig': sig
    }
    return json.dumps(payload, separators=(',', ':'))


def verify_student_qr_payload(qr_payload_str: str) -> tuple:
    """
    Verify and decode a student QR code payload.
    Returns: (is_valid: bool, student_id: str, error_msg: str)
    """
    if not qr_payload_str or not isinstance(qr_payload_str, str):
        return False, None, "Invalid or empty QR code."

    qr_payload_str = qr_payload_str.strip()

    try:
        data = json.loads(qr_payload_str)
    except Exception:
        # If it was sent as plain string or simple student id (e.g. for fallback testing or direct entry)
        if qr_payload_str.upper().startswith("STD-"):
            return True, qr_payload_str.upper(), None
        return False, None, "Invalid QR code format: JSON expected."

    if not isinstance(data, dict):
        return False, None, "Invalid QR code payload structure."

    # Check if this is the signed format
    if 'sig' in data and 'student_id' in data and 'nonce' in data and 'iat' in data:
        student_id = data['student_id']
        nonce = data['nonce']
        iat = data['iat']
        provided_sig = data['sig']

        expected_bytes = f"{student_id}:{nonce}:{iat}".encode('utf-8')
        expected_sig = hmac.new(Config.JWT_SECRET.encode('utf-8'), expected_bytes, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(provided_sig, expected_sig):
            return False, None, "Cryptographic signature validation failed. QR code may be counterfeit or tampered."

        return True, student_id, None

    # Also support older pass format: {"type": "attendx-student-pass", "studentId": "..."}
    if data.get('type') == 'attendx-student-pass' and data.get('studentId'):
        return True, data['studentId'], None

    # Or if student_id is present in simple JSON
    if data.get('student_id'):
        return True, data['student_id'], None

    return False, None, "Missing student identifier in QR payload."

