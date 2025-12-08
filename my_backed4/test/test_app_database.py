# 檔案位置: my_backed3/test/test_app_database.py
"""
針對 app_database.py 的 Pytest 測試
執行方式: pytest test/test_app_database.py -v
"""

import pytest
import json
import sys
import os

# 確保可以 import 到 src 資料夾的模組
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.app_database import app, db, User, hash_password, PackageStatus

@pytest.fixture
def client():
    """建立測試用的 Flask 客戶端 (使用記憶體資料庫)"""
    app.config['TESTING'] = True
    # 強制切換為記憶體資料庫
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            # 1. 關鍵修改：先移除舊連線並清空資料庫，確保環境是乾淨的
            db.session.remove()
            db.drop_all()
            
            # 2. 重新建立表格
            db.create_all()
            
            # 3. 建立測試資料 (這時候因為表格是空的，所以不會報錯)
            db.session.add(User(username='admin', password_hash=hash_password('admin123'), role='admin'))
            db.session.add(User(username='staff1', password_hash=hash_password('staff123'), role='staff'))
            db.session.add(User(username='customer1', password_hash=hash_password('customer123'), role='customer'))
            db.session.commit()
            
            yield client
            
            # 4. 測試結束後再次清理
            db.session.remove()
            db.drop_all()

def get_token(client, username, password):
    """輔助函式：取得 JWT Token"""
    response = client.post('/api/auth/login',
                          data=json.dumps({'username': username, 'password': password}),
                          content_type='application/json')
    return response.json['token']

# ========== 測試案例 ==========

def test_db_health_check(client):
    """測試伺服器是否活著"""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert 'DB版' in response.json['message']

def test_create_customer_with_database(client):
    """測試寫入客戶資料到資料庫"""
    token = get_token(client, 'staff1', 'staff123')
    
    payload = {
        'account': 'CUST-TEST-001',
        'name': '測試客戶',
        'email': 'test@example.com',
        'phone': '0912345678',
        'address': '台北市測試路',
        'type': '合約'
    }
    
    response = client.post('/api/customers',
                          data=json.dumps(payload),
                          headers={'Authorization': f'Bearer {token}'},
                          content_type='application/json')
    
    assert response.status_code == 200
    assert response.json['customer']['name'] == '測試客戶'
    # 確認資料庫真的有存入 (利用 GET API 驗證)
    get_resp = client.get('/api/customers', 
                         headers={'Authorization': f'Bearer {token}'})
    assert len(get_resp.json) == 1
    assert get_resp.json[0]['account'] == 'CUST-TEST-001'

def test_create_customer_duplicate(client):
    """測試重複建立客戶 (應該要失敗)"""
    token = get_token(client, 'staff1', 'staff123')
    payload = {
        'account': 'CUST-DUP', 'name': 'Duplicate', 
        'email': 'dup@e.com', 'phone': '0900', 'address': 'Addr'
    }
    
    # 第一次建立
    client.post('/api/customers', data=json.dumps(payload),
                headers={'Authorization': f'Bearer {token}'}, content_type='application/json')
    
    # 第二次建立 (帳號相同)
    response = client.post('/api/customers', data=json.dumps(payload),
                          headers={'Authorization': f'Bearer {token}'}, content_type='application/json')
    
    assert response.status_code == 400
    assert '已存在' in response.json['error']

def test_create_parcel_and_status(client):
    """測試建立包裹與預設狀態"""
    token = get_token(client, 'staff1', 'staff123')
    
    payload = {
        'sender_id': 'customer1',
        'recipient_name': '收件人A',
        'recipient_address': '高雄市楠梓區',
        'weight': 2.5
    }
    
    response = client.post('/api/parcels',
                          data=json.dumps(payload),
                          headers={'Authorization': f'Bearer {token}'},
                          content_type='application/json')
    
    assert response.status_code == 200
    pkg = response.json['package']
    assert pkg['tracking_number'].startswith('TRK')
    assert pkg['status'] == PackageStatus.CREATED.value  # 驗證預設狀態是否為 "已建立"

def test_search_parcel_permission(client):
    """測試搜尋權限 (客戶只能搜自己的)"""
    staff_token = get_token(client, 'staff1', 'staff123')
    
    # 員工建立兩個包裹：一個是 customer1 的，一個是 customer2 的
    client.post('/api/parcels',
               data=json.dumps({'sender_id': 'customer1', 'recipient_name': 'R1', 'recipient_address': 'A1'}),
               headers={'Authorization': f'Bearer {staff_token}'}, content_type='application/json')
    
    client.post('/api/parcels',
               data=json.dumps({'sender_id': 'customer2', 'recipient_name': 'R2', 'recipient_address': 'A2'}),
               headers={'Authorization': f'Bearer {staff_token}'}, content_type='application/json')

    # customer1 搜尋
    cust_token = get_token(client, 'customer1', 'customer123')
    response = client.post('/api/parcels/search',
                          data=json.dumps({}), # 空條件，搜全部
                          headers={'Authorization': f'Bearer {cust_token}'},
                          content_type='application/json')
    
    results = response.json
    # 應該只找得到自己 (customer1) 的那一個
    assert len(results) == 1
    assert results[0]['sender_id'] == 'customer1'