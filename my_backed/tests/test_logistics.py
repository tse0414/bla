"""
物流管理系統 - Pytest 測試套件
執行方式: pytest test_logistics.py -v
"""
import pytest
from datetime import datetime
from src.Logistics_system import (
    CustomerType, BillingPreference, ServiceType, PackageStatus, 
    SpecialMarker, UserRole,
    Customer, Package, TrackingEvent, PricingRule,
    CustomerManager, PackageManager, TrackingManager, 
    BillingManager, AccessControlManager
)


# ========== Fixtures ==========
@pytest.fixture
def customer_manager():
    """客戶管理器 fixture"""
    return CustomerManager()


@pytest.fixture
def package_manager():
    """包裹管理器 fixture"""
    return PackageManager()


@pytest.fixture
def tracking_manager(package_manager):
    """追蹤管理器 fixture"""
    return TrackingManager(package_manager)


@pytest.fixture
def billing_manager(package_manager, customer_manager):
    """計費管理器 fixture"""
    return BillingManager(package_manager, customer_manager)


@pytest.fixture
def access_control():
    """權限控制 fixture"""
    return AccessControlManager()


@pytest.fixture
def sample_customer(customer_manager):
    """建立測試客戶"""
    return customer_manager.create_customer(
        name="張三",
        address="台北市信義區信義路一號",
        phone="0912345678",
        email="zhang@example.com"
    )


@pytest.fixture
def sample_package(package_manager, sample_customer):
    """建立測試包裹"""
    package = package_manager.create_package(
        sender_id=sample_customer.customer_id,
        recipient_name="李四",
        recipient_address="新北市板橋區中山路二段123號"
    )
    package_manager.update_package_attributes(
        tracking_number=package.tracking_number,
        weight=2.5,
        length=30.0,
        width=20.0,
        height=10.0,
        declared_value=1000.0,
        description="3C產品"
    )
    return package


# ========== 客戶管理測試 ==========
class TestCustomerManager:
    """測試客戶管理功能"""

    def test_create_customer(self, customer_manager):
        """測試建立客戶檔案"""
        customer = customer_manager.create_customer(
            name="王五",
            address="高雄市前鎮區中正路100號",
            phone="0923456789",
            email="wang@example.com"
        )
        
        assert customer.name == "王五"
        assert customer.phone == "0923456789"
        assert customer.customer_type == CustomerType.NON_CONTRACT
        assert customer.customer_id in customer_manager.customers

    def test_get_customer(self, customer_manager, sample_customer):
        """測試取得客戶資料"""
        retrieved = customer_manager.get_customer(sample_customer.customer_id)
        
        assert retrieved is not None
        assert retrieved.name == sample_customer.name
        assert retrieved.email == sample_customer.email

    def test_get_nonexistent_customer(self, customer_manager):
        """測試取得不存在的客戶"""
        retrieved = customer_manager.get_customer("nonexistent_id")
        assert retrieved is None

    def test_update_customer_type(self, customer_manager, sample_customer):
        """測試設定客戶類型"""
        success = customer_manager.update_customer_type(
            sample_customer.customer_id, 
            CustomerType.CONTRACT
        )
        
        assert success is True
        assert sample_customer.customer_type == CustomerType.CONTRACT

    def test_update_billing_preference(self, customer_manager, sample_customer):
        """測試設定帳單偏好"""
        success = customer_manager.update_billing_preference(
            sample_customer.customer_id,
            BillingPreference.MONTHLY
        )
        
        assert success is True
        assert sample_customer.billing_preference == BillingPreference.MONTHLY

    def test_update_nonexistent_customer(self, customer_manager):
        """測試更新不存在的客戶"""
        success = customer_manager.update_customer_type(
            "nonexistent_id",
            CustomerType.PREPAID
        )
        assert success is False


