#版本三-> add 登入權限處理
"""
物流管理系統後端 API - 整合 JWT 驗證版本
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from enum import Enum
import uuid
import json
import os
import hashlib
import jwt
from functools import wraps

app = Flask(__name__)
CORS(app)

# JWT 密鑰
SECRET_KEY = "my_secret_key_123"

# ========== 登入系統 ==========
users = {}  # {username: {password_hash, role}}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_token_and_role(required_role: str = None):
    """驗證 Token 並檢查角色權限的裝飾器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                return jsonify({"error": "缺少 Authorization header"}), 401
            
            try:
                token = auth_header.replace("Bearer ", "")
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                
                # 檢查角色權限
                if required_role:
                    role_hierarchy = {
                        'customer': 0,
                        'staff': 1,
                        'admin': 2
                    }
                    
                    user_level = role_hierarchy.get(payload['role'], 0)
                    required_level = role_hierarchy.get(required_role, 2)
                    
                    if user_level < required_level:
                        return jsonify({"error": f"權限不足，需要 {required_role} 權限"}), 403
                
                # 將使用者資訊附加到 request 中
                request.current_user = payload
                
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token 已過期"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Token 無效"}), 401
            except Exception as e:
                return jsonify({"error": f"驗證失敗: {str(e)}"}), 401
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ========== 登入 API ==========
@app.route('/api/auth/register', methods=['POST'])
def register():
    """註冊新使用者"""
    data = request.json
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "customer")  # 預設為客戶
    
    if not username or not password:
        return jsonify({"error": "缺少帳號或密碼"}), 400
    
    if username in users:
        return jsonify({"error": "使用者已存在"}), 400
    
    users[username] = {
        "password_hash": hash_password(password),
        "role": role
    }
    
    return jsonify({
        "message": "註冊成功",
        "username": username,
        "role": role
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    """使用者登入"""
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"error": "缺少帳號或密碼"}), 400
    
    user = users.get(username)
    if not user or user["password_hash"] != hash_password(password):
        return jsonify({"error": "帳號或密碼錯誤"}), 401
    
    token = jwt.encode({
        "username": username,
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=3)
    }, SECRET_KEY, algorithm="HS256")
    
    return jsonify({
        "token": token,
        "username": username,
        "role": user["role"]
    })

# ========== 枚舉類型 ==========
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

# ========== 資料模型 (簡化版) ==========
class Customer:
    def __init__(self, name: str, address: str, phone: str, email: str, account: str = None):
        self.customer_id = account if account else str(uuid.uuid4())
        self.name = name
        self.address = address
        self.phone = phone
        self.email = email
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

class Package:
    def __init__(self, sender_id: str, recipient_name: str, recipient_address: str):
        self.tracking_number = f"TRK{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"
        self.sender_id = sender_id
        self.recipient_name = recipient_name
        self.recipient_address = recipient_address
        self.weight = 0.0
        self.distance = 0.0
        self.status = PackageStatus.CREATED
        self.service_type = ServiceType.STANDARD
        self.location = ""
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            "tracking_number": self.tracking_number,
            "sender_id": self.sender_id,
            "recipient_name": self.recipient_name,
            "recipient_address": self.recipient_address,
            "weight": self.weight,
            "distance": self.distance,
            "status": self.status.value,
            "location": self.location,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

# ========== 管理器 ==========
class CustomerManager:
    def __init__(self):
        self.customers: Dict[str, Customer] = {}

    def create_customer(self, name: str, address: str, phone: str, email: str, account: str) -> Customer:
        customer = Customer(name, address, phone, email, account)
        self.customers[customer.customer_id] = customer
        return customer

    def get_all(self):
        return [c.to_dict() for c in self.customers.values()]
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self.customers.get(customer_id)

