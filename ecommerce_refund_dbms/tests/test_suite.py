import pytest
import mysql.connector
import threading
import time
import requests
from backend.database import get_db_connection

API_BASE = "http://127.0.0.1:8000"

@pytest.fixture(scope="module")
def db_conn():
    conn = get_db_connection()
    yield conn
    conn.close()

# ============================================================================
# 1. CONSTRAINT TESTS
# ============================================================================
def test_constraint_invalid_quantity(db_conn):
    """Assert CHECK constraint blocks quantity <= 0"""
    cursor = db_conn.cursor()
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase) VALUES (1, 1, 0, 100.00)")
    assert "CHECK" in str(exc_info.value) or "constraint" in str(exc_info.value).lower() or "0" in str(exc_info.value)
    cursor.close()

def test_constraint_negative_amount(db_conn):
    """Assert CHECK constraint blocks negative price / total amount"""
    cursor = db_conn.cursor()
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("INSERT INTO Orders (customer_id, total_amount, order_status) VALUES (1, -50.00, 'Pending')")
    assert "CHECK" in str(exc_info.value) or "constraint" in str(exc_info.value).lower()
    cursor.close()

def test_constraint_duplicate_provider_reference(db_conn):
    """Assert UNIQUE constraint blocks duplicate provider_reference"""
    cursor = db_conn.cursor()
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("INSERT INTO Payment (order_id, provider_reference, amount) VALUES (1, 'PAY-DEMO-001', 199.99)")
    assert "Duplicate entry" in str(exc_info.value)
    cursor.close()

def test_constraint_bad_status_enum(db_conn):
    """Assert ENUM domain restriction blocks invalid status values"""
    cursor = db_conn.cursor()
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("INSERT INTO ReturnRequest (order_id, customer_id, reason, return_status) VALUES (1, 1, 'Test', 'SuperStatus')")
    assert "Truncated" in str(exc_info.value) or "Data truncated" in str(exc_info.value) or "enum" in str(exc_info.value).lower()
    cursor.close()

def test_constraint_fk_restrict(db_conn):
    """Assert ON DELETE RESTRICT blocks deleting Customer with active orders"""
    cursor = db_conn.cursor()
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("DELETE FROM Customer WHERE customer_id = 1")
    assert "foreign key constraint" in str(exc_info.value).lower()
    cursor.close()

# ============================================================================
# 2. UNIT TESTS (sp_process_refund & triggers)
# ============================================================================
def test_unit_sp_process_refund_validation(db_conn):
    """Unit test sp_process_refund rejects return not in Inspected state"""
    cursor = db_conn.cursor()
    # Order #5, Return #2 is in 'Approved' state (not Inspected)
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.callproc("sp_process_refund", (5, 2, 'unit_test', 0))
    assert "Inspected state" in str(exc_info.value)
    cursor.close()

# ============================================================================
# 3. INTEGRATION TESTS (Full API Lifecycle)
# ============================================================================
def test_integration_full_lifecycle():
    """API-to-database full lifecycle: order -> return -> approval -> inspection -> refund"""
    # 1. Login as Admin
    login_res = requests.post(f"{API_BASE}/api/auth/login", json={"username": "admin_user", "password": "password123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Place Order
    order_res = requests.post(f"{API_BASE}/api/orders", json={"items": [{"product_id": 1, "quantity": 1}]}, headers=headers)
    assert order_res.status_code == 201
    order_id = order_res.json()["order_id"]

    # Get order item id
    status_res = requests.get(f"{API_BASE}/api/orders/{order_id}/status", headers=headers)
    item_id = status_res.json()["items"][0]["order_item_id"]

    # 3. Submit Return Request
    ret_res = requests.post(f"{API_BASE}/api/returns", json={"order_id": order_id, "reason": "Defective item", "items": [{"order_item_id": item_id, "quantity": 1}]}, headers=headers)
    assert ret_res.status_code == 201
    return_id = ret_res.json()["return_id"]

    # 4. Support Approve Return
    appr_res = requests.put(f"{API_BASE}/api/returns/{return_id}/approve?action=approve", headers=headers)
    assert appr_res.status_code == 200

    # 5. Warehouse Receive Return
    rec_res = requests.put(f"{API_BASE}/api/returns/{return_id}/receive", headers=headers)
    assert rec_res.status_code == 200

    # 6. Warehouse Inspect Return
    insp_res = requests.put(f"{API_BASE}/api/returns/{return_id}/inspect", json={"condition_status": "GOOD", "notes": "Verified good"}, headers=headers)
    assert insp_res.status_code == 200

    # 7. Process Refund via Stored Procedure
    ref_res = requests.post(f"{API_BASE}/api/returns/{return_id}/refund", headers=headers)
    assert ref_res.status_code == 200
    assert ref_res.json()["status"] == "Refunded"

# ============================================================================
# 4. FAILURE & ROLLBACK TESTS
# ============================================================================
def test_failure_rollback_on_procedure_error(db_conn):
    """Force an error mid sp_process_refund and assert complete transaction rollback"""
    cursor = db_conn.cursor(dictionary=True)
    # Attempt refund on invalid return_id 99999
    with pytest.raises(mysql.connector.Error):
        cursor.callproc("sp_process_refund", (99999, 99999, 'test_rollback', 0))
    
    # Assert no partial Refund record created for return 99999
    cursor.execute("SELECT COUNT(*) AS cnt FROM Refund WHERE return_id = 99999")
    assert cursor.fetchone()["cnt"] == 0
    cursor.close()

# ============================================================================
# 5. CONCURRENCY TESTS
# ============================================================================
def test_concurrency_duplicate_refund_attempts():
    """Parallel competing threads attempting duplicate refund; assert EXACTLY 1 succeeds"""
    login_res = requests.post(f"{API_BASE}/api/auth/login", json={"username": "admin_user", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup a new inspected return
    order_res = requests.post(f"{API_BASE}/api/orders", json={"items": [{"product_id": 2, "quantity": 1}]}, headers=headers)
    order_id = order_res.json()["order_id"]
    status_res = requests.get(f"{API_BASE}/api/orders/{order_id}/status", headers=headers)
    item_id = status_res.json()["items"][0]["order_item_id"]

    ret_res = requests.post(f"{API_BASE}/api/returns", json={"order_id": order_id, "reason": "Concurrency test", "items": [{"order_item_id": item_id, "quantity": 1}]}, headers=headers)
    return_id = ret_res.json()["return_id"]

    requests.put(f"{API_BASE}/api/returns/{return_id}/approve?action=approve", headers=headers)
    requests.put(f"{API_BASE}/api/returns/{return_id}/receive", headers=headers)
    requests.put(f"{API_BASE}/api/returns/{return_id}/inspect", json={"condition_status": "GOOD"}, headers=headers)

    results = []

    def call_refund():
        res = requests.post(f"{API_BASE}/api/returns/{return_id}/refund", headers=headers)
        results.append(res.status_code)

    t1 = threading.Thread(target=call_refund)
    t2 = threading.Thread(target=call_refund)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Assert exactly one 200 OK and one 400 Bad Request (Duplicate refund prevented)
    assert 200 in results
    assert 400 in results
    assert results.count(200) == 1