# ========== 包裹管理測試 ==========
class TestPackageManager:
    """測試包裹管理功能"""

    def test_create_package(self, package_manager):
        """測試建立包裹並產生追蹤編號"""
        package = package_manager.create_package(
            sender_id="customer123",
            recipient_name="收件人",
            recipient_address="收件地址"
        )
        
        assert package.tracking_number.startswith("TRK")
        assert len(package.tracking_number) > 10
        assert package.sender_id == "customer123"
        assert package.status == PackageStatus.CREATED

    def test_tracking_number_uniqueness(self, package_manager):
        """測試追蹤編號唯一性"""
        package1 = package_manager.create_package("s1", "r1", "a1")
        package2 = package_manager.create_package("s2", "r2", "a2")
        
        assert package1.tracking_number != package2.tracking_number

    def test_update_package_attributes(self, package_manager, sample_package):
        """測試記錄包裹屬性"""
        success = package_manager.update_package_attributes(
            tracking_number=sample_package.tracking_number,
            weight=5.0,
            length=40.0,
            width=30.0,
            height=20.0,
            declared_value=2000.0,
            description="更新後的描述"
        )
        
        assert success is True
        assert sample_package.weight == 5.0
        assert sample_package.length == 40.0
        assert sample_package.declared_value == 2000.0

    def test_add_special_marker(self, package_manager, sample_package):
        """測試新增特殊標記"""
        success = package_manager.add_special_marker(
            sample_package.tracking_number,
            SpecialMarker.FRAGILE
        )
        
        assert success is True
        assert SpecialMarker.FRAGILE in sample_package.special_markers

    def test_add_multiple_special_markers(self, package_manager, sample_package):
        """測試新增多個特殊標記"""
        package_manager.add_special_marker(
            sample_package.tracking_number,
            SpecialMarker.FRAGILE
        )
        package_manager.add_special_marker(
            sample_package.tracking_number,
            SpecialMarker.DANGEROUS
        )
        
        assert len(sample_package.special_markers) == 2
        assert SpecialMarker.FRAGILE in sample_package.special_markers
        assert SpecialMarker.DANGEROUS in sample_package.special_markers

    def test_calculate_volume_weight(self, sample_package):
        """測試體積重量計算"""
        # 30 * 20 * 10 / 5000 = 1.2 kg
        volume_weight = sample_package.calculate_volume_weight()
        assert volume_weight == 1.2

    def test_calculate_shipping_cost_standard(self, package_manager, sample_package):
        """測試標準配送費用計算"""
        cost = package_manager.calculate_shipping_cost(sample_package.tracking_number)
        
        # 重量 2.5kg > 體積重 1.2kg, 取 2.5kg
        # 標準配送費率 5.0 * 2.5 = 12.5
        assert cost == 12.5

    def test_calculate_shipping_cost_with_markers(self, package_manager, sample_package):
        """測試含附加費的運費計算"""
        package_manager.add_special_marker(
            sample_package.tracking_number,
            SpecialMarker.FRAGILE
        )
        
        cost = package_manager.calculate_shipping_cost(sample_package.tracking_number)
        
        # 基本費 12.5 + 易碎品費 10.0 = 22.5
        assert cost == 22.5

    def test_calculate_shipping_cost_express(self, package_manager, sample_package):
        """測試快速配送費用"""
        sample_package.service_type = ServiceType.EXPRESS
        cost = package_manager.calculate_shipping_cost(sample_package.tracking_number)
        
        # 快速配送費率 8.0 * 2.5 = 20.0
        assert cost == 20.0


