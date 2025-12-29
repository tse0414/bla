"""
包裹追蹤與計費系統 - 完整測試套件
目標：達到近 100% 代碼覆蓋率
涵蓋所有功能性需求 (1.1-1.6) 與非功能性需求 (2.1-2.5)
"""

import pytest
import json
from datetime import datetime, timedelta
from app import app, SECRET_KEY, init_default_accounts
import jwt
import io

# ========================================
# Fixtures - 測試前置作業
# ========================================

@pytest.fixture(scope='function')
def client():
    """建立測試客戶端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        init_default_accounts()  # 確保預設帳號存在
        yield client

@pytest.fixture
def admin_token():
    """生成管理員 Token"""
    return jwt.encode(
        {"username": "admin1", "role": "admin", "exp": datetime.utcnow() + timedelta(hours=4)},
        SECRET_KEY, algorithm="HS256"
    )

@pytest.fixture
def staff_token():
    """生成作業人員 Token"""
    return jwt.encode(
        {"username": "staff1", "role": "staff", "exp": datetime.utcnow() + timedelta(hours=4)},
        SECRET_KEY, algorithm="HS256"
    )

@pytest.fixture
def driver_token():
    """生成司機 Token"""
    return jwt.encode(
        {"username": "driver1", "role": "driver", "exp": datetime.utcnow() + timedelta(hours=4)},
        SECRET_KEY, algorithm="HS256"
    )

@pytest.fixture
def warehouse_token():
    """生成倉儲人員 Token"""
    return jwt.encode(
        {"username": "warehouse1", "role": "warehouse", "exp": datetime.utcnow() + timedelta(hours=4)},
        SECRET_KEY, algorithm="HS256"
    )

@pytest.fixture
def customer_token():
    """生成客戶 Token"""
    return jwt.encode(
        {"username": "test1", "role": "customer", "exp": datetime.utcnow() + timedelta(hours=4)},
        SECRET_KEY, algorithm="HS256"
    )

@pytest.fixture
def test_parcel(client, admin_token):
    """建立測試用包裹並返回追蹤編號"""
    response = client.post('/api/parcels',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={
            "sender_id": "admin1",
            "recipient_name": "測試收件人",
            "recipient_address": "台北市信義區信義路五段7號",
            "weight": 5.5,
            "volume": "30x20x15",
            "package_type": "中型箱",
            "declared_value": 1000,
            "contents": "電子產品",
            "service_type": "標準速遞"
        }
    )
    return json.loads(response.data)['tracking_no']


# ========================================
# 測試類別 1: 認證與授權 (需求 1.6, 2.4)
# ========================================

class TestAuthentication:
    """測試登入、註冊與身份驗證功能"""
    
    def test_login_success_admin(self, client):
        """測試管理員成功登入"""
        response = client.post('/api/auth/login', 
            json={"username": "admin1", "password": "admin123"}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == '登入成功'
        assert data['role'] == 'admin'
        assert data['username'] == 'admin1'
        assert 'token' in data
    
    def test_login_success_staff(self, client):
        """測試作業人員成功登入"""
        response = client.post('/api/auth/login',
            json={"username": "staff1", "password": "staff123"}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['role'] == 'staff'
    
    def test_login_success_driver(self, client):
        """測試司機成功登入"""
        response = client.post('/api/auth/login',
            json={"username": "driver1", "password": "driver123"}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['role'] == 'driver'
    
    def test_login_success_warehouse(self, client):
        """測試倉儲人員成功登入"""
        response = client.post('/api/auth/login',
            json={"username": "warehouse1", "password": "warehouse123"}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['role'] == 'warehouse'
    
    def test_login_success_customer(self, client):
        """測試客戶成功登入"""
        response = client.post('/api/auth/login',
            json={"username": "test1", "password": "test123"}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['role'] == 'customer'
    
    def test_login_wrong_password(self, client):
        """測試錯誤密碼 (需求 2.4: 身份驗證)"""
        response = client.post('/api/auth/login',
            json={"username": "admin1", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == '密碼錯誤'
    
    def test_login_nonexistent_user(self, client):
        """測試不存在的帳號"""
        response = client.post('/api/auth/login',
            json={"username": "nonexistent999", "password": "anything"}
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == '帳號不存在'
    
    def test_login_missing_username(self, client):
        """測試缺少帳號"""
        response = client.post('/api/auth/login',
            json={"password": "test123"}
        )
        assert response.status_code == 400
    
    def test_login_missing_password(self, client):
        """測試缺少密碼"""
        response = client.post('/api/auth/login',
            json={"username": "admin1"}
        )
        assert response.status_code == 400
    
    def test_login_empty_json(self, client):
        """測試空的 JSON"""
        response = client.post('/api/auth/login', json={})
        assert response.status_code == 400
    
    def test_register_success(self, client):
        """測試成功註冊 (需求 1.1: 客戶管理)"""
        unique_username = f"newuser_{datetime.now().microsecond}"
        response = client.post('/api/auth/register',
            json={
                "username": unique_username,
                "password": "newpass123",
                "name": "新註冊用戶",
                "phone": "0912345678",
                "email": "new@example.com",
                "address": "台北市大安區",
                "customer_type": "NON_CONTRACT",
                "billing_preference": "COD"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == '註冊成功'
        assert data['username'] == unique_username
    
    def test_register_contract_customer(self, client):
        """測試註冊合約客戶 (需求 1.1: 合約客戶)"""
        unique_username = f"contract_{datetime.now().microsecond}"
        response = client.post('/api/auth/register',
            json={
                "username": unique_username,
                "password": "pass123",
                "name": "合約客戶",
                "customer_type": "CONTRACT",
                "billing_preference": "MONTHLY"
            }
        )
        assert response.status_code == 200
    
    def test_register_prepaid_customer(self, client):
        """測試註冊預付客戶 (需求 1.1: 預付客戶)"""
        unique_username = f"prepaid_{datetime.now().microsecond}"
        response = client.post('/api/auth/register',
            json={
                "username": unique_username,
                "password": "pass123",
                "name": "預付客戶",
                "customer_type": "PREPAID",
                "billing_preference": "PREPAID"
            }
        )
        assert response.status_code == 200
    
    def test_register_duplicate_username(self, client):
        """測試重複帳號註冊"""
        response = client.post('/api/auth/register',
            json={"username": "admin1", "password": "test123"}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert '已存在' in data['error']
    
    def test_register_missing_credentials(self, client):
        """測試缺少必要資訊"""
        response = client.post('/api/auth/register', json={})
        assert response.status_code == 400


# ========================================
# 測試類別 2: 客戶管理 (需求 1.1)
# ========================================

class TestCustomerManagement:
    """測試客戶資料的完整 CRUD 操作"""
    
    def test_create_customer_as_staff(self, client, staff_token):
        """測試作業人員建立客戶"""
        unique_account = f"cust_{datetime.now().microsecond}"
        response = client.post('/api/customers',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={
                "account": unique_account,
                "name": "新建客戶",
                "phone": "0987654321",
                "email": "customer@test.com",
                "address": "高雄市前鎮區",
                "customer_type": "NON_CONTRACT",
                "billing_preference": "COD"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert '已建立' in data['message']
    
    def test_create_customer_as_admin(self, client, admin_token):
        """測試管理員建立客戶"""
        unique_account = f"admin_cust_{datetime.now().microsecond}"
        response = client.post('/api/customers',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "account": unique_account,
                "name": "管理員建立的客戶"
            }
        )
        assert response.status_code == 200
    
    def test_create_customer_unauthorized(self, client, customer_token):
        """測試客戶無法建立客戶 (需求 1.6: 權限控制)"""
        response = client.post('/api/customers',
            headers={'Authorization': f'Bearer {customer_token}'},
            json={"account": "test", "name": "Test"}
        )
        assert response.status_code == 403
    
    def test_list_customers_as_admin(self, client, admin_token):
        """測試管理員查看所有客戶"""
        response = client.get('/api/customers',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_list_customers_as_staff(self, client, staff_token):
        """測試作業人員查看客戶列表"""
        response = client.get('/api/customers',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        assert response.status_code == 200
    
    def test_list_customers_as_customer_forbidden(self, client, customer_token):
        """測試客戶無法查看客戶列表"""
        response = client.get('/api/customers',
            headers={'Authorization': f'Bearer {customer_token}'}
        )
        assert response.status_code == 403
    
    def test_list_customers_as_driver_forbidden(self, client, driver_token):
        """測試司機無法查看客戶列表"""
        response = client.get('/api/customers',
            headers={'Authorization': f'Bearer {driver_token}'}
        )
        assert response.status_code == 403
    
    def test_update_customer_as_admin(self, client, admin_token):
        """測試管理員更新客戶資料"""
        response = client.put('/api/customers/test1',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "name": "更新後的名稱",
                "phone": "0911222333",
                "email": "updated@test.com"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert '已更新' in data['message']
    
    def test_update_customer_as_staff(self, client, staff_token):
        """測試作業人員更新客戶資料"""
        response = client.put('/api/customers/test1',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={"name": "作業人員更新"}
        )
        assert response.status_code == 200
    
    def test_update_customer_unauthorized(self, client, customer_token):
        """測試客戶無法更新其他客戶資料"""
        response = client.put('/api/customers/test1',
            headers={'Authorization': f'Bearer {customer_token}'},
            json={"name": "Unauthorized"}
        )
        assert response.status_code == 403


# ========================================
# 測試類別 3: 包裹建立與屬性 (需求 1.2, 1.3)
# ========================================

class TestParcelCreation:
    """測試包裹建立與各種屬性驗證"""
    
    def test_create_parcel_full_details(self, client, admin_token):
        """測試建立包含完整資訊的包裹 (需求 1.3: 包裹屬性)"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "王小明",
                "recipient_address": "台中市西屯區台灣大道三段99號",
                "weight": 12.5,
                "volume": "50x40x30",
                "package_type": "大型箱",
                "declared_value": 5000,
                "contents": "家用電器",
                "service_type": "隔夜達"
            }
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['message'] == '包裹建立成功'
        assert 'tracking_no' in data
        assert data['tracking_no'].startswith('TRK-')
        package = data['package']
        assert package['weight'] == 12.5
        assert package['package_type'] == '大型箱'
        assert package['service_type'] == '隔夜達'
    
    def test_create_parcel_small_box(self, client, admin_token):
        """測試建立小型箱包裹 (需求 1.2: 包裹類型)"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "李小姐",
                "weight": 0.5,
                "package_type": "小型箱",
                "service_type": "經濟速遞"
            }
        )
        assert response.status_code == 201
    
    def test_create_parcel_envelope(self, client, admin_token):
        """測試建立平郵信封 (需求 1.2: 平郵信封)"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "陳先生",
                "weight": 0.1,
                "package_type": "平郵信封",
                "service_type": "標準速遞"
            }
        )
        assert response.status_code == 201
    
    def test_create_parcel_overnight_delivery(self, client, admin_token):
        """測試隔夜達服務 (需求 1.2: 配送時效)"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "張經理",
                "weight": 3.0,
                "service_type": "隔夜達"
            }
        )
        assert response.status_code == 201
    
    def test_create_parcel_two_day_delivery(self, client, admin_token):
        """測試兩日達服務"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "林小姐",
                "weight": 2.5,
                "service_type": "兩日達"
            }
        )
        assert response.status_code == 201
    
    def test_create_parcel_minimal_info(self, client, staff_token):
        """測試最少必要資訊建立包裹"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={
                "sender_id": "staff1",
                "recipient_name": "收件人",
                "weight": 1.0
            }
        )
        assert response.status_code == 201
    
    def test_create_parcel_invalid_weight_negative(self, client, admin_token):
        """測試負重量 (需求驗證: 資料正確性)"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "Test",
                "weight": -5.0
            }
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert '重量' in data['error']
    
    def test_create_parcel_zero_weight(self, client, admin_token):
        """測試零重量"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "Test",
                "weight": 0
            }
        )
        assert response.status_code == 400
    
    def test_create_parcel_invalid_weight_string(self, client, admin_token):
        """測試非數字重量"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "Test",
                "weight": "invalid"
            }
        )
        assert response.status_code == 400
    
    def test_create_parcel_negative_volume(self, client, admin_token):
        """測試負體積"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "Test",
                "weight": 1.0,
                "volume": -100
            }
        )
        assert response.status_code == 400
    
    def test_create_parcel_missing_sender(self, client, admin_token):
        """測試缺少寄件人"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "recipient_name": "Test",
                "weight": 1.0
            }
        )
        # 系統會自動使用當前用戶作為寄件人
        assert response.status_code == 201
    
    def test_create_parcel_missing_recipient(self, client, admin_token):
        """測試缺少收件人"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "weight": 1.0
            }
        )
        assert response.status_code == 400
    
    def test_create_parcel_unauthorized(self, client):
        """測試未授權建立包裹"""
        response = client.post('/api/parcels',
            json={"sender_id": "test", "recipient_name": "Test", "weight": 1.0}
        )
        assert response.status_code == 401


# ========================================
# 測試類別 4: 計費與付款 (需求 1.5)
# ========================================

class TestBillingAndPayment:
    """測試計費功能與多種付款方式"""
    
    def test_set_amount_cash_payment(self, client, admin_token, test_parcel):
        """測試現金付款 (需求 1.5: 付款方式)"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 150.0,
                "payment_method": "cash"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['amount'] == 150.0
        assert '貨到付款' in data['payment_status']
    
    def test_set_amount_cod_payment(self, client, admin_token, test_parcel):
        """測試貨到付款 (需求 1.1, 1.5: 非合約客戶)"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 200.0,
                "payment_method": "cod"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert '貨到付款' in data['payment_status']
    
    def test_set_amount_monthly_billing(self, client, admin_token, test_parcel):
        """測試月結帳單 (需求 1.1, 1.5: 合約客戶)"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 180.0,
                "payment_method": "monthly"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['amount'] == 180.0
        assert '月結帳單' in data['payment_status']
    
    def test_set_amount_prepaid(self, client, admin_token, test_parcel):
        """測試預付款 (需求 1.1, 1.5: 預付客戶)"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 120.0,
                "payment_method": "prepaid"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert '預付' in data['payment_status']
    
    def test_set_amount_online_payment(self, client, admin_token, test_parcel):
        """測試線上付款"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 250.0,
                "payment_method": "online"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert '線上' in data['payment_status']
    
    def test_set_amount_with_service_type_update(self, client, admin_token, test_parcel):
        """測試同時更新金額與服務類型 (需求 1.2, 1.5)"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 300.0,
                "payment_method": "cash",
                "service_type": "隔夜達"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['service_type'] == '隔夜達'
    
    def test_set_amount_missing_tracking(self, client, admin_token):
        """測試缺少追蹤編號"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={"amount": 100.0}
        )
        assert response.status_code == 400
    
    def test_set_amount_missing_amount(self, client, admin_token, test_parcel):
        """測試缺少金額"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={"tracking_number": test_parcel}
        )
        assert response.status_code == 400
    
    def test_set_amount_negative(self, client, admin_token, test_parcel):
        """測試負數金額"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": -50.0
            }
        )
        assert response.status_code == 400
    
    def test_set_amount_invalid_format(self, client, admin_token, test_parcel):
        """測試無效金額格式"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": "invalid"
            }
        )
        assert response.status_code == 400
    
    def test_set_amount_nonexistent_parcel(self, client, admin_token):
        """測試不存在的包裹"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": "TRK-NONEXISTENT-9999",
                "amount": 100.0
            }
        )
        assert response.status_code == 404


# ========================================
# 測試類別 5: 追蹤與物流 (需求 1.4)
# ========================================

class TestTrackingAndLogistics:
    """測試包裹追蹤與狀態更新"""
    
    def test_update_status_received(self, client, warehouse_token, test_parcel):
        """測試已收件狀態 (需求 1.4: 起運地收件)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {warehouse_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "已收件",
                "location": "台北倉儲中心",
                "warehouse_id": "WH-TPE-001"
            }
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == '已收件'
    
    def test_update_status_warehouse(self, client, warehouse_token, test_parcel):
        """測試進入倉儲 (需求 1.4: 進出倉儲)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {warehouse_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "進入倉儲",
                "location": "高雄物流中心",
                "warehouse_id": "WH-KHH-002"
            }
        )
        assert response.status_code == 200
    
    def test_update_status_loaded(self, client, warehouse_token, test_parcel):
        """測試已裝車 (需求 1.4: 進出貨車)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {warehouse_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "已裝車",
                "location": "台中轉運站",
                "vehicle_id": "VEH-TC-101"
            }
        )
        assert response.status_code == 200
    
    def test_update_status_in_transit(self, client, driver_token, test_parcel):
        """測試配送中 (需求 1.4: 外送狀態)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {driver_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "配送中",
                "location": "台南市區",
                "vehicle_id": "VEH-TN-202",
                "description": "司機正在配送中"
            }
        )
        assert response.status_code == 200
    
    def test_update_status_delivered(self, client, driver_token, test_parcel):
        """測試已送達 (需求 1.4: 最終投遞與簽收)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {driver_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "已送達",
                "location": "收件人地址",
                "description": "已由本人簽收"
            }
        )
        assert response.status_code == 200
    
    def test_update_status_delayed(self, client, driver_token, test_parcel):
        """測試延誤狀態 (需求 1.4: 異常追蹤)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {driver_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "延誤",
                "location": "交通壅塞區域",
                "description": "因交通事故延誤"
            }
        )
        assert response.status_code == 200
    
    def test_update_status_lost(self, client, driver_token, test_parcel):
        """測試遺失狀態 (需求 1.4: 遺失包裹)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {driver_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "遺失",
                "location": "未知",
                "description": "包裹遺失,正在調查"
            }
        )
        assert response.status_code == 200
    
    def test_update_status_damaged(self, client, driver_token, test_parcel):
        """測試損毀狀態 (需求 1.4: 損毀)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {driver_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "損毀",
                "location": "倉儲中心",
                "description": "包裝破損"
            }
        )
        assert response.status_code == 200
    
    def test_update_status_returned(self, client, warehouse_token, test_parcel):
        """測試退回狀態"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {warehouse_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "退回",
                "location": "原倉儲",
                "description": "無法聯繫收件人"
            }
        )
        assert response.status_code == 200
    
    def test_get_parcel_history(self, client, admin_token, test_parcel):
        """測試查詢包裹歷史 (需求 1.4: 歷史追蹤查詢)"""
        response = client.get(f'/api/parcels/{test_parcel}/history',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'events' in data
        assert data['tracking_number'] == test_parcel
        assert len(data['events']) > 0
    
    def test_get_parcel_history_nonexistent(self, client, admin_token):
        """測試查詢不存在的包裹歷史"""
        response = client.get('/api/parcels/TRK-FAKE-9999/history',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['events'] == []
    
    def test_search_by_vehicle(self, client, admin_token):
        """測試依車輛搜尋 (需求 1.4: 運輸載具識別碼)"""
        response = client.get('/records?vehicle_id=VEH-TC-101',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200
    
    def test_search_by_warehouse(self, client, admin_token):
        """測試依倉儲搜尋 (需求 1.4: 倉儲地點)"""
        response = client.get('/records?warehouse_id=WH-TPE-001',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200
    
    def test_customer_cannot_update_status(self, client, customer_token, test_parcel):
        """測試客戶無法更新狀態 (需求 1.6: 權限控制)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {customer_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "已送達"
            }
        )
        assert response.status_code == 403
    
    def test_update_status_missing_data(self, client, admin_token):
        """測試缺少必要資料"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={}
        )
        assert response.status_code == 400
    
    def test_update_status_nonexistent_parcel(self, client, admin_token):
        """測試更新不存在的包裹狀態"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": "TRK-FAKE-0000",
                "status": "配送中"
            }
        )
        assert response.status_code == 404


# ========================================
# 測試類別 6: 角色權限與異常鎖定 (需求 1.6)
# ========================================

class TestRolePermissions:
    """測試不同角色的權限控制"""
    
    def test_driver_allowed_statuses(self, client, driver_token, admin_token):
        """測試司機允許的狀態變更 - 修正版"""
        allowed_statuses = ["已裝車", "配送中", "已送達", "延誤", "遺失", "損毀"]
        
        for status in allowed_statuses:
            # === 關鍵修正：每次都建立一個全新的包裹 ===
            create_resp = client.post('/api/parcels',
                headers={'Authorization': f'Bearer {admin_token}'},
                json={
                    "sender_id": "admin1",
                    "recipient_name": f"測試_{status}",
                    "weight": 1.0,
                    "service_type": "標準速遞"
                }
            )
            tracking_no = json.loads(create_resp.data)['tracking_no']
            # ==========================================

            response = client.post('/api/parcels/status',
                headers={'Authorization': f'Bearer {driver_token}'},
                json={
                    "tracking_number": tracking_no,
                    "status": status,
                    "location": "測試地點",
                    "description": f"狀態變更為{status}"
                }
            )
            assert response.status_code == 200, f"司機無法更新狀態為: {status}"
    
    def test_driver_forbidden_status(self, client, driver_token, test_parcel):
        """測試司機無法執行的狀態 (需求 1.6: 角色限制)"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {driver_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "進入倉儲"
            }
        )
        assert response.status_code == 403
    
    def test_warehouse_allowed_statuses(self, client, warehouse_token, admin_token):
        """測試倉儲人員允許的狀態 - 修正版"""
        allowed_statuses = ["已收件", "進入倉儲", "已裝車", "退回", "損毀"]
        
        for status in allowed_statuses:
            # === 關鍵修正：每次都建立一個全新的包裹 ===
            create_resp = client.post('/api/parcels',
                headers={'Authorization': f'Bearer {admin_token}'},
                json={
                    "sender_id": "admin1",
                    "recipient_name": f"倉儲測試_{status}",
                    "weight": 1.0
                }
            )
            tracking_no = json.loads(create_resp.data)['tracking_no']
            # ==========================================
            
            response = client.post('/api/parcels/status',
                headers={'Authorization': f'Bearer {warehouse_token}'},
                json={
                    "tracking_number": tracking_no,
                    "status": status,
                    "warehouse_id": "WH-TEST",
                    "location": "測試倉儲"
                }
            )
            assert response.status_code == 200, f"倉儲人員無法更新狀態為: {status}"
    
    def test_warehouse_forbidden_status(self, client, warehouse_token, test_parcel):
        """測試倉儲人員無法執行的狀態"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {warehouse_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "配送中"
            }
        )
        assert response.status_code == 403
    
    def test_abnormal_status_lock_non_admin(self, client, staff_token, test_parcel):
        """測試異常狀態鎖定 - 非管理員無法更新 (需求 1.4: 異常追蹤)"""
        # 先設為遺失狀態
        client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "遺失"
            }
        )
        
        # 嘗試更新為其他狀態
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "配送中"
            }
        )
        assert response.status_code == 400
    
    def test_abnormal_status_admin_can_update(self, client, admin_token, test_parcel):
        """測試管理員可以更新異常狀態包裹"""
        # 先設為損毀
        client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "損毀"
            }
        )
        
        # 管理員可以更新
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "處理中"
            }
        )
        assert response.status_code == 200


# ========================================
# 測試類別 7: 查詢與搜尋 (需求 1.4)
# ========================================

class TestSearchAndQuery:
    """測試各種查詢與搜尋功能"""
    
    def test_list_all_records_as_admin(self, client, admin_token):
        """測試管理員查看所有記錄 (需求 1.4: 查詢功能)"""
        response = client.get('/records',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_list_records_as_customer_filtered(self, client, customer_token):
        """測試客戶只能看到自己的包裹 (需求 1.6: 客戶權限)"""
        response = client.get('/records',
            headers={'Authorization': f'Bearer {customer_token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        for record in data:
            assert record['sender_id'] == 'test1'
    
    def test_list_records_staff(self, client, staff_token):
        """測試作業人員查看記錄"""
        response = client.get('/records',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        assert response.status_code == 200
    
    def test_list_records_driver(self, client, driver_token):
        """測試司機查看記錄"""
        response = client.get('/records',
            headers={'Authorization': f'Bearer {driver_token}'}
        )
        assert response.status_code == 200
    
    def test_list_records_warehouse(self, client, warehouse_token):
        """測試倉儲人員查看記錄"""
        response = client.get('/records',
            headers={'Authorization': f'Bearer {warehouse_token}'}
        )
        assert response.status_code == 200


# ========================================
# 測試類別 8: 刪除功能 (需求 1.6)
# ========================================

class TestDeletion:
    """測試刪除功能與權限"""
    
    def test_delete_parcel_as_admin(self, client, admin_token):
        """測試管理員刪除包裹"""
        # 建立測試包裹
        create_resp = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "待刪除",
                "weight": 1.0
            }
        )
        tracking_no = json.loads(create_resp.data)['tracking_no']
        
        # 刪除
        del_resp = client.delete(f'/api/parcels/{tracking_no}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert del_resp.status_code == 200
    
    def test_delete_parcel_as_staff(self, client, staff_token):
        """測試作業人員刪除包裹"""
        # 建立
        create_resp = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={
                "sender_id": "staff1",
                "recipient_name": "測試",
                "weight": 1.0
            }
        )
        tracking_no = json.loads(create_resp.data)['tracking_no']
        
        # 刪除
        del_resp = client.delete(f'/api/parcels/{tracking_no}',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        assert del_resp.status_code == 200
    
    def test_delete_parcel_as_customer_forbidden(self, client, customer_token):
        """測試客戶無法刪除包裹"""
        response = client.delete('/api/parcels/TRK-TEST-0001',
            headers={'Authorization': f'Bearer {customer_token}'}
        )
        assert response.status_code == 403
    
    def test_delete_parcel_as_driver_forbidden(self, client, driver_token):
        """測試司機無法刪除包裹"""
        response = client.delete('/api/parcels/TRK-TEST-0001',
            headers={'Authorization': f'Bearer {driver_token}'}
        )
        assert response.status_code == 403
    
    def test_delete_nonexistent_parcel(self, client, admin_token):
        """測試刪除不存在的包裹"""
        response = client.delete('/api/parcels/TRK-NONEXISTENT-9999',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 404


# ========================================
# 測試類別 9: Excel 下載 (需求 1.5: 歷史計費數據)
# ========================================

class TestExcelDownload:
    """測試 Excel 匯出功能"""
    
    def test_download_as_admin(self, client, admin_token):
        """測試管理員下載完整資料"""
        response = client.get('/api/download',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200
        assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response.content_type
    
    def test_download_as_staff(self, client, staff_token):
        """測試作業人員下載"""
        response = client.get('/api/download',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        assert response.status_code == 200
    
    def test_download_as_warehouse(self, client, warehouse_token):
        """測試倉儲人員下載"""
        response = client.get('/api/download',
            headers={'Authorization': f'Bearer {warehouse_token}'}
        )
        assert response.status_code == 200
    
    def test_download_as_driver(self, client, driver_token):
        """測試司機下載"""
        response = client.get('/api/download',
            headers={'Authorization': f'Bearer {driver_token}'}
        )
        assert response.status_code == 200
    
    def test_download_as_customer_forbidden(self, client, customer_token):
        """測試客戶無法下載 Excel"""
        response = client.get('/api/download',
            headers={'Authorization': f'Bearer {customer_token}'}
        )
        assert response.status_code == 403


# ========================================
# 測試類別 10: JWT 安全性 (需求 2.4)
# ========================================

class TestJWTSecurity:
    """測試 JWT Token 安全機制"""
    
    def test_expired_token(self, client):
        """測試過期的 Token (需求 2.4: 身份驗證)"""
        expired = jwt.encode(
            {"username": "admin1", "role": "admin", "exp": datetime.utcnow() - timedelta(hours=1)},
            SECRET_KEY, algorithm="HS256"
        )
        response = client.get('/api/customers',
            headers={'Authorization': f'Bearer {expired}'}
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert '過期' in data['error']
    
    def test_invalid_token_signature(self, client):
        """測試無效簽名的 Token"""
        invalid = jwt.encode(
            {"username": "admin1", "role": "admin", "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong_secret", algorithm="HS256"
        )
        response = client.get('/api/customers',
            headers={'Authorization': f'Bearer {invalid}'}
        )
        assert response.status_code == 401
    
    def test_malformed_token(self, client):
        """測試格式錯誤的 Token"""
        response = client.get('/api/customers',
            headers={'Authorization': 'Bearer malformed_token_xyz'}
        )
        assert response.status_code == 401
    
    def test_missing_bearer_prefix(self, client, admin_token):
        """測試缺少 Bearer 前綴"""
        response = client.get('/api/customers',
            headers={'Authorization': admin_token}
        )
        assert response.status_code == 401
    
    def test_missing_authorization_header(self, client):
        """測試缺少 Authorization header"""
        response = client.get('/api/customers')
        assert response.status_code == 401
    
    def test_empty_authorization_header(self, client):
        """測試空的 Authorization header"""
        response = client.get('/api/customers',
            headers={'Authorization': ''}
        )
        assert response.status_code == 401


# ========================================
# 測試類別 11: 邊界與異常情況
# ========================================

class TestEdgeCases:
    """測試邊界條件與異常情況"""
    
    def test_create_parcel_very_heavy(self, client, admin_token):
        """測試極重包裹"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "重物測試",
                "weight": 999.9,
                "package_type": "大型箱"
            }
        )
        assert response.status_code == 201
    
    def test_create_parcel_very_light(self, client, admin_token):
        """測試極輕包裹"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "輕物測試",
                "weight": 0.01,
                "package_type": "平郵信封"
            }
        )
        assert response.status_code == 201
    
    def test_create_parcel_very_high_value(self, client, admin_token):
        """測試高價值包裹"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "高價值測試",
                "weight": 1.0,
                "declared_value": 1000000
            }
        )
        assert response.status_code == 201
    
    def test_set_amount_zero(self, client, admin_token, test_parcel):
        """測試零金額"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 0.0
            }
        )
        assert response.status_code == 200
    
    def test_register_with_all_fields(self, client):
        """測試完整欄位註冊"""
        unique = f"full_{datetime.now().microsecond}"
        response = client.post('/api/auth/register',
            json={
                "username": unique,
                "password": "pass123",
                "name": "完整資料用戶",
                "phone": "0912345678",
                "email": "full@test.com",
                "address": "完整地址 123號",
                "customer_type": "CONTRACT",
                "billing_preference": "MONTHLY"
            }
        )
        assert response.status_code == 200
    
    def test_update_status_with_all_fields(self, client, admin_token, test_parcel):
        """測試完整欄位狀態更新"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "配送中",
                "location": "詳細地點",
                "vehicle_id": "VEH-FULL-001",
                "warehouse_id": "WH-FULL-001",
                "description": "完整描述資訊"
            }
        )
        assert response.status_code == 200


# ========================================
# 測試類別 12: 額外邊界情況覆蓋
# ========================================

class TestAdditionalCoverage:
    """補充測試以提高覆蓋率"""
    
    def test_create_parcel_with_receiver_field(self, client, admin_token):
        """測試使用 receiver 欄位名稱建立包裹"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "receiver": "使用receiver欄位",  # 測試別名
                "receiverAddress": "測試地址",
                "weight": 2.0
            }
        )
        assert response.status_code == 201
    
    def test_create_parcel_with_sender_field(self, client, admin_token):
        """測試使用 sender 欄位名稱"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender": "admin1",  # 測試別名
                "receiver_name": "測試收件人",
                "receiver_address": "測試地址",
                "weight": 1.5
            }
        )
        assert response.status_code == 201
    
    def test_create_parcel_auto_sender(self, client, staff_token):
        """測試自動使用當前用戶作為寄件人"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={
                "recipient_name": "測試自動寄件人",
                "weight": 1.0
            }
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['package']['sender_id'] == 'staff1'
    
    def test_set_amount_with_tracking_no_alias(self, client, admin_token, test_parcel):
        """測試使用 tracking_no 別名"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_no": test_parcel,  # 使用別名
                "amount": 100.0,
                "payment_method": "cash"
            }
        )
        assert response.status_code == 200
    
    def test_set_amount_default_payment_method(self, client, admin_token, test_parcel):
        """測試預設付款方式"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 80.0
                # 不提供 payment_method,測試預設值
            }
        )
        assert response.status_code == 200
    
    def test_update_status_with_tracking_no_alias(self, client, admin_token, test_parcel):
        """測試狀態更新使用 tracking_no 別名"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_no": test_parcel,  # 使用別名
                "status": "處理中"
            }
        )
        assert response.status_code == 200
    
    def test_update_status_empty_optional_fields(self, client, admin_token, test_parcel):
        """測試只提供必要欄位"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "處理中"
                # 不提供 location, vehicle_id, warehouse_id, description
            }
        )
        assert response.status_code == 200
    
    def test_register_minimal_fields(self, client):
        """測試只提供必要註冊欄位"""
        unique = f"minimal_{datetime.now().microsecond}"
        response = client.post('/api/auth/register',
            json={
                "username": unique,
                "password": "pass123"
                # 其他欄位使用預設值
            }
        )
        assert response.status_code == 200
    
    def test_create_customer_minimal_fields(self, client, admin_token):
        """測試只提供必要客戶欄位"""
        unique = f"min_cust_{datetime.now().microsecond}"
        response = client.post('/api/customers',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "account": unique
                # 其他欄位為空
            }
        )
        assert response.status_code == 200
    
    def test_parcel_volume_string_format(self, client, admin_token):
        """測試字串格式的體積"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "體積測試",
                "weight": 3.0,
                "volume": "invalid_volume_string"  # 非數字字串
            }
        )
        # 系統應該接受字串格式的體積
        assert response.status_code == 201
    
    def test_update_status_staff_allowed(self, client, staff_token, test_parcel):
        """測試作業人員可以更新狀態"""
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={
                "tracking_number": test_parcel,
                "status": "處理中"
            }
        )
        assert response.status_code == 200
    
    def test_abnormal_status_return_allowed(self, client, staff_token, admin_token):
        """測試異常狀態可以轉為退回"""
        # 建立新包裹
        create_resp = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "異常轉退回測試",
                "weight": 1.0
            }
        )
        tracking_no = json.loads(create_resp.data)['tracking_no']
        
        # 設為遺失
        client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={
                "tracking_number": tracking_no,
                "status": "遺失"
            }
        )
        
        # 嘗試轉為退回 (應該允許)
        response = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {staff_token}'},
            json={
                "tracking_number": tracking_no,
                "status": "退回"
            }
        )
        assert response.status_code == 200
    
    def test_create_parcel_with_all_aliases(self, client, admin_token):
        """測試所有欄位別名"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender": "admin1",
                "receiver": "測試別名",
                "receiverAddress": "別名地址",
                "weight": 2.5,
                "volume": "20x20x20"
            }
        )
        assert response.status_code == 201


# ========================================
# 測試類別 13: 完整流程整合測試
# ========================================

class TestCompleteWorkflow:
    """測試完整業務流程"""
    
    def test_complete_parcel_lifecycle(self, client, admin_token, warehouse_token, driver_token):
        """測試包裹完整生命週期"""
        # 1. 建立包裹
        create_resp = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "完整流程測試",
                "recipient_address": "台北市大安區",
                "weight": 3.5,
                "package_type": "中型箱",
                "service_type": "標準速遞"
            }
        )
        assert create_resp.status_code == 201
        tracking_no = json.loads(create_resp.data)['tracking_no']
        
        # 2. 設定金額
        amount_resp = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": tracking_no,
                "amount": 200.0,
                "payment_method": "cod"
            }
        )
        assert amount_resp.status_code == 200
        
        # 3. 倉儲收件
        status1 = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {warehouse_token}'},
            json={
                "tracking_number": tracking_no,
                "status": "已收件",
                "location": "台北倉儲",
                "warehouse_id": "WH-TPE-001"
            }
        )
        assert status1.status_code == 200
        
        # 4. 進入倉儲
        status2 = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {warehouse_token}'},
            json={
                "tracking_number": tracking_no,
                "status": "進入倉儲",
                "warehouse_id": "WH-TPE-001"
            }
        )
        assert status2.status_code == 200
        
        # 5. 裝車
        status3 = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {warehouse_token}'},
            json={
                "tracking_number": tracking_no,
                "status": "已裝車",
                "vehicle_id": "VEH-001"
            }
        )
        assert status3.status_code == 200
        
        # 6. 配送中
        status4 = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {driver_token}'},
            json={
                "tracking_number": tracking_no,
                "status": "配送中",
                "vehicle_id": "VEH-001"
            }
        )
        assert status4.status_code == 200
        
        # 7. 送達
        status5 = client.post('/api/parcels/status',
            headers={'Authorization': f'Bearer {driver_token}'},
            json={
                "tracking_number": tracking_no,
                "status": "已送達",
                "description": "本人簽收"
            }
        )
        assert status5.status_code == 200
        
        # 8. 查詢歷史
        history_resp = client.get(f'/api/parcels/{tracking_no}/history',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert history_resp.status_code == 200
        history_data = json.loads(history_resp.data)
        # 應該有至少 6 個事件 (建立 + 5次狀態更新)
        assert len(history_data['events']) >= 6
    
    def test_contract_customer_workflow(self, client):
        """測試合約客戶完整流程"""
        # 1. 註冊合約客戶
        unique = f"contract_flow_{datetime.now().microsecond}"
        reg_resp = client.post('/api/auth/register',
            json={
                "username": unique,
                "password": "pass123",
                "name": "合約客戶流程",
                "customer_type": "CONTRACT",
                "billing_preference": "MONTHLY"
            }
        )
        assert reg_resp.status_code == 200
        
        # 2. 登入
        login_resp = client.post('/api/auth/login',
            json={"username": unique, "password": "pass123"}
        )
        assert login_resp.status_code == 200
        token = json.loads(login_resp.data)['token']
        
        # 3. 建立包裹
        parcel_resp = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {token}'},
            json={
                "recipient_name": "合約客戶收件人",
                "weight": 2.0
            }
        )
        assert parcel_resp.status_code == 201
        
        # 4. 查詢自己的記錄
        records_resp = client.get('/records',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert records_resp.status_code == 200

class TestInitialization:
    """測試系統初始化"""
    
    def test_init_default_accounts(self):
        """測試預設帳號初始化"""
        from app import init_default_accounts
        from db_operations import read_accounts
        
        init_default_accounts()
        accounts = read_accounts()
        
        # 驗證預設帳號都存在
        assert "admin1" in accounts
        assert "staff1" in accounts
        assert "driver1" in accounts
        assert "warehouse1" in accounts
        assert "test1" in accounts
    
    def test_secret_key_exists(self):
        """測試 SECRET_KEY 存在"""
        from app import SECRET_KEY
        assert SECRET_KEY is not None
        assert len(SECRET_KEY) > 0

class TestTokenDecorator:
    """測試 token_required 裝飾器的所有分支"""
    
    def test_token_without_bearer(self, client):
        """測試沒有 Bearer 前綴"""
        response = client.get('/api/customers',
            headers={'Authorization': 'some_token_without_bearer'}
        )
        assert response.status_code == 401
    
    def test_authorization_header_empty_string(self, client):
        """測試空字串 Authorization"""
        response = client.get('/api/customers',
            headers={'Authorization': ''}
        )
        assert response.status_code == 401
    
    def test_authorization_bearer_only(self, client):
        """測試只有 Bearer 沒有 token"""
        response = client.get('/api/customers',
            headers={'Authorization': 'Bearer '}
        )
        assert response.status_code == 401

def test_database_error_handling(client, admin_token, monkeypatch, test_parcel):
        """測試資料庫交易錯誤處理 """
        from unittest.mock import Mock
        
        # 1. 建立一個假的 Session 物件
        mock_session = Mock()
        # 設定：當呼叫 commit() 時，才拋出錯誤
        mock_session.commit.side_effect = Exception("DB Commit Error")
        # 設定：其他的查詢 (query) 都回傳正常的 Mock，避免在查詢階段就報錯
        mock_session.query.return_value.filter_by.return_value.first.return_value = Mock()

        # 2. 建立一個假的 SessionLocal 建構子，讓它回傳上面那個假的 Session
        mock_session_constructor = Mock(return_value=mock_session)
        
        # 3. 替換掉 app.py 裡面的 SessionLocal
        monkeypatch.setattr("app.SessionLocal", mock_session_constructor)

        # 4. 執行會觸發寫入的動作 (例如設定金額)
        # 注意：這裡使用 test_parcel 確保有真實的追蹤編號流程可跑
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 100,
                "payment_method": "cash"
            }
        )
        
        # 5. 驗證結果
        # 如果 app.py 有寫 try-except，這裡應該要回傳 500 並且程式不會當機
        assert response.status_code == 500
        assert "error" in response.json

class TestConditionalBranches:
    """測試條件分支"""
    
    def test_parcel_with_null_volume(self, client, admin_token):
        """測試 volume 為 None"""
        response = client.post('/api/parcels',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "sender_id": "admin1",
                "recipient_name": "測試",
                "weight": 1.0,
                "volume": None  # 明確設為 None
            }
        )
        assert response.status_code == 201
    
    def test_amount_with_service_type_none(self, client, admin_token, test_parcel):
        """測試不提供 service_type"""
        response = client.post('/api/parcels/amount',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                "tracking_number": test_parcel,
                "amount": 100.0,
                "payment_method": "cash"
                # 不提供 service_type
            }
        )
        assert response.status_code == 200
# ========================================
# 測試統計與報告
# ========================================

if __name__ == '__main__':
    pytest.main([
        __file__,
        '-v',  # 詳細輸出
        '--tb=short',  # 簡短錯誤追蹤
        '--cov=app',  # 代碼覆蓋率
        '--cov-report=html',  # HTML 報告
        '--cov-report=term-missing',  # 顯示未覆蓋行
        '--cov-report=json',  # JSON 報告
        '-p', 'no:warnings'  # 忽略警告
    ])