class PackageManager:
    def __init__(self):
        self.packages: Dict[str, Package] = {}

    def create_package(self, sender_id: str, recipient_name: str, recipient_address: str) -> Package:
        package = Package(sender_id, recipient_name, recipient_address)
        self.packages[package.tracking_number] = package
        return package

    def get_package(self, tracking_number: str) -> Optional[Package]:
        return self.packages.get(tracking_number)

    def get_all(self):
        return [p.to_dict() for p in self.packages.values()]

    def search_packages(self, criteria: Dict) -> List[Dict]:
        results = []
        for pkg in self.packages.values():
            match = True
            
            if 'sender_id' in criteria and criteria['sender_id']:
                if pkg.sender_id != criteria['sender_id']:
                    match = False
            
            if 'status' in criteria and criteria['status']:
                if pkg.status.value != criteria['status']:
                    match = False
           
            if match:
                results.append(pkg.to_dict())
        
        return results

# ========== 初始化 ==========
customer_mgr = CustomerManager()
package_mgr = PackageManager()

# ========== API 路由 ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "物流系統運行中"})

# ========== 客戶管理 API (需要 staff 權限) ==========
@app.route('/api/customers', methods=['POST'])
@verify_token_and_role('staff')
def create_customer():
    """建立客戶 - 需要 staff 權限"""
    data = request.json
    try:
        customer = customer_mgr.create_customer(
            name=data['name'],
            address=data['address'],
            phone=data['phone'],
            email=data['email'],
            account=data['account']
        )
        return jsonify({
            "success": True,
            "customer": customer.to_dict(),
            "created_by": request.current_user['username']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/customers', methods=['GET'])
@verify_token_and_role()
def get_customers():
    """取得所有客戶 - 需登入"""
    return jsonify(customer_mgr.get_all())

# ========== 包裹管理 API ==========
@app.route('/api/parcels', methods=['POST'])
@verify_token_and_role('staff')
def create_parcel():
    """建立包裹 - 需要 staff 權限"""
    data = request.json
    try:
        package = package_mgr.create_package(
            sender_id=data['sender_id'],
            recipient_name=data['recipient_name'],
            recipient_address=data['recipient_address']
        )
        
        if 'weight' in data:
            package.weight = float(data['weight'])
        if 'distance' in data:
            package.distance = float(data['distance'])
        
        return jsonify({
            "success": True,
            "package": package.to_dict(),
            "created_by": request.current_user['username']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/parcels', methods=['GET'])
@verify_token_and_role()
def get_parcels():
    """取得包裹 - 需登入"""
    user = request.current_user
    
    # 客戶只能看自己的包裹
    if user['role'] == 'customer':
        criteria = {'sender_id': user['username']}
        return jsonify(package_mgr.search_packages(criteria))
    
    # staff 和 admin 可以看全部
    return jsonify(package_mgr.get_all())

@app.route('/api/parcels/search', methods=['POST'])
@verify_token_and_role()
def search_parcels():
    """搜尋包裹 - 需登入"""
    data = request.json
    user = request.current_user
    
    criteria = {}
    
    # 客戶只能搜尋自己的包裹
    if user['role'] == 'customer':
        criteria['sender_id'] = user['username']
    else:
        # staff 可以指定搜尋條件
        if 'sender_id' in data:
            criteria['sender_id'] = data['sender_id']
        if 'status' in data:
            criteria['status'] = data['status']
    
    results = package_mgr.search_packages(criteria)
    return jsonify(results)

if __name__ == '__main__':
    # 預先建立測試帳號
    users['admin'] = {
        "password_hash": hash_password("admin123"),
        "role": "admin"
    }
    users['staff1'] = {
        "password_hash": hash_password("staff123"),
        "role": "staff"
    }
    users['customer1'] = {
        "password_hash": hash_password("customer123"),
        "role": "customer"
    }
    
    print("🚀 物流系統後端啟動")
    print("📍 測試帳號:")
    print("   admin / admin123 (管理員)")
    print("   staff1 / staff123 (員工)")
    print("   customer1 / customer123 (客戶)")
    print("\n📋 API 文件:")
    print("   POST /api/auth/register - 註冊")
    print("   POST /api/auth/login - 登入")
    print("   POST /api/customers - 建立客戶(需staff)")
    print("   GET  /api/customers - 查詢客戶(需登入)")
    print("   POST /api/parcels - 建立包裹(需staff)")
    print("   GET  /api/parcels - 查詢包裹(需登入)")
    print("   POST /api/parcels/search - 搜尋包裹(需登入)")
    
    app.run(debug=True, host='0.0.0.0', port=5000)