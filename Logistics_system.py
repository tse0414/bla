"""
物流管理系統後端 - 主要模組
"""
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
import uuid


# ========== 枚舉類型 ==========
class CustomerType(Enum):
    """客戶類型"""
    CONTRACT = "合約"
    NON_CONTRACT = "非合約"
    PREPAID = "預付"


class BillingPreference(Enum):
    """帳單偏好"""
    MONTHLY = "月結"
    COD = "貨到付款"
    PREPAID = "預付"


class ServiceType(Enum):
    """服務類型"""
    STANDARD = "標準配送"
    EXPRESS = "快速配送"
    OVERNIGHT = "隔夜配送"
    INTERNATIONAL = "國際配送"


class PackageStatus(Enum):
    """包裹狀態"""
    CREATED = "已建立"
    PICKUP = "已取件"
    IN_TRANSIT = "運輸中"
    AT_FACILITY = "抵達物流中心"
    SORTING = "分揀中"
    OUT_FOR_DELIVERY = "外送中"
    DELIVERED = "已送達"
    EXCEPTION = "異常"


class SpecialMarker(Enum):
    """特殊標記"""
    DANGEROUS = "危險品"
    FRAGILE = "易碎品"
    INTERNATIONAL = "國際件"
    PERISHABLE = "易腐品"


class UserRole(Enum):
    """使用者角色"""
    CUSTOMER = "客戶"
    CUSTOMER_SERVICE = "客服人員"
    WAREHOUSE = "倉儲人員"
    DRIVER = "駕駛員"
    ADMIN = "管理員"


# ========== 資料模型 ==========
class Customer:
    """客戶資料模型"""
    def __init__(self, name: str, address: str, phone: str, email: str):
        self.customer_id = str(uuid.uuid4())
        self.name = name
        self.address = address
        self.phone = phone
        self.email = email
        self.customer_type = CustomerType.NON_CONTRACT
        self.billing_preference = BillingPreference.COD
        self.created_at = datetime.now()

    def set_customer_type(self, customer_type: CustomerType):
        """設定客戶類型"""
        self.customer_type = customer_type

    def set_billing_preference(self, preference: BillingPreference):
        """設定帳單偏好"""
        self.billing_preference = preference