# ========== 追蹤管理測試 ==========
class TestTrackingManager:
    """測試物流事件追蹤功能"""

    def test_start_tracking(self, tracking_manager, sample_package):
        """測試啟動包裹追蹤"""
        success = tracking_manager.start_tracking(
            sample_package.tracking_number,
            "台北物流中心"
        )
        
        assert success is True
        assert sample_package.status == PackageStatus.PICKUP
        assert sample_package.tracking_number in tracking_manager.tracking_events

    def test_record_event(self, tracking_manager, sample_package):
        """測試記錄追蹤事件"""
        success = tracking_manager.record_event(
            sample_package.tracking_number,
            PackageStatus.IN_TRANSIT,
            "台中轉運站",
            "正常運輸中"
        )
        
        assert success is True
        assert sample_package.status == PackageStatus.IN_TRANSIT

    def test_record_multiple_events(self, tracking_manager, sample_package):
        """測試記錄多個追蹤事件"""
        tracking_manager.start_tracking(sample_package.tracking_number, "台北")
        tracking_manager.record_event(
            sample_package.tracking_number,
            PackageStatus.IN_TRANSIT,
            "台中"
        )
        tracking_manager.record_event(
            sample_package.tracking_number,
            PackageStatus.AT_FACILITY,
            "高雄物流中心"
        )
        
        events = tracking_manager.tracking_events[sample_package.tracking_number]
        assert len(events) == 3
        assert events[-1].location == "高雄物流中心"

    def test_record_delivery(self, tracking_manager, sample_package):
        """測試記錄投遞與簽收"""
        success = tracking_manager.record_delivery(
            sample_package.tracking_number,
            "收件地址",
            "李四"
        )
        
        assert success is True
        assert sample_package.status == PackageStatus.DELIVERED
        
        events = tracking_manager.tracking_events[sample_package.tracking_number]
        assert "簽收人:李四" in events[-1].notes

    def test_get_current_status(self, tracking_manager, sample_package):
        """測試查詢包裹目前狀態"""
        tracking_manager.start_tracking(sample_package.tracking_number, "起點")
        tracking_manager.record_event(
            sample_package.tracking_number,
            PackageStatus.OUT_FOR_DELIVERY,
            "配送站"
        )
        
        status = tracking_manager.get_current_status(sample_package.tracking_number)
        
        assert status is not None
        assert status["status"] == PackageStatus.OUT_FOR_DELIVERY.value
        assert status["location"] == "配送站"
        assert "tracking_number" in status
        assert "timestamp" in status

    def test_get_tracking_history(self, tracking_manager, sample_package):
        """測試查詢完整追蹤歷史"""
        tracking_manager.start_tracking(sample_package.tracking_number, "台北")
        tracking_manager.record_event(
            sample_package.tracking_number,
            PackageStatus.IN_TRANSIT,
            "台中"
        )
        tracking_manager.record_delivery(
            sample_package.tracking_number,
            "高雄",
            "收件人"
        )
        
        history = tracking_manager.get_tracking_history(sample_package.tracking_number)
        
        assert len(history) == 3
        assert history[0]["status"] == PackageStatus.PICKUP.value
        assert history[-1]["status"] == PackageStatus.DELIVERED.value

    def test_get_nonexistent_tracking(self, tracking_manager):
        """測試查詢不存在的追蹤號"""
        status = tracking_manager.get_current_status("INVALID")
        assert status is None
        
        history = tracking_manager.get_tracking_history("INVALID")
        assert history == []


# ========== 計費管理測試 ==========
class TestBillingManager:
    """測試計費與帳單功能"""

    def test_process_payment(self, billing_manager, sample_customer, sample_package):
        """測試付款處理"""
        record = billing_manager.process_payment(sample_package.tracking_number)
        
        assert record is not None
        assert record["tracking_number"] == sample_package.tracking_number
        assert record["customer_id"] == sample_customer.customer_id
        assert record["amount"] == 12.5
        assert "payment_status" in record

    def test_process_payment_prepaid_customer(
        self, billing_manager, customer_manager, sample_package
    ):
        """測試預付客戶付款處理"""
        customer_manager.update_customer_type(
            sample_package.sender_id,
            CustomerType.PREPAID
        )
        
        record = billing_manager.process_payment(sample_package.tracking_number)
        
        assert record["payment_status"] == "已付款"

    def test_process_payment_cod(
        self, billing_manager, customer_manager, sample_package
    ):
        """測試貨到付款處理"""
        customer_manager.update_billing_preference(
            sample_package.sender_id,
            BillingPreference.COD
        )
        
        record = billing_manager.process_payment(sample_package.tracking_number)
        
        assert record["payment_status"] == "貨到付款"

    def test_get_customer_shipments(
        self, billing_manager, package_manager, sample_customer
    ):
        """測試列出客戶貨件與費用"""
        # 建立多個包裹
        pkg1 = package_manager.create_package(
            sample_customer.customer_id, "收件人1", "地址1"
        )
        pkg2 = package_manager.create_package(
            sample_customer.customer_id, "收件人2", "地址2"
        )
        
        package_manager.update_package_attributes(
            pkg1.tracking_number, 1.0, 10, 10, 10, 100, "物品1"
        )
        package_manager.update_package_attributes(
            pkg2.tracking_number, 2.0, 20, 20, 20, 200, "物品2"
        )
        
        billing_manager.process_payment(pkg1.tracking_number)
        billing_manager.process_payment(pkg2.tracking_number)
        
        shipments = billing_manager.get_customer_shipments(sample_customer.customer_id)
        
        assert len(shipments) == 2
        assert all(s["customer_id"] == sample_customer.customer_id for s in shipments)


