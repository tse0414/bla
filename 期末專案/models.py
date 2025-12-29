from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# 建立資料庫引擎 (SQLite)
DATABASE_URL = "sqlite:///logistics.db"
engine = create_engine(DATABASE_URL, echo=False)

Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# ================================================
# 1. 帳號表
# ================================================
class Account(Base):
    __tablename__ = "accounts"
    
    username = Column(String(50), primary_key=True)
    password = Column(String(255), nullable=False)  # 實際應該加密
    role = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 關聯
    customer = relationship("Customer", back_populates="account_ref", uselist=False)
    parcels_sent = relationship("Parcel", back_populates="sender")


# ================================================
# 2. 客戶表
# ================================================
class Customer(Base):
    __tablename__ = "customers"
    
    account = Column(String(50), ForeignKey("accounts.username"), primary_key=True)
    name = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(String(255))
    customer_type = Column(String(20), default="NON_CONTRACT")
    billing_preference = Column(String(20), default="COD")
    created_at = Column(DateTime, default=datetime.now)
    
    # 關聯
    account_ref = relationship("Account", back_populates="customer")


# ================================================
# 3. 包裹表
# ================================================
class Parcel(Base):
    __tablename__ = "parcels"
    
    tracking_number = Column(String(50), primary_key=True)
    sender_id = Column(String(50), ForeignKey("accounts.username"), nullable=False)
    recipient_name = Column(String(100), nullable=False)
    recipient_address = Column(String(255))
    weight = Column(Float)
    package_type = Column(String(50), default="中型箱")
    declared_value = Column(Float, default=0)
    contents = Column(String(255), default="一般貨物")
    service_type = Column(String(50))
    status = Column(String(50), default="建立包裹")
    amount = Column(Float)
    payment_status = Column(String(50), default="Unpaid")
    created_at = Column(DateTime, default=datetime.now)
    
    # 關聯
    sender = relationship("Account", back_populates="parcels_sent")
    events = relationship("TrackingEvent", back_populates="parcel", cascade="all, delete-orphan")


# ================================================
# 4. 物流事件表
# ================================================
class TrackingEvent(Base):
    __tablename__ = "tracking_events"
    
    event_id = Column(String(50), primary_key=True)
    tracking_number = Column(String(50), ForeignKey("parcels.tracking_number"), nullable=False)
    event_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    location = Column(String(100))
    vehicle_id = Column(String(50))
    warehouse_id = Column(String(50))
    operator = Column(String(50))
    description = Column(String(500))
    
    # 關聯
    parcel = relationship("Parcel", back_populates="events")


# ================================================
# 初始化資料庫
# ================================================
def init_database():
    """建立所有資料表"""
    Base.metadata.create_all(engine)
    print("✅ 資料庫初始化完成")


def get_db():
    """取得資料庫 session (用於 API)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # 直接執行此檔案可建立資料庫
    init_database()