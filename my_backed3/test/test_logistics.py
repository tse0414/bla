"""
物流系統 Pytest 測試
執行方式: pytest test_logistics.py -v
"""

import pytest
import json
from src.app import app, users, hash_password

@pytest.fixture
def client():
    """建立測試客戶端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # 重置測試資料
        users.clear()
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
        yield client

def get_token(client, username, password):
    """取得登入 Token"""
    response = client.post('/api/auth/login',
                          data=json.dumps({
                              'username': username,
                              'password': password
                          }),
                          content_type='application/json')
    return response.json['token']

# ========== 測試登入系統 ==========

def test_health_check(client):
    """測試健康檢查"""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'

def test_login_success(client):
    """測試成功登入"""
    response = client.post('/api/auth/login',
                          data=json.dumps({
                              'username': 'admin',
                              'password': 'admin123'
                          }),
                          content_type='application/json')
    
    assert response.status_code == 200
    assert 'token' in response.json
    assert response.json['role'] == 'admin'

def test_login_wrong_password(client):
    """測試密碼錯誤"""
    response = client.post('/api/auth/login',
                          data=json.dumps({
                              'username': 'admin',
                              'password': 'wrong'
                          }),
                          content_type='application/json')
    
    assert response.status_code == 401
    assert '錯誤' in response.json['error']

def test_register_new_user(client):
    """測試註冊新使用者"""
    response = client.post('/api/auth/register',
                          data=json.dumps({
                              'username': 'testuser',
                              'password': 'test123',
                              'role': 'customer'
                          }),
                          content_type='application/json')
    
    assert response.status_code == 201
    assert response.json['role'] == 'customer'

def test_register_duplicate_user(client):
    """測試重複註冊"""
    response = client.post('/api/auth/register',
                          data=json.dumps({
                              'username': 'admin',
                              'password': 'test123',
                              'role': 'customer'
                          }),
                          content_type='application/json')
    
    assert response.status_code == 400
    assert '已存在' in response.json['error']

# ========== 測試權限控制 ==========

def test_create_customer_without_token(client):
    """測試未登入建立客戶"""
    response = client.post('/api/customers',
                          data=json.dumps({
                              'name': 'Test Customer',
                              'address': 'Test Address',
                              'phone': '0912345678',
                              'email': 'test@example.com',
                              'account': 'TEST001'
                          }),
                          content_type='application/json')
    
    assert response.status_code == 401
    assert '缺少' in response.json['error']

def test_create_customer_with_customer_role(client):
    """測試客戶角色無法建立客戶"""
    token = get_token(client, 'customer1', 'customer123')
    
    response = client.post('/api/customers',
                          data=json.dumps({
                              'name': 'Test Customer',
                              'address': 'Test Address',
                              'phone': '0912345678',
                              'email': 'test@example.com',
                              'account': 'TEST001'
                          }),
                          headers={'Authorization': f'Bearer {token}'},
                          content_type='application/json')
    
    assert response.status_code == 403
    assert '權限不足' in response.json['error']

def test_create_customer_with_staff_role(client):
    """測試員工角色可以建立客戶"""
    token = get_token(client, 'staff1', 'staff123')
    
    response = client.post('/api/customers',
                          data=json.dumps({
                              'name': 'Test Customer',
                              'address': 'Test Address',
                              'phone': '0912345678',
                              'email': 'test@example.com',
                              'account': 'TEST001'
                          }),
                          headers={'Authorization': f'Bearer {token}'},
                          content_type='application/json')
    
    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['customer']['name'] == 'Test Customer'

# ========== 測試包裹管理 ==========

def test_create_parcel_with_staff(client):
    """測試員工建立包裹"""
    token = get_token(client, 'staff1', 'staff123')
    
    response = client.post('/api/parcels',
                          data=json.dumps({
                              'sender_id': 'customer1',
                              'recipient_name': 'John Doe',
                              'recipient_address': '123 Test St',
                              'weight': 5.5,
                              'distance': 10.0
                          }),
                          headers={'Authorization': f'Bearer {token}'},
                          content_type='application/json')
    
    assert response.status_code == 200
    assert response.json['success'] is True
    assert 'tracking_number' in response.json['package']

def test_get_parcels_customer_only_sees_own(client):
    """測試客戶只能看到自己的包裹"""
    # 先建立包裹 (使用 staff)
    staff_token = get_token(client, 'staff1', 'staff123')
    
    # 建立 customer1 的包裹
    client.post('/api/parcels',
               data=json.dumps({
                   'sender_id': 'customer1',
                   'recipient_name': 'Test Recipient',
                   'recipient_address': 'Test Address'
               }),
               headers={'Authorization': f'Bearer {staff_token}'},
               content_type='application/json')
    
    # 建立其他客戶的包裹
    client.post('/api/parcels',
               data=json.dumps({
                   'sender_id': 'other_customer',
                   'recipient_name': 'Other Recipient',
                   'recipient_address': 'Other Address'
               }),
               headers={'Authorization': f'Bearer {staff_token}'},
               content_type='application/json')
    
    # customer1 登入查詢
    customer_token = get_token(client, 'customer1', 'customer123')
    response = client.get('/api/parcels',
                         headers={'Authorization': f'Bearer {customer_token}'})
    
    assert response.status_code == 200
    parcels = response.json
    
    # 客戶只能看到自己的包裹
    assert all(p['sender_id'] == 'customer1' for p in parcels)

def test_get_parcels_staff_sees_all(client):
    """測試員工可以看到所有包裹"""
    staff_token = get_token(client, 'staff1', 'staff123')
    
    # 建立多個包裹
    client.post('/api/parcels',
               data=json.dumps({
                   'sender_id': 'customer1',
                   'recipient_name': 'Recipient 1',
                   'recipient_address': 'Address 1'
               }),
               headers={'Authorization': f'Bearer {staff_token}'},
               content_type='application/json')
    
    client.post('/api/parcels',
               data=json.dumps({
                   'sender_id': 'customer2',
                   'recipient_name': 'Recipient 2',
                   'recipient_address': 'Address 2'
               }),
               headers={'Authorization': f'Bearer {staff_token}'},
               content_type='application/json')
    
    # 員工查詢所有包裹
    response = client.get('/api/parcels',
                         headers={'Authorization': f'Bearer {staff_token}'})
    
    assert response.status_code == 200
    parcels = response.json
    assert len(parcels) >= 2

# ========== 測試搜尋功能 ==========

def test_search_parcels_customer_restricted(client):
    """測試客戶搜尋被限制在自己的包裹"""
    staff_token = get_token(client, 'staff1', 'staff123')
    
    # 建立測試包裹
    client.post('/api/parcels',
               data=json.dumps({
                   'sender_id': 'customer1',
                   'recipient_name': 'Test',
                   'recipient_address': 'Address'
               }),
               headers={'Authorization': f'Bearer {staff_token}'},
               content_type='application/json')
    
    # 客戶搜尋
    customer_token = get_token(client, 'customer1', 'customer123')
    response = client.post('/api/parcels/search',
                          data=json.dumps({}),
                          headers={'Authorization': f'Bearer {customer_token}'},
                          content_type='application/json')
    
    assert response.status_code == 200
    results = response.json
    assert all(r['sender_id'] == 'customer1' for r in results)

# ========== 執行測試 ==========

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])