from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import jwt
from functools import wraps
from datetime import datetime, timedelta
import os

from excel_db import (
    EXCEL_FILE,
    initialize_excel,
    append_customer,
    read_customers,
    update_customer,
    append_parcel,
    read_parcels,
    update_parcel_amount,
    update_parcel_status,
    append_tracking_event,      
    read_tracking_events,        
    append_account,              
    read_accounts,               
    find_account,
    read_all_events_for_search,
    read_customers,       
)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization"])

SECRET_KEY = "my_secret_key_for_jwt_12345"

# ✅ 初始化預設帳號 (只在第一次執行時寫入 Excel)
def init_default_accounts():
    """初始化預設帳號到 Excel"""
    accounts = read_accounts()
    
    defaults = {
        "staff1": {"password": "staff123", "role": "staff"},
        "admin1": {"password": "admin123", "role": "admin"},
        "driver1": {"password": "driver123", "role": "driver"},
        "warehouse1": {"password": "warehouse123", "role": "warehouse"},  # ✅ 新增倉儲人員
        "test1": {"password": "test123", "role": "customer"},
    }
    
    for username, info in defaults.items():
        if username not in accounts:
            append_account({
                "username": username,
                "password": info["password"],
                "role": info["role"]
            })


# ------------------------------------------------
# JWT 驗證裝飾器
# ------------------------------------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            auth = request.headers["Authorization"]
            if auth.startswith("Bearer "):
                token = auth.split(" ")[1]

        if not token:
            return jsonify({"error": "缺少 JWT Token"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user = data
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token 已過期"}), 401
        except Exception:
            return jsonify({"error": "無效 Token"}), 401

        return f(*args, **kwargs)

    return decorated


# ------------------------------------------------
# 登入 (改用 Excel 查詢)
# ------------------------------------------------
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "請提供帳號與密碼"}), 400

    # ✅ 從 Excel 讀取帳號
    account = find_account(username)
    
    if not account:
        return jsonify({"error": "帳號不存在"}), 401

    if account["password"] != password:
        return jsonify({"error": "密碼錯誤"}), 401

    token = jwt.encode(
        {
            "username": username,
            "role": account["role"],
            "exp": datetime.utcnow() + timedelta(hours=4),
        },
        SECRET_KEY,
        algorithm="HS256",
    )

    return jsonify(
        {
            "message": "登入成功",
            "username": username,
            "role": account["role"],
            "token": token,
        }
    )


# ------------------------------------------------
# 客戶註冊 (改良版)
# ------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
def register_customer_account():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    name = data.get("name") or ""
    phone = data.get("phone") or ""
    email = data.get("email") or ""
    address = data.get("address") or ""
    customer_type = data.get("customer_type") or "NON_CONTRACT"  # ✅ 新增
    billing_preference = data.get("billing_preference") or "COD"  # ✅ 新增

    if not username or not password:
        return jsonify({"error": "請提供帳號與密碼"}), 400

    # ✅ 檢查帳號是否已存在
    if find_account(username):
        return jsonify({"error": "帳號已存在"}), 400

    # ✅ 寫入 Accounts 表
    append_account({
        "username": username,
        "password": password,
        "role": "customer"
    })

    # 寫入 Customers 表
    append_customer({
        "account": username,
        "name": name,
        "phone": phone,
        "email": email,
        "address": address,
        "customer_type": customer_type,
        "billing_preference": billing_preference,
    })

    return jsonify({"message": "註冊成功", "username": username})


# ------------------------------------------------
# 客戶資料：建立 / 查看 / 修改
# ------------------------------------------------
@app.route("/api/customers", methods=["POST"])
@token_required
def create_customer():
    if request.user.get("role") not in ["staff", "admin"]:
        return jsonify({"error": "權限不足"}), 403

    data = request.get_json() or {}
    append_customer(data)

    return jsonify({"message": "客戶已建立", "customer_id": data.get("account")})


@app.route("/api/customers", methods=["GET"])
@token_required
def list_customers():
    role = request.user.get("role")
    if role not in ["staff", "admin"]:
        return jsonify({"error": "權限不足"}), 403

    customers = read_customers() or []
    return jsonify(customers)