# ========== 權限控制測試 ==========
class TestAccessControl:
    """測試權限與安全功能"""

    def test_create_user(self, access_control):
        """測試建立使用者"""
        user_id = access_control.create_user("admin_user", UserRole.ADMIN)
        
        assert user_id in access_control.users
        assert access_control.users[user_id]["username"] == "admin_user"
        assert access_control.users[user_id]["role"] == UserRole.ADMIN

    def test_admin_permissions(self, access_control):
        """測試管理員權限"""
        admin_id = access_control.create_user("admin", UserRole.ADMIN)
        
        assert access_control.check_permission(admin_id, "create_package")
        assert access_control.check_permission(admin_id, "view_package")
        assert access_control.check_permission(admin_id, "update_tracking")

    def test_customer_service_permissions(self, access_control):
        """測試客服人員權限"""
        cs_id = access_control.create_user("cs_agent", UserRole.CUSTOMER_SERVICE)
        
        assert access_control.check_permission(cs_id, "create_package")
        assert access_control.check_permission(cs_id, "view_package")
        assert not access_control.check_permission(cs_id, "unauthorized_action")

    def test_warehouse_permissions(self, access_control):
        """測試倉儲人員權限"""
        wh_id = access_control.create_user("warehouse", UserRole.WAREHOUSE)
        
        assert access_control.check_permission(wh_id, "update_tracking")
        assert access_control.check_permission(wh_id, "add_marker")
        assert not access_control.check_permission(wh_id, "create_customer")

    def test_driver_permissions(self, access_control):
        """測試駕駛員權限"""
        driver_id = access_control.create_user("driver", UserRole.DRIVER)
        
        assert access_control.check_permission(driver_id, "update_tracking")
        assert access_control.check_permission(driver_id, "view_package")
        assert not access_control.check_permission(driver_id, "create_package")

    def test_customer_permissions(self, access_control):
        """測試客戶權限"""
        customer_id = access_control.create_user("customer", UserRole.CUSTOMER)
        
        assert access_control.check_permission(customer_id, "view_own_package")
        assert not access_control.check_permission(customer_id, "create_package")
        assert not access_control.check_permission(customer_id, "update_tracking")


# ========== 整合測試 ==========
class TestIntegration:
    """測試完整流程整合"""

    def test_complete_shipping_flow(
        self, customer_manager, package_manager, tracking_manager, billing_manager
    ):
        """測試完整寄送流程"""
        # 1. 建立客戶
        customer = customer_manager.create_customer(
            "測試客戶", "測試地址", "0900000000", "test@test.com"
        )
        customer_manager.update_customer_type(customer.customer_id, CustomerType.CONTRACT)
        
        # 2. 建立包裹
        package = package_manager.create_package(
            customer.customer_id, "收件人", "收件地址"
        )
        package_manager.update_package_attributes(
            package.tracking_number, 3.0, 30, 30, 30, 1500, "測試物品"
        )
        package_manager.add_special_marker(
            package.tracking_number, SpecialMarker.FRAGILE
        )
        
        # 3. 追蹤流程
        tracking_manager.start_tracking(package.tracking_number, "寄件地")
        tracking_manager.record_event(
            package.tracking_number, PackageStatus.IN_TRANSIT, "轉運站"
        )
        tracking_manager.record_event(
            package.tracking_number, PackageStatus.OUT_FOR_DELIVERY, "配送站"
        )
        tracking_manager.record_delivery(
            package.tracking_number, "收件地", "收件人"
        )
        
        # 4. 計費
        billing_record = billing_manager.process_payment(package.tracking_number)
        
        # 驗證
        assert package.status == PackageStatus.DELIVERED
        assert billing_record["amount"] > 0
        
        history = tracking_manager.get_tracking_history(package.tracking_number)
        assert len(history) == 4
        assert history[-1]["status"] == PackageStatus.DELIVERED.value


# ========== 執行測試 ==========
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])