class Package:
    """包裹資料模型"""
    def __init__(self, sender_id: str, recipient_name: str, recipient_address: str):
        self.tracking_number = self._generate_tracking_number()
        self.sender_id = sender_id
        self.recipient_name = recipient_name
        self.recipient_address = recipient_address
        self.weight = 0.0  # kg
        self.length = 0.0  # cm
        self.width = 0.0   # cm
        self.height = 0.0  # cm
        self.declared_value = 0.0
        self.content_description = ""
        self.service_type = ServiceType.STANDARD
        self.status = PackageStatus.CREATED
        self.special_markers: List[SpecialMarker] = []
        self.created_at = datetime.now()

    def _generate_tracking_number(self) -> str:
        """產生唯一追蹤編號"""
        return f"TRK{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"

    def set_attributes(self, weight: float, length: float, width: float, height: float, 
                      declared_value: float, description: str):
        """記錄包裹屬性"""
        self.weight = weight
        self.length = length
        self.width = width
        self.height = height
        self.declared_value = declared_value
        self.content_description = description

    def add_special_marker(self, marker: SpecialMarker):
        """新增特殊標記"""
        if marker not in self.special_markers:
            self.special_markers.append(marker)

    def calculate_volume_weight(self) -> float:
        """計算體積重量 (長x寬x高/5000)"""
        return (self.length * self.width * self.height) / 5000

    def to_dict(self):
        """將包裹物件轉換為字典，以便存成 JSON"""
        return {
            "tracking_number": self.tracking_number,
            "sender_id": self.sender_id,
            "recipient_name": self.recipient_name,
            "recipient_address": self.recipient_address,
            "weight": self.weight,
            "content_description": self.content_description,
            # Enum 需要轉成字串 (.value)
            "status": self.status.value, 
            "service_type": self.service_type.value,
            # 時間需要轉成字串
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

class TrackingEvent:
    """追蹤事件資料模型"""
    def __init__(self, tracking_number: str, status: PackageStatus, 
                 location: str, notes: str = ""):
        self.event_id = str(uuid.uuid4())
        self.tracking_number = tracking_number
        self.status = status
        self.location = location
        self.notes = notes
        self.timestamp = datetime.now()
        self.created_by = None  # 可記錄操作人員ID


class PricingRule:
    """定價規則"""
    def __init__(self, service_type: ServiceType, base_rate: float):
        self.service_type = service_type
        self.base_rate = base_rate  # 基本費率(每kg)
        self.additional_fees: Dict[str, float] = {}

    def add_additional_fee(self, fee_name: str, amount: float):
        """新增附加費用"""
        self.additional_fees[fee_name] = amount


# ========== 商業邏輯模組 ==========
class CustomerManager:
    """客戶管理模組"""
    def __init__(self):
        self.customers: Dict[str, Customer] = {}

    def create_customer(self, name: str, address: str, phone: str, email: str) -> Customer:
        """建立客戶檔案"""
        customer = Customer(name, address, phone, email)
        self.customers[customer.customer_id] = customer
        return customer

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """取得客戶資料"""
        return self.customers.get(customer_id)

    def update_customer_type(self, customer_id: str, customer_type: CustomerType) -> bool:
        """設定客戶類型"""
        customer = self.get_customer(customer_id)
        if customer:
            customer.set_customer_type(customer_type)
            return True
        return False

    def update_billing_preference(self, customer_id: str, preference: BillingPreference) -> bool:
        """設定帳單偏好"""
        customer = self.get_customer(customer_id)
        if customer:
            customer.set_billing_preference(preference)
            return True
        return False

'''
class PackageManager:
    """包裹管理模組"""
    def __init__(self):
        self.packages: Dict[str, Package] = {}
        self.pricing_rules: Dict[ServiceType, PricingRule] = {}
        self._initialize_pricing_rules()

    def _initialize_pricing_rules(self):
        """初始化定價規則"""
        self.pricing_rules[ServiceType.STANDARD] = PricingRule(ServiceType.STANDARD, 5.0)
        self.pricing_rules[ServiceType.EXPRESS] = PricingRule(ServiceType.EXPRESS, 8.0)
        self.pricing_rules[ServiceType.OVERNIGHT] = PricingRule(ServiceType.OVERNIGHT, 12.0)
        self.pricing_rules[ServiceType.INTERNATIONAL] = PricingRule(ServiceType.INTERNATIONAL, 15.0)
        
        # 設定附加費用
        for rule in self.pricing_rules.values():
            rule.add_additional_fee("危險品", 20.0)
            rule.add_additional_fee("易碎品", 10.0)
            rule.add_additional_fee("國際件", 30.0)

    def create_package(self, sender_id: str, recipient_name: str, 
                      recipient_address: str) -> Package:
        """建立包裹(產生追蹤編號)"""
        package = Package(sender_id, recipient_name, recipient_address)
        self.packages[package.tracking_number] = package
        return package

    def get_package(self, tracking_number: str) -> Optional[Package]:
        """取得包裹資料"""
        return self.packages.get(tracking_number)

    def update_package_attributes(self, tracking_number: str, weight: float, 
                                 length: float, width: float, height: float,
                                 declared_value: float, description: str) -> bool:
        """記錄包裹屬性"""
        package = self.get_package(tracking_number)
        if package:
            package.set_attributes(weight, length, width, height, declared_value, description)
            return True
        return False

    def add_special_marker(self, tracking_number: str, marker: SpecialMarker) -> bool:
        """管理特殊服務標記"""
        package = self.get_package(tracking_number)
        if package:
            package.add_special_marker(marker)
            return True
        return False

    def calculate_shipping_cost(self, tracking_number: str) -> Optional[float]:
        """計算包裹費用"""
        package = self.get_package(tracking_number)
        if not package:
            return None

        pricing_rule = self.pricing_rules.get(package.service_type)
        if not pricing_rule:
            return None

        # 計算重量費用(取實重與體積重較大者)
        chargeable_weight = max(package.weight, package.calculate_volume_weight())
        base_cost = chargeable_weight * pricing_rule.base_rate

        # 計算附加費用
        additional_cost = 0.0
        for marker in package.special_markers:
            if marker.value in pricing_rule.additional_fees:
                additional_cost += pricing_rule.additional_fees[marker.value]

        return base_cost + additional_cost
'''
import json
import os

class PackageManager:
    """包裹管理模組 (含 JSON 存檔功能)"""
    def __init__(self):
        self.packages: Dict[str, Package] = {}
        self.pricing_rules: Dict[ServiceType, PricingRule] = {}
        self._initialize_pricing_rules()
        
        # 設定檔案名稱
        self.db_file = "data_packages.json"
        # 啟動時自動讀取檔案
        self.load_data()

    def _initialize_pricing_rules(self):
        """初始化定價規則 (維持原樣)"""
        self.pricing_rules[ServiceType.STANDARD] = PricingRule(ServiceType.STANDARD, 5.0)
        self.pricing_rules[ServiceType.EXPRESS] = PricingRule(ServiceType.EXPRESS, 8.0)
        self.pricing_rules[ServiceType.OVERNIGHT] = PricingRule(ServiceType.OVERNIGHT, 12.0)
        self.pricing_rules[ServiceType.INTERNATIONAL] = PricingRule(ServiceType.INTERNATIONAL, 15.0)

    def save_data(self):
        """將所有包裹存入 JSON 檔案"""
        data_map = {}
        for tid, pkg in self.packages.items():
            data_map[tid] = pkg.to_dict()
        
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data_map, f, ensure_ascii=False, indent=4)
            print(f"資料已儲存：{len(self.packages)} 筆")
        except Exception as e:
            print(f"存檔失敗: {e}")

    def load_data(self):
        """從 JSON 檔案讀取包裹"""
        if not os.path.exists(self.db_file):
            return

        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data_loaded = json.load(f)

            for tid, item in data_loaded.items():
                # 重建物件
                pkg = Package(item['sender_id'], item['recipient_name'], item['recipient_address'])
                pkg.tracking_number = item['tracking_number']
                pkg.weight = item.get('weight', 0.0)
                pkg.content_description = item.get('content_description', '')
                
                # 還原 Enum (如果字串對應得到)
                try:
                    pkg.status = PackageStatus(item['status'])
                except:
                    pass # 保持預設

                # 還原時間
                try:
                    pkg.created_at = datetime.strptime(item['created_at'], "%Y-%m-%d %H:%M:%S")
                except:
                    pass

                self.packages[tid] = pkg
            print(f"成功載入歷史資料：{len(self.packages)} 筆")
        except Exception as e:
            print(f"讀檔失敗或檔案格式錯誤: {e}")

    def create_package(self, sender_id: str, recipient_name: str, 
                      recipient_address: str) -> Package:
        """建立包裹並立即存檔"""
        package = Package(sender_id, recipient_name, recipient_address)
        self.packages[package.tracking_number] = package
        
        # ★ 關鍵動作：建立完馬上存檔
        self.save_data()
        return package

    def get_package(self, tracking_number: str) -> Optional[Package]:
        return self.packages.get(tracking_number)

    def update_package_attributes(self, tracking_number: str, weight: float, 
                                 length: float, width: float, height: float,
                                 declared_value: float, description: str) -> bool:
        package = self.get_package(tracking_number)
        if package:
            package.set_attributes(weight, length, width, height, declared_value, description)
            # ★ 關鍵動作：更新完馬上存檔
            self.save_data()
            return True
        return False

    def add_special_marker(self, tracking_number: str, marker: SpecialMarker) -> bool:
        """管理特殊服務標記"""
        package = self.get_package(tracking_number)
        if package:
            package.add_special_marker(marker)
            return True
        return False

    def calculate_shipping_cost(self, tracking_number: str) -> Optional[float]:
        """計算包裹費用"""
        package = self.get_package(tracking_number)
        if not package:
            return None

        pricing_rule = self.pricing_rules.get(package.service_type)
        if not pricing_rule:
            return None

        # 計算重量費用(取實重與體積重較大者)
        chargeable_weight = max(package.weight, package.calculate_volume_weight())
        base_cost = chargeable_weight * pricing_rule.base_rate

        # 計算附加費用
        additional_cost = 0.0
        for marker in package.special_markers:
            if marker.value in pricing_rule.additional_fees:
                additional_cost += pricing_rule.additional_fees[marker.value]

        return base_cost + additional_cost
    # (原本的 add_special_marker 和 calculate_shipping_cost 維持原樣即可，不需要改)