@app.route("/api/customers/<account>", methods=["PUT"])
@token_required
def edit_customer(account):
    if request.user.get("role") != "admin":
        return jsonify({"error": "只有管理員可以修改客戶資料"}), 403

    data = request.get_json() or {}
    update_customer(account, data)

    return jsonify({"message": "客戶資料已更新"})


# ------------------------------------------------
# 建立包裹 (改良版)
# ------------------------------------------------
@app.route("/api/parcels", methods=["POST"])
@token_required
def create_parcel():
    data = request.get_json() or {}

    sender_id = (
        data.get("sender")
        or data.get("sender_id")
        or request.user.get("username")
    )
    recipient_name = (
        data.get("receiver")
        or data.get("receiver_name")
        or data.get("recipient_name")
    )
    recipient_address = (
        data.get("receiverAddress")
        or data.get("receiver_address")
        or data.get("recipient_address")
        or ""
    )
    weight = data.get("weight")
    package_type = data.get("package_type") or "中型箱"  # ✅ 新增
    declared_value = data.get("declared_value") or 0    # ✅ 新增
    contents = data.get("contents") or "一般貨物"        # ✅ 新增
    service_type = data.get("service_type") or "標準速遞"

    customers = read_customers()
    sender_info = next((c for c in customers if c["account"] == sender_id), None)
    
    is_contract = False
    if sender_info and sender_info.get("customer_type") == "CONTRACT":
        is_contract = True

    if not sender_id or not recipient_name:
        return jsonify({"error": "缺少寄件人或收件人"}), 400

    today = datetime.now().strftime("%Y%m%d")
    rand4 = str(datetime.now().microsecond)[-4:]
    tracking_number = f"TRK-{today}-{rand4}"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    record = {
        "tracking_number": tracking_number,
        "sender_id": sender_id,
        "recipient_name": recipient_name,
        "recipient_address": recipient_address,
        "weight": weight,
        "package_type": package_type,      # ✅
        "declared_value": declared_value,  # ✅
        "contents": contents,              # ✅
        "service_type": service_type,
        "status": "建立包裹",
        "amount": None,
        "created_at": created_at,
    }

    append_parcel(record)
    
    # ✅ 同時記錄第一筆事件
    event_id = f"EVT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    append_tracking_event({
        "event_id": event_id,
        "tracking_number": tracking_number,
        "event_type": "建立包裹",
        "timestamp": created_at,
        "location": "系統",
        "operator": request.user.get("username"),
        "description": f"包裹由 {sender_id} 建立"
    })

    return jsonify(
        {
            "message": "包裹建立成功",
            "tracking_no": tracking_number,
            "package": record,
        }
    ), 201


# ------------------------------------------------
# 更新包裹金額（付款完成）
# ------------------------------------------------
@app.route("/api/parcels/amount", methods=["POST"])
@token_required
def set_parcel_amount():
    data = request.get_json() or {}
    tracking = data.get("tracking_number") or data.get("tracking_no")
    amount = data.get("amount")

    if not tracking:
        return jsonify({"error": "缺少追蹤編號"}), 400
    if amount is None:
        return jsonify({"error": "缺少金額"}), 400

    try:
        amount_val = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "金額格式錯誤"}), 400

    update_parcel_amount(tracking, amount_val)
    
    # ✅ 記錄付款事件
    event_id = f"EVT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    append_tracking_event({
        "event_id": event_id,
        "tracking_number": tracking,
        "event_type": "付款完成",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "location": "線上",
        "operator": request.user.get("username"),
        "description": f"支付金額: {amount_val} 元"
    })

    return jsonify(
        {
            "message": "金額已更新",
            "tracking_number": tracking,
            "amount": amount_val,
        }
    )


