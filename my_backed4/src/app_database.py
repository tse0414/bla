# 檔案位置: my_backed3/src/app_database.py
"""
物流管理系統後端 API - 資料庫版 (app_database.py)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from enum import Enum
import uuid
import hashlib
import jwt
from functools import wraps
import os

app = Flask(__name__)
CORS(app)

# ========== 1. 資料庫設定 ==========
basedir = os.path.abspath(os.path.dirname(__file__))
# 資料庫檔案會產生在 src 資料夾下，名為 logistics.db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'logistics.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "my_secret_key_123"

db = SQLAlchemy(app)

# ========== 2. Enum 定義 (轉為字串儲存) ==========
class CustomerType(Enum):
    CONTRACT = "合約"
    NON_CONTRACT = "非合約"
    PREPAID = "預付"

class ServiceType(Enum):
    STANDARD = "標準配送"
    EXPRESS = "快速配送"
    OVERNIGHT = "隔夜配送"

class PackageStatus(Enum):
    CREATED = "已建立"
    PICKUP = "已取件"
    IN_TRANSIT = "運輸中"
    DELIVERED = "已送達"
    EXCEPTION = "異常"

# ========== 3. 資料庫模型 (Models) ==========

class User(db.Model):
    """使用者帳號"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Customer(db.Model):
    """客戶資料"""
    account = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    customer_type = db.Column(db.String(20), default=CustomerType.NON_CONTRACT.value)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "account": self.account,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "type": self.customer_type,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

class Package(db.Model):
    """包裹資料"""
    tracking_number = db.Column(db.String(50), primary_key=True)
    sender_id = db.Column(db.String(50), nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    recipient_address = db.Column(db.String(200), nullable=False)
    
    weight = db.Column(db.Float, default=0.0)
    distance = db.Column(db.Float, default=0.0)
    
    status = db.Column(db.String(20), default=PackageStatus.CREATED.value)
    service_type = db.Column(db.String(20), default=ServiceType.STANDARD.value)
    
    location = db.Column(db.String(100), default="轉運中心")
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "tracking_number": self.tracking_number,
            "sender_id": self.sender_id,
            "recipient_name": self.recipient_name,
            "recipient_address": self.recipient_address,
            "weight": self.weight,
            "distance": self.distance,
            "status": self.status,
            "service_type": self.service_type,
            "location": self.location,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

# ========== 4. 輔助函式 ==========

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_token_and_role(required_role: str = None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "缺少 Authorization header"}), 401
            try:
                token = auth_header.replace("Bearer ", "")
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                
                role_levels = {'customer': 0, 'staff': 1, 'admin': 2}
                user_level = role_levels.get(payload['role'], 0)
                req_level = role_levels.get(required_role, 0) if required_role else 0

                if user_level < req_level:
                    return jsonify({"error": f"權限不足，需要 {required_role} 權限"}), 403
                
                request.current_user = payload
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token 已過期"}), 401
            except Exception:
                return jsonify({"error": "驗證失敗"}), 401
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ========== 5. API 路由 ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "物流系統 (DB版) 運行中"})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "使用者已存在"}), 400
    
    new_user = User(
        username=data['username'],
        password_hash=hash_password(data['password']),
        role=data.get("role", "customer")
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "註冊成功", "username": new_user.username}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or user.password_hash != hash_password(data['password']):
        return jsonify({"error": "帳號或密碼錯誤"}), 401
    
    token = jwt.encode({
        "username": user.username,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=3)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({"token": token, "username": user.username, "role": user.role})

@app.route('/api/customers', methods=['POST'])
@verify_token_and_role('staff')
def create_customer():
    data = request.json
    if Customer.query.filter_by(account=data['account']).first():
        return jsonify({"error": "客戶帳號已存在"}), 400

    new_customer = Customer(
        account=data['account'],
        name=data['name'],
        email=data['email'],
        phone=data['phone'],
        address=data['address'],
        customer_type=data.get('type', CustomerType.NON_CONTRACT.value)
    )
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({"success": True, "customer": new_customer.to_dict()})

@app.route('/api/customers', methods=['GET'])
@verify_token_and_role()
def get_customers():
    customers = Customer.query.all()
    return jsonify([c.to_dict() for c in customers])

@app.route('/api/parcels', methods=['POST'])
@verify_token_and_role('staff')
def create_parcel():
    data = request.json
    track_no = f"TRK{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
    
    new_pkg = Package(
        tracking_number=track_no,
        sender_id=data['sender_id'],
        recipient_name=data['recipient_name'],
        recipient_address=data['recipient_address'],
        weight=float(data.get('weight', 0.0)),
        distance=float(data.get('distance', 0.0)),
        status=PackageStatus.CREATED.value,
        service_type=data.get('service_type', ServiceType.STANDARD.value)
    )
    db.session.add(new_pkg)
    db.session.commit()
    return jsonify({"success": True, "package": new_pkg.to_dict()})

@app.route('/api/parcels', methods=['GET'])
@verify_token_and_role()
def get_parcels():
    user = request.current_user
    if user['role'] == 'customer':
        parcels = Package.query.filter_by(sender_id=user['username']).all()
    else:
        parcels = Package.query.all()
    return jsonify([p.to_dict() for p in parcels])

@app.route('/api/parcels/search', methods=['POST'])
@verify_token_and_role()
def search_parcels():
    data = request.json
    user = request.current_user
    query = Package.query
    
    if user['role'] == 'customer':
        query = query.filter_by(sender_id=user['username'])
    else:
        if 'sender_id' in data and data['sender_id']:
            query = query.filter_by(sender_id=data['sender_id'])
            
    if 'status' in data and data['status']:
        query = query.filter_by(status=data['status'])

    results = query.all()
    return jsonify([p.to_dict() for p in results])

# ========== 6. 初始化 ==========
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            print("📦 初始化資料庫與測試帳號...")
            db.session.add(User(username='admin', password_hash=hash_password('admin123'), role='admin'))
            db.session.add(User(username='staff1', password_hash=hash_password('staff123'), role='staff'))
            db.session.add(User(username='customer1', password_hash=hash_password('customer123'), role='customer'))
            db.session.commit()
            print("✅ 測試帳號建立完成")

if __name__ == '__main__':
    if not os.path.exists(os.path.join(basedir, 'logistics.db')):
        init_db()
    print("🚀 物流系統 (app_database.py) 啟動！")
    app.run(debug=True, host='0.0.0.0', port=5000)