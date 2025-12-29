from models import (
    SessionLocal, Account, Customer, Parcel, TrackingEvent, init_database
)
from datetime import datetime

# ================================================
# 帳號管理
# ================================================
def append_account(account_data):
    """新增帳號"""
    db = SessionLocal()
    try:
        account = Account(
            username=account_data.get("username"),
            password=account_data.get("password"),  # 實際應加密
            role=account_data.get("role", "customer")
        )
        db.add(account)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"新增帳號失敗: {e}")
    finally:
        db.close()


def find_account(username):
    """查詢單一帳號"""
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.username == username).first()
        if account:
            return {
                "username": account.username,
                "password": account.password,
                "role": account.role,
                "created_at": account.created_at.strftime("%Y-%m-%d %H:%M:%S") if account.created_at else ""
            }
        return None
    finally:
        db.close()


def read_accounts():
    """讀取所有帳號"""
    db = SessionLocal()
    try:
        accounts = {}
        for account in db.query(Account).all():
            accounts[account.username] = {
                "password": account.password,
                "role": account.role,
                "created_at": account.created_at.strftime("%Y-%m-%d %H:%M:%S") if account.created_at else ""
            }
        return accounts
    finally:
        db.close()


# ================================================
# 客戶管理
# ================================================
def append_customer(data):
    """新增客戶"""
    db = SessionLocal()
    try:
        customer = Customer(
            account=data.get("account"),
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            address=data.get("address", ""),
            customer_type=data.get("customer_type", "NON_CONTRACT"),
            billing_preference=data.get("billing_preference", "COD")
        )
        db.add(customer)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"新增客戶失敗: {e}")
    finally:
        db.close()


def read_customers():
    """讀取所有客戶"""
    db = SessionLocal()
    try:
        result = []
        for c in db.query(Customer).all():
            result.append({
                "account": c.account,
                "name": c.name,
                "phone": c.phone,
                "email": c.email,
                "address": c.address,
                "customer_type": c.customer_type,
                "billing_preference": c.billing_preference,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else ""
            })
        return result
    finally:
        db.close()


def update_customer(account, data):
    """更新客戶資料"""
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.account == account).first()
        if customer:
            customer.name = data.get("name", customer.name)
            customer.phone = data.get("phone", customer.phone)
            customer.email = data.get("email", customer.email)
            customer.address = data.get("address", customer.address)
            customer.customer_type = data.get("customer_type", customer.customer_type)
            customer.billing_preference = data.get("billing_preference", customer.billing_preference)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"更新客戶失敗: {e}")
    finally:
        db.close()


# ================================================
# 包裹管理
# ================================================
def append_parcel(record):
    """新增包裹"""
    db = SessionLocal()
    try:
        parcel = Parcel(
            tracking_number=record.get("tracking_number"),
            sender_id=record.get("sender_id"),
            recipient_name=record.get("recipient_name"),
            recipient_address=record.get("recipient_address"),
            weight=record.get("weight"),
            package_type=record.get("package_type", "中型箱"),
            declared_value=record.get("declared_value", 0),
            contents=record.get("contents", "一般貨物"),
            service_type=record.get("service_type"),
            status=record.get("status", "建立包裹"),
            amount=record.get("amount"),
            payment_status=record.get("payment_status", "Unpaid")
        )
        db.add(parcel)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"新增包裹失敗: {e}")
    finally:
        db.close()


def read_parcels():
    """讀取所有包裹"""
    db = SessionLocal()
    try:
        parcels = []
        for p in db.query(Parcel).all():
            parcels.append({
                "tracking_number": p.tracking_number,
                "sender_id": p.sender_id,
                "recipient_name": p.recipient_name,
                "recipient_address": p.recipient_address,
                "weight": p.weight,
                "package_type": p.package_type,
                "declared_value": p.declared_value,
                "contents": p.contents,
                "service_type": p.service_type,
                "status": p.status,
                "amount": p.amount,
                "payment_status": p.payment_status,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else ""
            })
        return parcels
    finally:
        db.close()


def update_parcel_amount(tracking_number, amount):
    """更新包裹金額"""
    db = SessionLocal()
    try:
        parcel = db.query(Parcel).filter(Parcel.tracking_number == tracking_number).first()
        if parcel:
            parcel.amount = amount
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"更新金額失敗: {e}")
    finally:
        db.close()


def update_parcel_status(tracking_number, status):
    """更新包裹狀態"""
    db = SessionLocal()
    try:
        parcel = db.query(Parcel).filter(Parcel.tracking_number == tracking_number).first()
        if parcel:
            parcel.status = status
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"更新狀態失敗: {e}")
        return False
    finally:
        db.close()


def delete_parcel_by_tracking(tracking_number):
    """刪除包裹 (會自動刪除相關事件)"""
    db = SessionLocal()
    try:
        parcel = db.query(Parcel).filter(Parcel.tracking_number == tracking_number).first()
        if parcel:
            db.delete(parcel)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"刪除包裹失敗: {e}")
        return False
    finally:
        db.close()


# ================================================
# 物流事件追蹤
# ================================================
def append_tracking_event(event):
    """新增追蹤事件"""
    db = SessionLocal()
    try:
        tracking_event = TrackingEvent(
            event_id=event.get("event_id"),
            tracking_number=event.get("tracking_number"),
            event_type=event.get("event_type"),
            timestamp=datetime.strptime(event.get("timestamp"), "%Y-%m-%d %H:%M:%S") if isinstance(event.get("timestamp"), str) else event.get("timestamp"),
            location=event.get("location", ""),
            vehicle_id=event.get("vehicle_id", ""),
            warehouse_id=event.get("warehouse_id", ""),
            operator=event.get("operator", ""),
            description=event.get("description", "")
        )
        db.add(tracking_event)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"新增事件失敗: {e}")
    finally:
        db.close()


def read_tracking_events(tracking_number):
    """查詢包裹的完整追蹤歷史"""
    db = SessionLocal()
    try:
        events = []
        for e in db.query(TrackingEvent).filter(
            TrackingEvent.tracking_number == tracking_number
        ).order_by(TrackingEvent.timestamp.desc()).all():
            events.append({
                "event_id": e.event_id,
                "tracking_number": e.tracking_number,
                "event_type": e.event_type,
                "timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M:%S") if e.timestamp else "",
                "location": e.location,
                "vehicle_id": e.vehicle_id,
                "warehouse_id": e.warehouse_id,
                "operator": e.operator,
                "description": e.description
            })
        return events
    finally:
        db.close()


def read_all_events_for_search():
    """讀取所有事件 (用於搜尋)"""
    db = SessionLocal()
    try:
        events = []
        for e in db.query(TrackingEvent).all():
            events.append({
                "tracking_number": e.tracking_number,
                "vehicle_id": e.vehicle_id,
                "warehouse_id": e.warehouse_id
            })
        return events
    finally:
        db.close()


# ================================================
# 初始化
# ================================================
def initialize_database():
    """初始化資料庫 (建立資料表)"""
    init_database()


if __name__ == "__main__":
    initialize_database()
    print("✅ 資料庫操作層載入完成")