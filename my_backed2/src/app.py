"""
物流管理系統後端 API - Flask 完整版
補足所有缺口：進階搜尋、月結報表、距離體積計費、權限控管
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
import uuid
import json
import os

app = Flask(__name__)
CORS(app)

# ========== 枚舉類型 ==========
class CustomerType(Enum):
    CONTRACT = "合約"
    NON_CONTRACT = "非合約"
    PREPAID = "預付"

class BillingPreference(Enum):
    MONTHLY = "月結"
    COD = "貨到付款"
    PREPAID = "預付"

class ServiceType(Enum):
    STANDARD = "標準配送"
    EXPRESS = "快速配送"
    OVERNIGHT = "隔夜配送"
    INTERNATIONAL = "國際配送"

class PackageStatus(Enum):
    CREATED = "已建立"
    PICKUP = "已取件"
    IN_TRANSIT = "運輸中"
    AT_FACILITY = "抵達物流中心"
    SORTING = "分揀中"
    OUT_FOR_DELIVERY = "外送中"
    DELIVERED = "已送達"
    EXCEPTION = "異常"

class SpecialMarker(Enum):
    DANGEROUS = "危險品"
    FRAGILE = "易碎品"
    INTERNATIONAL = "國際件"
    PERISHABLE = "易腐品"

class UserRole(Enum):
    CUSTOMER = "客戶"
    CUSTOMER_SERVICE = "客服人員"
    WAREHOUSE = "倉儲人員"
    DRIVER = "駕駛員"
    ADMIN = "管理員"

# ========== 資料模型 ==========
class Customer:
    def __init__(self, name: str, address: str, phone: str, email: str, account: str = None):
        self.customer_id = account if account else str(uuid.uuid4())
        self.name = name
        self.address = address
        self.phone = phone
        self.email = email
        self.customer_type = CustomerType.NON_CONTRACT
        self.billing_preference = BillingPreference.COD
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "type": self.customer_type.value,
            "billing_preference": self.billing_preference.value,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

class Package:
    def __init__(self, sender_id: str, recipient_name: str, recipient_address: str):
        self.tracking_number = self._generate_tracking_number()
        self.sender_id = sender_id
        self.recipient_name = recipient_name
        self.recipient_address = recipient_address
        self.weight = 0.0
        self.length = 0.0
        self.width = 0.0
        self.height = 0.0
        self.declared_value = 0.0
        self.content_description = ""
        self.service_type = ServiceType.STANDARD
        self.status = PackageStatus.CREATED
        self.special_markers: List[SpecialMarker] = []
        self.created_at = datetime.now()
        self.distance = 0.0
        self.location = ""

    def _generate_tracking_number(self) -> str:
        return f"TRK{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}"

    def set_attributes(self, weight: float, length: float, width: float, height: float,
                      declared_value: float, description: str, distance: float = 0.0):
        self.weight = weight
        self.length = length
        self.width = width
        self.height = height
        self.declared_value = declared_value
        self.content_description = description
        self.distance = distance

    def add_special_marker(self, marker: SpecialMarker):
        if marker not in self.special_markers:
            self.special_markers.append(marker)

    def calculate_volume_weight(self) -> float:
        return (self.length * self.width * self.height) / 5000
   
    def to_dict(self):
        return {
            "tracking_number": self.tracking_number,
            "sender_id": self.sender_id,
            "recipient_name": self.recipient_name,
            "recipient_address": self.recipient_address,
            "weight": self.weight,
            "distance": self.distance,
            "content_description": self.content_description,
            "status": self.status.value,
            "service_type": self.service_type.value,
            "location": self.location,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

class TrackingEvent:
    def __init__(self, tracking_number: str, status: PackageStatus, location: str, notes: str = ""):
        self.event_id = str(uuid.uuid4())
        self.tracking_number = tracking_number
        self.status = status
        self.location = location
        self.notes = notes
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "time": self.timestamp.strftime("%Y-%m-%d %H:%M"),
            "type": self.status.value,
            "location": self.location,
            "note": self.notes
        }

class PricingRule:
    def __init__(self, service_type: ServiceType, base_rate: float):
        self.service_type = service_type
        self.base_rate = base_rate
        self.additional_fees: Dict[str, float] = {}
        self.distance_rate = 2.0

    def add_additional_fee(self, fee_name: str, amount: float):
        self.additional_fees[fee_name] = amount

# ========== 管理器模組 ==========
class CustomerManager:
    def __init__(self):
        self.customers: Dict[str, Customer] = {}
        self.db_file = "data_customers.json"
        self.load_data()

    def save_data(self):
        data = {k: v.to_dict() for k, v in self.customers.items()}
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except: pass

    def load_data(self):
        if not os.path.exists(self.db_file): return
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in data.items():
                c = Customer(v['name'], v['address'], v['phone'], v['email'], v['customer_id'])
                try: c.customer_type = CustomerType(v['type'])
                except: pass
                try: c.created_at = datetime.strptime(v['created_at'], "%Y-%m-%d %H:%M:%S")
                except: pass
                self.customers[k] = c
        except: pass

    def create_customer(self, name: str, address: str, phone: str, email: str, account: str) -> Customer:
        customer = Customer(name, address, phone, email, account)
        self.customers[customer.customer_id] = customer
        self.save_data()
        return customer

    def get_all(self):
        return [c.to_dict() for c in self.customers.values()]
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self.customers.get(customer_id)

class PackageManager:
    def __init__(self):
        self.packages: Dict[str, Package] = {}
        self.pricing_rules: Dict[ServiceType, PricingRule] = {}
        self._initialize_pricing_rules()
        self.db_file = "data_packages.json"
        self.load_data()

    def _initialize_pricing_rules(self):
        self.pricing_rules[ServiceType.STANDARD] = PricingRule(ServiceType.STANDARD, 5.0)
        self.pricing_rules[ServiceType.EXPRESS] = PricingRule(ServiceType.EXPRESS, 8.0)
        self.pricing_rules[ServiceType.OVERNIGHT] = PricingRule(ServiceType.OVERNIGHT, 12.0)
       
    def save_data(self):
        data = {k: v.to_dict() for k, v in self.packages.items()}
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except: pass

    def load_data(self):
        if not os.path.exists(self.db_file): return
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in data.items():
                p = Package(v['sender_id'], v['recipient_name'], v['recipient_address'])
                p.tracking_number = v['tracking_number']
                p.weight = v.get('weight', 0)
                p.distance = v.get('distance', 0)
                p.content_description = v.get('content_description', '')
                p.location = v.get('location', '')
                try: p.status = PackageStatus(v['status'])
                except: pass
                try: p.service_type = ServiceType(v['service_type'])
                except: pass
                try: p.created_at = datetime.strptime(v['created_at'], "%Y-%m-%d %H:%M:%S")
                except: pass
                self.packages[k] = p
        except: pass

    def create_package(self, sender_id: str, recipient_name: str, recipient_address: str) -> Package:
        package = Package(sender_id, recipient_name, recipient_address)
        self.packages[package.tracking_number] = package
        self.save_data()
        return package

    def get_package(self, tracking_number: str) -> Optional[Package]:
        return self.packages.get(tracking_number)

    def get_all(self):
        return [p.to_dict() for p in self.packages.values()]

    def update_package_attributes(self, tracking_number: str, weight: float,
                                 length: float, width: float, height: float,
                                 declared_value: float, description: str, 
                                 distance: float = 0.0, service_type: str = None) -> bool:
        package = self.get_package(tracking_number)
        if package:
            package.set_attributes(weight, length, width, height, declared_value, description, distance)
            if service_type:
                try:
                    package.service_type = ServiceType(service_type)
                except: pass
            self.save_data()
            return True
        return False

    # ★ 缺口一：進階搜尋功能
    def search_packages(self, criteria: Dict) -> List[Dict]:
        results = []
        for pkg in self.packages.values():
            match = True
            
            # 依客戶帳號搜尋
            if 'sender_id' in criteria and criteria['sender_id']:
                if pkg.sender_id != criteria['sender_id']:
                    match = False
            
            # 依日期範圍搜尋
            if 'date_from' in criteria and criteria['date_from']:
                pkg_date = pkg.created_at.strftime("%Y-%m-%d")
                if pkg_date < criteria['date_from']:
                    match = False
            
            if 'date_to' in criteria and criteria['date_to']:
                pkg_date = pkg.created_at.strftime("%Y-%m-%d")
                if pkg_date > criteria['date_to']:
                    match = False
            
            # 依倉儲地點搜尋
            if 'location' in criteria and criteria['location']:
                if criteria['location'].lower() not in pkg.location.lower():
                    match = False
            
            # 依狀態搜尋
            if 'status' in criteria and criteria['status']:
                if pkg.status.value != criteria['status']:
                    match = False
           
            if match:
                results.append(pkg.to_dict())
        
        return results

    # ★ 缺口三：複雜計費 (距離 + 重量 + 體積)
    def calculate_cost(self, tracking_number: str) -> Dict:
        pkg = self.get_package(tracking_number)
        if not pkg:
            return {"error": "找不到包裹", "total": 0.0}
       
        rule = self.pricing_rules.get(pkg.service_type, self.pricing_rules[ServiceType.STANDARD])
       
        # 1. 重量計費 (取實重與材積重較大者)
        vol_weight = pkg.calculate_volume_weight()
        charge_weight = max(pkg.weight, vol_weight)
        weight_cost = charge_weight * rule.base_rate
       
        # 2. 距離計費
        dist_cost = pkg.distance * rule.distance_rate
        
        # 3. 基本費用
        base_cost = 50.0
       
        total = base_cost + weight_cost + dist_cost
        
        return {
            "tracking_number": tracking_number,
            "base_cost": round(base_cost, 2),
            "weight_cost": round(weight_cost, 2),
            "distance_cost": round(dist_cost, 2),
            "charge_weight": round(charge_weight, 2),
            "volume_weight": round(vol_weight, 2),
            "actual_weight": pkg.weight,
            "distance": pkg.distance,
            "total": round(total, 2)
        }

class TrackingManager:
    def __init__(self, package_manager: PackageManager):
        self.package_manager = package_manager
        self.tracking_events: Dict[str, List[TrackingEvent]] = {}
        self.db_file = "data_tracking.json"
        self.load_data()

    def save_data(self):
        data_to_save = {}
        for trk, events in self.tracking_events.items():
            data_to_save[trk] = [e.to_dict() for e in events]
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        except: pass

    def load_data(self):
        if not os.path.exists(self.db_file): return
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            for trk, events_list in raw_data.items():
                self.tracking_events[trk] = []
                for e in events_list:
                    status_enum = PackageStatus.CREATED
                    for s in PackageStatus:
                        if s.value == e['type']:
                            status_enum = s
                            break
                    evt = TrackingEvent(trk, status_enum, e['location'], e['note'])
                    evt.timestamp = datetime.strptime(e['time'], "%Y-%m-%d %H:%M")
                    self.tracking_events[trk].append(evt)
        except: pass

    def record_event(self, tracking_number: str, status: PackageStatus, location: str, notes: str = "") -> bool:
        package = self.package_manager.get_package(tracking_number)
        if not package: return False

        event = TrackingEvent(tracking_number, status, location, notes)
        if tracking_number not in self.tracking_events:
            self.tracking_events[tracking_number] = []
       
        self.tracking_events[tracking_number].append(event)
        package.status = status
        package.location = location
       
        self.save_data()
        self.package_manager.save_data()
        return True

    def get_tracking_history(self, tracking_number: str) -> List[Dict]:
        events = self.tracking_events.get(tracking_number, [])
        return [e.to_dict() for e in events]

class BillingManager:
    def __init__(self, package_manager: PackageManager):
        self.package_mgr = package_manager
        self.invoices = []
        self.db_file = "data_billing.json"
        self.load_data()

    def save_data(self):
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.invoices, f, ensure_ascii=False, indent=4)
        except: pass

    def load_data(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self.invoices = json.load(f)
            except: pass

    def create_invoice(self, customer_account, amount, method, status):
        record = {
            "id": str(uuid.uuid4()),
            "customerAccount": customer_account,
            "period": datetime.now().strftime("%Y-%m"),
            "amount": amount,
            "method": method,
            "status": status,
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        self.invoices.append(record)
        self.save_data()
        return True
   
    def get_all(self):
        return self.invoices

    # ★ 缺口二：產生月結報表
    def generate_monthly_report(self, customer_id: str, month_str: str) -> Dict:
        """
        產生月結報表
        month_str 格式: "2025-12"
        """
        total_amount = 0
        shipment_list = []
       
        for pkg in self.package_mgr.packages.values():
            if pkg.sender_id == customer_id:
                pkg_month = pkg.created_at.strftime("%Y-%m")
                if pkg_month == month_str:
                    cost_detail = self.package_mgr.calculate_cost(pkg.tracking_number)
                    cost = cost_detail.get('total', 0)
                    total_amount += cost
                    shipment_list.append({
                        "tracking_number": pkg.tracking_number,
                        "cost": cost,
                        "date": pkg.created_at.strftime("%Y-%m-%d"),
                        "recipient": pkg.recipient_name,
                        "status": pkg.status.value
                    })
       
        return {
            "customer_id": customer_id,
            "month": month_str,
            "total_amount": round(total_amount, 2),
            "shipment_count": len(shipment_list),
            "shipments": shipment_list
        }

# ========== 權限控管工具 ==========
def check_permission(required_role: str):
    """檢查使用者權限"""
    data = request.get_json() or {}
    current_role = data.get('current_role', 'customer')
    
    role_hierarchy = {
        'customer': 0,
        'staff': 1,
        'admin': 2
    }
    
    required_level = role_hierarchy.get(required_role, 2)
    current_level = role_hierarchy.get(current_role, 0)
    
    if current_level < required_level:
        return False, f"權限不足：需要 {required_role} 權限"
    
    return True, ""

# ========== 初始化管理器 ==========
customer_mgr = CustomerManager()
package_mgr = PackageManager()
tracking_mgr = TrackingManager(package_mgr)
billing_mgr = BillingManager(package_mgr)

# ========== API 路由 ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({"status": "ok", "message": "物流系統後端運行中"})

# ========== 客戶管理 API ==========
@app.route('/api/customers', methods=['POST'])
def create_customer():
    """建立客戶 (需要 staff 權限)"""
    has_perm, msg = check_permission('staff')
    if not has_perm:
        return jsonify({"error": msg}), 403
    
    data = request.json
    try:
        customer = customer_mgr.create_customer(
            name=data['name'],
            address=data['address'],
            phone=data['phone'],
            email=data['email'],
            account=data['account']
        )
        return jsonify({"success": True, "customer": customer.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/customers', methods=['GET'])
def get_customers():
    """取得所有客戶"""
    return jsonify(customer_mgr.get_all())

@app.route('/api/customers/<customer_id>', methods=['GET'])
def get_customer(customer_id):
    """取得單一客戶"""
    customer = customer_mgr.get_customer(customer_id)
    if customer:
        return jsonify(customer.to_dict())
    return jsonify({"error": "找不到客戶"}), 404

# ========== 包裹管理 API ==========
@app.route('/api/parcels', methods=['POST'])
def create_parcel():
    """建立包裹 (需要 staff 權限)"""
    has_perm, msg = check_permission('staff')
    if not has_perm:
        return jsonify({"error": msg}), 403
    
    data = request.json
    try:
        package = package_mgr.create_package(
            sender_id=data['sender_id'],
            recipient_name=data['recipient_name'],
            recipient_address=data['recipient_address']
        )
        
        # 更新包裹屬性
        if 'weight' in data:
            package_mgr.update_package_attributes(
                tracking_number=package.tracking_number,
                weight=float(data.get('weight', 0)),
                length=float(data.get('length', 0)),
                width=float(data.get('width', 0)),
                height=float(data.get('height', 0)),
                declared_value=float(data.get('declared_value', 0)),
                description=data.get('content_description', ''),
                distance=float(data.get('distance', 0)),
                service_type=data.get('service_type')
            )
        
        return jsonify({"success": True, "package": package.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/parcels', methods=['GET'])
def get_parcels():
    """取得所有包裹"""
    return jsonify(package_mgr.get_all())

@app.route('/api/parcels/<tracking_number>', methods=['GET'])
def get_parcel(tracking_number):
    """取得單一包裹"""
    package = package_mgr.get_package(tracking_number)
    if package:
        return jsonify(package.to_dict())
    return jsonify({"error": "找不到包裹"}), 404

# ★ 缺口一：進階搜尋 API
@app.route('/api/parcels/search', methods=['POST'])
def search_parcels():
    """進階搜尋包裹"""
    data = request.json
    criteria = {
        'sender_id': data.get('sender_id'),
        'date_from': data.get('date_from'),
        'date_to': data.get('date_to'),
        'location': data.get('location'),
        'status': data.get('status')
    }
    
    # 客戶只能搜尋自己的包裹
    current_role = data.get('current_role', 'customer')
    if current_role == 'customer':
        criteria['sender_id'] = data.get('customer_id')
    
    results = package_mgr.search_packages(criteria)
    return jsonify(results)

# ========== 追蹤管理 API ==========
@app.route('/api/tracking/<tracking_number>', methods=['GET'])
def get_tracking(tracking_number):
    """查詢包裹追蹤"""
    package = package_mgr.get_package(tracking_number)
    if not package:
        return jsonify({"error": "找不到包裹"}), 404
    
    events = tracking_mgr.get_tracking_history(tracking_number)
    return jsonify({
        "package": package.to_dict(),
        "events": events
    })

@app.route('/api/tracking/event', methods=['POST'])
def add_tracking_event():
    """新增追蹤事件 (需要 staff 權限)"""
    has_perm, msg = check_permission('staff')
    if not has_perm:
        return jsonify({"error": msg}), 403
    
    data = request.json
    try:
        status = PackageStatus(data['status'])
        success = tracking_mgr.record_event(
            tracking_number=data['tracking_number'],
            status=status,
            location=data['location'],
            notes=data.get('notes', '')
        )
        
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "更新失敗"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ========== 計費管理 API ==========
@app.route('/api/billing/calculate/<tracking_number>', methods=['GET'])
def calculate_cost(tracking_number):
    """計算包裹運費"""
    cost_detail = package_mgr.calculate_cost(tracking_number)
    return jsonify(cost_detail)

# ★ 缺口二：月結報表 API
@app.route('/api/billing/monthly-report', methods=['POST'])
def monthly_report():
    """產生月結報表 (需要 staff 權限)"""
    has_perm, msg = check_permission('staff')
    if not has_perm:
        return jsonify({"error": msg}), 403
    
    data = request.json
    report = billing_mgr.generate_monthly_report(
        customer_id=data['customer_id'],
        month_str=data['month']
    )
    return jsonify(report)

@app.route('/api/billing/invoice', methods=['POST'])
def create_invoice():
    """建立帳單 (需要 staff 權限)"""
    has_perm, msg = check_permission('staff')
    if not has_perm:
        return jsonify({"error": msg}), 403
    
    data = request.json
    billing_mgr.create_invoice(
        customer_account=data['customer_account'],
        amount=data['amount'],
        method=data.get('method', '月結'),
        status=data.get('status', '未付款')
    )
    return jsonify({"success": True})

@app.route('/api/billing/invoices', methods=['GET'])
def get_invoices():
    """取得所有帳單"""
    return jsonify(billing_mgr.get_all())

# ========== 錯誤處理 ==========
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "API 路徑不存在"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "伺服器錯誤"}), 500

if __name__ == '__main__':
    print("🚀 物流系統後端啟動中...")
    print("📍 API 位址: http://localhost:5000")
    print("📋 API 文件:")
    print("   - GET  /api/health")
    print("   - POST /api/customers")
    print("   - GET  /api/customers")
    print("   - POST /api/parcels")
    print("   - GET  /api/parcels")
    print("   - POST /api/parcels/search")
    print("   - GET  /api/tracking/<tracking_number>")
    print("   - POST /api/tracking/event")
    print("   - GET  /api/billing/calculate/<tracking_number>")
    print("   - POST /api/billing/monthly-report")
    print("   - POST /api/billing/invoice")
    print("   - GET  /api/billing/invoices")
    app.run(debug=True, host='0.0.0.0', port=5000)