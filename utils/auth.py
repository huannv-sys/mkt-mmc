"""
Module xác thực và phân quyền người dùng
"""

import jwt
import bcrypt
import datetime
from functools import wraps
from flask import request, jsonify, session, redirect, url_for
import config

# Danh sách các quyền hạn người dùng
PERMISSIONS = {
    'admin': ['read', 'write', 'delete', 'config'],
    'user': ['read', 'write'],
    'viewer': ['read']
}

def hash_password(password):
    """Băm mật khẩu sử dụng bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password(password, hashed_password):
    """Kiểm tra mật khẩu"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def generate_token(user_id, username, role):
    """Tạo JWT token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=config.JWT_ACCESS_TOKEN_EXPIRES)
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm='HS256')

def decode_token(token):
    """Giải mã JWT token"""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def login_required(f):
    """Decorator yêu cầu đăng nhập"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('token')
        if not token:
            # Check for JWT in Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                return redirect(url_for('auth.login', next=request.url))
        
        user_data = decode_token(token)
        if not user_data:
            return redirect(url_for('auth.login', next=request.url))
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator yêu cầu quyền admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('token')
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                return jsonify({'error': 'Unauthorized'}), 401
        
        user_data = decode_token(token)
        if not user_data or user_data.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def has_permission(permission):
    """Decorator kiểm tra quyền hạn"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = session.get('token')
            if not token:
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                else:
                    return jsonify({'error': 'Unauthorized'}), 401
            
            user_data = decode_token(token)
            if not user_data:
                return jsonify({'error': 'Unauthorized'}), 401
            
            user_role = user_data.get('role')
            if user_role not in PERMISSIONS or permission not in PERMISSIONS[user_role]:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator