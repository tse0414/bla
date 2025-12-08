"""
物流管理系統 - 完整測試套件
測試所有功能：客戶管理、包裹管理、追蹤、計費、權限控管
"""

import pytest
import json
import os
from datetime import datetime
from src.app import (
    app, customer_mgr, package_mgr, tracking_mgr, billing_mgr,
    CustomerType, PackageStatus, ServiceType
)

@pytest.fixture
def client():
    """建立測試客戶端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def cleanup():
    """測試後清理資料"""
    yield
    # 清理測試資料檔案
    files = ['data_customers.json', 'data_packages.json', 'data_tracking.json', 'data_billing.json']
    for f in files:
        if os.path.exists(f):
            os.remove(f)

# ========== 基礎測試 ==========
def test_health_check(client):
    """測試健康檢查"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ok'

# ========== 客戶管理測試 ==========
def test_create_customer_success(client):
    """測試建立客戶 - 成功案例"""
    response = client.post('/api/customers', 
        json={
            'current_role': 'staff',
            'name': '測試客戶',
            'address': '台北市信義區',
            'phone': '0912345678',
            'email': 'test@example.com',
            'account': 'TEST001'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['customer']['name'] == '測試客戶'
    assert data['customer']['customer_id'] == 'TEST001'

def test_create_customer_permission_denied(client):
    """測試建立客戶 - 權限不足"""
    response = client.post('/api/customers', 
        json={
            'current_role': 'customer',  # 客戶角色不能建立客戶
            'name': '測試客戶',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'test@example.com',
            'account': 'TEST001'
        })
    
    assert response.status_code == 403
    data = json.loads(response.data)
    assert 'error' in data
    assert '權限不足' in data['error']

def test_get_customers(client):
    """測試取得客戶列表"""
    # 先建立一個客戶
    client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': '測試客戶',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'test@example.com',
            'account': 'TEST001'
        })
    
    response = client.get('/api/customers')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) >= 1

def test_get_customer_by_id(client):
    """測試取得單一客戶"""
    # 先建立客戶
    client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': '測試客戶',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'test@example.com',
            'account': 'TEST002'
        })
    
    response = client.get('/api/customers/TEST002')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['customer_id'] == 'TEST002'

# ========== 包裹管理測試 ==========
def test_create_parcel_success(client):
    """測試建立包裹 - 成功案例"""
    # 先建立客戶
    client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': '寄件人',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'sender@example.com',
            'account': 'SENDER001'
        })
    
    response = client.post('/api/parcels', 
        json={
            'current_role': 'staff',
            'sender_id': 'SENDER001',
            'recipient_name': '收件人',
            'recipient_address': '高雄市',
            'weight': 2.5,
            'length': 30,
            'width': 20,
            'height': 15,
            'declared_value': 1000,
            'content_description': '測試貨物',
            'distance': 350,
            'service_type': '標準配送'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'tracking_number' in data['package']

def test_create_parcel_permission_denied(client):
    """測試建立包裹 - 權限不足"""
    response = client.post('/api/parcels', 
        json={
            'current_role': 'customer',  # 客戶不能建立包裹
            'sender_id': 'TEST001',
            'recipient_name': '收件人',
            'recipient_address': '高雄市'
        })
    
    assert response.status_code == 403

def test_get_parcels(client):
    """測試取得包裹列表"""
    response = client.get('/api/parcels')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

# ========== 進階搜尋測試 (缺口一) ==========
def test_search_parcels_by_sender(client):
    """測試依寄件人搜尋包裹"""
    # 建立測試資料
    client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': '測試客戶',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'test@example.com',
            'account': 'SEARCH001'
        })
    
    client.post('/api/parcels', 
        json={
            'current_role': 'staff',
            'sender_id': 'SEARCH001',
            'recipient_name': '收件人A',
            'recipient_address': '高雄市',
            'weight': 1.0,
            'distance': 100
        })
    
    # 搜尋
    response = client.post('/api/parcels/search', 
        json={
            'current_role': 'staff',
            'sender_id': 'SEARCH001'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    for item in data:
        assert item['sender_id'] == 'SEARCH001'

def test_search_parcels_by_date_range(client):
    """測試依日期範圍搜尋"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    response = client.post('/api/parcels/search', 
        json={
            'current_role': 'staff',
            'date_from': today,
            'date_to': today
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_search_parcels_customer_restriction(client):
    """測試客戶只能搜尋自己的包裹"""
    response = client.post('/api/parcels/search', 
        json={
            'current_role': 'customer',
            'customer_id': 'CUST001',
            'sender_id': 'OTHER_CUSTOMER'  # 試圖查看別人的
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    # 應該只回傳 CUST001 的包裹
    for item in data:
        assert item['sender_id'] == 'CUST001'

# ========== 追蹤管理測試 ==========
def test_get_tracking(client):
    """測試查詢追蹤"""
    # 先建立包裹
    client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': '測試客戶',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'test@example.com',
            'account': 'TRACK001'
        })
    
    parcel_resp = client.post('/api/parcels', 
        json={
            'current_role': 'staff',
            'sender_id': 'TRACK001',
            'recipient_name': '收件人',
            'recipient_address': '高雄市'
        })
    
    parcel_data = json.loads(parcel_resp.data)
    tracking_number = parcel_data['package']['tracking_number']
    
    # 查詢追蹤
    response = client.get(f'/api/tracking/{tracking_number}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'package' in data
    assert 'events' in data

def test_add_tracking_event(client):
    """測試新增追蹤事件"""
    # 先建立包裹
    client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': '測試客戶',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'test@example.com',
            'account': 'TRACK002'
        })
    
    parcel_resp = client.post('/api/parcels', 
        json={
            'current_role': 'staff',
            'sender_id': 'TRACK002',
            'recipient_name': '收件人',
            'recipient_address': '高雄市'
        })
    
    parcel_data = json.loads(parcel_resp.data)
    tracking_number = parcel_data['package']['tracking_number']
    
    # 新增事件
    response = client.post('/api/tracking/event', 
        json={
            'current_role': 'staff',
            'tracking_number': tracking_number,
            'status': '已取件',
            'location': '台北物流中心',
            'notes': '包裹已收件'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True

def test_add_tracking_event_permission_denied(client):
    """測試新增事件 - 權限不足"""
    response = client.post('/api/tracking/event', 
        json={
            'current_role': 'customer',  # 客戶不能新增事件
            'tracking_number': 'TRK123',
            'status': '已取件',
            'location': '台北',
            'notes': '測試'
        })
    
    assert response.status_code == 403

# ========== 計費測試 (缺口三) ==========
def test_calculate_cost_with_distance_and_volume(client):
    """測試計費 - 包含距離與體積"""
    # 建立包裹
    client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': '測試客戶',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'test@example.com',
            'account': 'BILL001'
        })
    
    parcel_resp = client.post('/api/parcels', 
        json={
            'current_role': 'staff',
            'sender_id': 'BILL001',
            'recipient_name': '收件人',
            'recipient_address': '高雄市',
            'weight': 2.0,
            'length': 30,
            'width': 20,
            'height': 15,
            'distance': 350,
            'service_type': '標準配送'
        })
    
    parcel_data = json.loads(parcel_resp.data)
    tracking_number = parcel_data['package']['tracking_number']
    
    # 計算費用
    response = client.get(f'/api/billing/calculate/{tracking_number}')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'total' in data
    assert 'base_cost' in data
    assert 'weight_cost' in data
    assert 'distance_cost' in data
    assert data['total'] > 0
    
    # 驗證計算邏輯
    # 基本費 50 + 重量費 + 距離費
    expected_min = 50 + (2.0 * 5) + (350 * 2)  # 基本費 + 重量(2kg * 5元/kg) + 距離(350km * 2元/km)
    assert data['total'] >= expected_min

def test_calculate_cost_volume_weight_priority(client):
    """測試計費 - 體積重量優先"""
    # 建立體積很大但重量輕的包裹
    client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': '測試客戶',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'test@example.com',
            'account': 'BILL002'
        })
    
    parcel_resp = client.post('/api/parcels', 
        json={
            'current_role': 'staff',
            'sender_id': 'BILL002',
            'recipient_name': '收件人',
            'recipient_address': '高雄市',
            'weight': 0.5,  # 實重 0.5kg
            'length': 100,  # 長 100cm
            'width': 50,    # 寬 50cm
            'height': 50,   # 高 50cm (體積重 = 100*50*50/5000 = 50kg)
            'distance': 100
        })
    
    parcel_data = json.loads(parcel_resp.data)
    tracking_number = parcel_data['package']['tracking_number']
    
    response = client.get(f'/api/billing/calculate/{tracking_number}')
    data = json.loads(response.data)
    
    # 體積重應該大於實重
    assert data['volume_weight'] > data['actual_weight']
    # 計費重量應該採用體積重
    assert data['charge_weight'] == data['volume_weight']

# ========== 月結報表測試 (缺口二) ==========
def test_monthly_report(client):
    """測試月結報表生成"""
    # 建立客戶與多個包裹
    client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': '月結客戶',
            'address': '台北市',
            'phone': '0912345678',
            'email': 'monthly@example.com',
            'account': 'MONTHLY001'
        })
    
    # 建立第一個包裹
    client.post('/api/parcels', 
        json={
            'current_role': 'staff',
            'sender_id': 'MONTHLY001',
            'recipient_name': '收件人A',
            'recipient_address': '台中市',
            'weight': 1.0,
            'distance': 150
        })
    
    # 建立第二個包裹
    client.post('/api/parcels', 
        json={
            'current_role': 'staff',
            'sender_id': 'MONTHLY001',
            'recipient_name': '收件人B',
            'recipient_address': '高雄市',
            'weight': 2.0,
            'distance': 350
        })
    
    # 生成月結報表
    current_month = datetime.now().strftime('%Y-%m')
    response = client.post('/api/billing/monthly-report', 
        json={
            'current_role': 'staff',
            'customer_id': 'MONTHLY001',
            'month': current_month
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert data['customer_id'] == 'MONTHLY001'
    assert data['month'] == current_month
    assert data['shipment_count'] == 2
    assert data['total_amount'] > 0
    assert len(data['shipments']) == 2

def test_monthly_report_permission_denied(client):
    """測試月結報表 - 權限不足"""
    response = client.post('/api/billing/monthly-report', 
        json={
            'current_role': 'customer',  # 客戶不能產生報表
            'customer_id': 'TEST001',
            'month': '2025-12'
        })
    
    assert response.status_code == 403

# ========== 帳單管理測試 ==========
def test_create_invoice(client):
    """測試建立帳單"""
    response = client.post('/api/billing/invoice', 
        json={
            'current_role': 'staff',
            'customer_account': 'TEST001',
            'amount': 5000,
            'method': '月結',
            'status': '未付款'
        })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True

def test_get_invoices(client):
    """測試取得帳單列表"""
    response = client.get('/api/billing/invoices')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

# ========== 權限控管整合測試 (缺口四) ==========
def test_permission_hierarchy(client):
    """測試權限階層"""
    # 客戶角色
    customer_ops = [
        ('POST', '/api/customers', {'current_role': 'customer', 'name': 'Test', 'address': 'Test', 'phone': '0912345678', 'email': 'test@test.com', 'account': 'T001'}),
        ('POST', '/api/parcels', {'current_role': 'customer', 'sender_id': 'T001', 'recipient_name': 'R', 'recipient_address': 'A'}),
        ('POST', '/api/tracking/event', {'current_role': 'customer', 'tracking_number': 'T123', 'status': '已取件', 'location': 'L'}),
    ]
    
    for method, url, data in customer_ops:
        if method == 'POST':
            response = client.post(url, json=data)
            assert response.status_code == 403, f"客戶不應該能存取 {url}"
    
    # 作業人員角色
    response = client.post('/api/customers', 
        json={
            'current_role': 'staff',
            'name': 'Test',
            'address': 'Test',
            'phone': '0912345678',
            'email': 'test@test.com',
            'account': 'STAFF001'
        })
    assert response.status_code == 200, "作業人員應該能建立客戶"
    
    # 管理員角色 (最高權限)
    response = client.post('/api/customers', 
        json={
            'current_role': 'admin',
            'name': 'Admin Test',
            'address': 'Test',
            'phone': '0912345678',
            'email': 'admin@test.com',
            'account': 'ADMIN001'
        })
    assert response.status_code == 200, "管理員應該能執行所有操作"

# ========== 錯誤處理測試 ==========
def test_404_error(client):
    """測試 404 錯誤"""
    response = client.get('/api/nonexistent')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_missing_tracking_number(client):
    """測試查詢不存在的追蹤編號"""
    response = client.get('/api/tracking/NONEXISTENT123')
    assert response.status_code == 404

def test_missing_customer(client):
    """測試查詢不存在的客戶"""
    response = client.get('/api/customers/NONEXISTENT')
    assert response.status_code == 404

# ========== 執行測試 ==========
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])