class TrackingManager:
    """物流事件追蹤模組"""
    def __init__(self, package_manager: PackageManager):
        self.package_manager = package_manager
        self.tracking_events: Dict[str, List[TrackingEvent]] = {}

    def record_event(self, tracking_number: str, status: PackageStatus, 
                    location: str, notes: str = "") -> bool:
        """記錄追蹤事件"""
        package = self.package_manager.get_package(tracking_number)
        if not package:
            return False

        event = TrackingEvent(tracking_number, status, location, notes)
        
        if tracking_number not in self.tracking_events:
            self.tracking_events[tracking_number] = []
        
        self.tracking_events[tracking_number].append(event)
        package.status = status
        return True

    def start_tracking(self, tracking_number: str, location: str) -> bool:
        """啟動包裹追蹤"""
        return self.record_event(tracking_number, PackageStatus.PICKUP, location, "包裹已取件")

    def record_delivery(self, tracking_number: str, location: str, 
                       signature: str = "") -> bool:
        """記錄最終投遞與簽收"""
        notes = f"已送達，簽收人:{signature}" if signature else "已送達"
        return self.record_event(tracking_number, PackageStatus.DELIVERED, location, notes)

    def get_current_status(self, tracking_number: str) -> Optional[Dict]:
        """查詢包裹目前狀態"""
        events = self.tracking_events.get(tracking_number)
        if not events:
            return None

        latest_event = events[-1]
        return {
            "tracking_number": tracking_number,
            "status": latest_event.status.value,
            "location": latest_event.location,
            "timestamp": latest_event.timestamp,
            "notes": latest_event.notes
        }

    def get_tracking_history(self, tracking_number: str) -> List[Dict]:
        """查詢包裹歷史追蹤紀錄"""
        events = self.tracking_events.get(tracking_number, [])
        return [
            {
                "status": event.status.value,
                "location": event.location,
                "timestamp": event.timestamp,
                "notes": event.notes
            }
            for event in events
        ]