# ------------------------------------------------
# 更新包裹狀態（進階查詢預用）✅ 關鍵修改
# ------------------------------------------------
@app.route("/api/parcels/status", methods=["POST"])
@token_required
def set_parcel_status():
    role = request.user.get("role")
    if role == "customer":
        return jsonify({"error": "客戶無權修改包裹狀態"}), 403

    data = request.get_json() or {}
    tracking = data.get("tracking_number") or data.get("tracking_no")
    status = (data.get("status") or "").strip()
    
    # ✅ 新增: 允許輸入額外資訊
    location = data.get("location", "")
    vehicle_id = data.get("vehicle_id", "")
    warehouse_id = data.get("warehouse_id", "")
    description = data.get("description", "")

    if not tracking:
        return jsonify({"error": "缺少追蹤編號"}), 400
    if not status:
        return jsonify({"error": "缺少狀態"}), 400

    ok = update_parcel_status(tracking, status)
    if not ok:
        return jsonify({"error": "找不到該追蹤編號"}), 404

    # ✅ 同時記錄事件到 TrackingEvents 表
    event_id = f"EVT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    append_tracking_event({
        "event_id": event_id,
        "tracking_number": tracking,
        "event_type": status,
        "timestamp": timestamp,
        "location": location,
        "vehicle_id": vehicle_id,
        "warehouse_id": warehouse_id,
        "operator": request.user.get("username"),
        "description": description or f"狀態變更為: {status}"
    })

    return jsonify(
        {
            "message": "狀態已更新並記錄事件", 
            "tracking_number": tracking, 
            "status": status
        }
    )


# ------------------------------------------------
# ✅ 新增: 查詢包裹完整歷史
# ------------------------------------------------
@app.route("/api/parcels/<tracking_no>/history", methods=["GET"])
@token_required
def get_parcel_history(tracking_no):
    """查詢包裹的完整物流歷史"""
    events = read_tracking_events(tracking_no)
    
    if not events:
        return jsonify({"message": "查無追蹤紀錄", "events": []}), 200
    
    return jsonify({
        "tracking_number": tracking_no,
        "events": events
    })


# ------------------------------------------------
# 進階查詢（search.html 用）
# ------------------------------------------------
@app.route("/records", methods=["GET"])
@token_required
def list_records():
    current_user = request.user
    role = current_user.get("role")
    username = current_user.get("username")
    
    # 取得前端傳來的搜尋條件
    vehicle_filter = request.args.get("vehicle_id")
    warehouse_filter = request.args.get("warehouse_id")

    parcels = read_parcels() or []

    # 權限過濾：如果是客戶，只能看自己的
    if role == "customer":
        parcels = [p for p in parcels if p.get("sender_id") == username]
    
    # ✅ 進階搜尋邏輯
    # 如果使用者有輸入「車輛ID」或「倉儲ID」，我們就要去事件表反查
    allowed_tracking_nums = None
    
    if vehicle_filter or warehouse_filter:
        all_events = read_all_events_for_search()
        allowed_tracking_nums = set()
        
        for e in all_events:
            # 檢查車輛 ID 是否符合
            if vehicle_filter and vehicle_filter.lower() in str(e.get("vehicle_id") or "").lower():
                allowed_tracking_nums.add(e["tracking_number"])
            # 檢查倉儲 ID 是否符合
            if warehouse_filter and warehouse_filter.lower() in str(e.get("warehouse_id") or "").lower():
                allowed_tracking_nums.add(e["tracking_number"])
    
    rows = []
    for p in parcels:
        # 如果有啟用進階搜尋，且這個包裹不在符合的名單內，就跳過
        if allowed_tracking_nums is not None:
            if p.get("tracking_number") not in allowed_tracking_nums:
                continue

        created_at = p.get("created_at") or ""
        date_only = created_at.split(" ")[0] if created_at else ""

        rows.append({
            "tracking_no": p.get("tracking_number"),
            "sender_id": p.get("sender_id"),
            "receiver_name": p.get("recipient_name"),
            "weight": p.get("weight"),
            "package_type": p.get("package_type", ""),
            "date": date_only,
            "amount": p.get("amount"),
            "status": p.get("status"),
        })

    return jsonify(rows)


# ------------------------------------------------
# Excel 下載
# ------------------------------------------------
@app.route("/api/download", methods=["GET"])
@token_required
def download_excel():
    role = request.user.get("role")
    if role == "customer":
        return jsonify({"error": "權限不足:客戶不可下載 Excel"}), 403

    initialize_excel()
    if not os.path.exists(EXCEL_FILE):
        return jsonify({"error": "找不到 Excel 檔案"}), 500

    return send_file(EXCEL_FILE, as_attachment=True)


# ------------------------------------------------
# 啟動前先初始化 Excel 與預設帳號
# ------------------------------------------------
initialize_excel()
init_default_accounts()

if __name__ == "__main__":
    app.run(debug=True)