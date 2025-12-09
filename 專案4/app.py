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
)

app = Flask(__name__)
CORS(app)

SECRET_KEY = "my_secret_key_for_jwt_12345"


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
# 模擬帳號資料
# ------------------------------------------------
ACCOUNTS = {
    "staff1": {"password": "staff123", "role": "staff"},
    "admin1": {"password": "admin123", "role": "admin"},
}
# 客戶會透過 /api/auth/register 加進來（存在記憶體）


# ------------------------------------------------
# 登入
# ------------------------------------------------
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "請提供帳號與密碼"}), 400

    if username not in ACCOUNTS:
        return jsonify({"error": "帳號不存在"}), 401

    if ACCOUNTS[username]["password"] != password:
        return jsonify({"error": "密碼錯誤"}), 401

    token = jwt.encode(
        {
            "username": username,
            "role": ACCOUNTS[username]["role"],
            "exp": datetime.utcnow() + timedelta(hours=4),
        },
        SECRET_KEY,
        algorithm="HS256",
    )

    return jsonify(
        {
            "message": "登入成功",
            "username": username,
            "role": ACCOUNTS[username]["role"],
            "token": token,
        }
    )


# ------------------------------------------------
# 客戶註冊（同時寫入 Customers）
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

    if not username or not password:
        return jsonify({"error": "請提供帳號與密碼"}), 400

    if username in ACCOUNTS:
        return jsonify({"error": "帳號已存在"}), 400

    ACCOUNTS[username] = {
        "password": password,
        "role": "customer",
        "name": name,
        "phone": phone,
        "email": email,
        "address": address,
    }

    append_customer(
        {
            "account": username,
            "name": name,
            "phone": phone,
            "email": email,
            "address": address,
        }
    )

    return jsonify({"message": "註冊成功", "username": username})


# ------------------------------------------------
# 客戶資料：建立 / 查看 / 修改
# ------------------------------------------------
# （建立）只有 staff / admin 可以透過後台新增客戶
@app.route("/api/customers", methods=["POST"])
@token_required
def create_customer():
    if request.user.get("role") not in ["staff", "admin"]:
        return jsonify({"error": "權限不足"}), 403

    data = request.get_json() or {}
    append_customer(data)

    return jsonify(
        {"message": "客戶已建立", "customer_id": data.get("account")}
    )


# （查看全部）staff / admin 可查看所有客戶資料
@app.route("/api/customers", methods=["GET"])
@token_required
def list_customers():
    role = request.user.get("role")
    if role not in ["staff", "admin"]:
        return jsonify({"error": "權限不足"}), 403

    customers = read_customers() or []
    return jsonify(customers)


# （修改）只有 admin 可以修改客戶資料
@app.route("/api/customers/<account>", methods=["PUT"])
@token_required
def edit_customer(account):
    if request.user.get("role") != "admin":
        return jsonify({"error": "只有管理員可以修改客戶資料"}), 403

    data = request.get_json() or {}
    update_customer(account, data)

    return jsonify({"message": "客戶資料已更新"})


# ------------------------------------------------
# 建立包裹
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
    service_type = data.get("service_type") or "標準速遞"

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
        "service_type": service_type,
        "status": "建立包裹",
        "amount": None,
        "created_at": created_at,
    }

    append_parcel(record)

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

    return jsonify(
        {
            "message": "金額已更新",
            "tracking_number": tracking,
            "amount": amount_val,
        }
    )


# ------------------------------------------------
# 進階查詢（search.html 用）
# ------------------------------------------------
@app.route("/records", methods=["GET"])
def list_records():
    parcels = read_parcels() or []

    rows = []
    for p in parcels:
        created_at = p.get("created_at") or ""
        date_only = created_at.split(" ")[0] if created_at else ""

        rows.append(
            {
                "tracking_no": p.get("tracking_number"),
                "sender_id": p.get("sender_id"),
                "receiver_name": p.get("recipient_name"),
                "weight": p.get("weight"),
                "volume": "",
                "date": date_only,
                "amount": p.get("amount"),
            }
        )

    return jsonify(rows)


# ------------------------------------------------
# Excel 下載
# ------------------------------------------------
@app.route("/api/download", methods=["GET"])
def download_excel():
    initialize_excel()
    if not os.path.exists(EXCEL_FILE):
        return jsonify({"error": "找不到 Excel 檔案"}), 500

    return send_file(EXCEL_FILE, as_attachment=True)


# ------------------------------------------------
# 啟動前先初始化 Excel
# ------------------------------------------------
initialize_excel()

if __name__ == "__main__":
    app.run(debug=True)