class BillingManager:
    """計費與帳單模組"""
    def __init__(self, package_manager: PackageManager, customer_manager: CustomerManager):
        self.package_manager = package_manager
        self.customer_manager = customer_manager
        self.billing_records: Dict[str, Dict] = {}

    def process_payment(self, tracking_number: str) -> Optional[Dict]:
        """付款處理"""
        package = self.package_manager.get_package(tracking_number)
        if not package:
            return None

        customer = self.customer_manager.get_customer(package.sender_id)
        if not customer:
            return None

        cost = self.package_manager.calculate_shipping_cost(tracking_number)
        if cost is None:
            return None

        billing_record = {
            "tracking_number": tracking_number,
            "customer_id": customer.customer_id,
            "amount": cost,
            "billing_preference": customer.billing_preference.value,
            "payment_status": "待付款",
            "created_at": datetime.now()
        }

        # 根據客戶類型處理付款
        if customer.customer_type == CustomerType.PREPAID:
            billing_record["payment_status"] = "已付款"
        elif customer.billing_preference == BillingPreference.COD:
            billing_record["payment_status"] = "貨到付款"

        self.billing_records[tracking_number] = billing_record
        return billing_record

    def get_customer_shipments(self, customer_id: str) -> List[Dict]:
        """列出帳戶貨件與費用"""
        shipments = []
        for tracking_number, record in self.billing_records.items():
            if record["customer_id"] == customer_id:
                shipments.append(record)
        return shipments


# ========== 權限控制模組 ==========
class AccessControlManager:
    """權限與安全模組"""
    def __init__(self):
        self.users: Dict[str, Dict] = {}

    def create_user(self, username: str, role: UserRole) -> str:
        """建立使用者"""
        user_id = str(uuid.uuid4())
        self.users[user_id] = {
            "username": username,
            "role": role,
            "created_at": datetime.now()
        }
        return user_id

    def check_permission(self, user_id: str, action: str) -> bool:
        """檢查權限"""
        user = self.users.get(user_id)
        if not user:
            return False

        role = user["role"]
        
        # 定義權限規則
        permissions = {
            UserRole.ADMIN: ["all"],
            UserRole.CUSTOMER_SERVICE: ["create_package", "view_package", "create_customer"],
            UserRole.WAREHOUSE: ["update_tracking", "add_marker", "view_package"],
            UserRole.DRIVER: ["update_tracking", "view_package"],
            UserRole.CUSTOMER: ["view_own_package"]
        }

        user_permissions = permissions.get(role, [])
        return "all" in user_permissions or action in user_permissions