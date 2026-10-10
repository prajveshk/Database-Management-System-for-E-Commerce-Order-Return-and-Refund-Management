"""Streamlit application tests (TC-01..TC-10).

Exercises streamlit_app/db_ops.py and the database directly against
MySQL 8 on 127.0.0.1:3307: engine constraints, procedure guards, the full
order-to-refund lifecycle, rollback, duplicate prevention, and auth/RBAC.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector  # noqa: E402
import pytest  # noqa: E402

from streamlit_app.database import get_db_connection  # noqa: E402
from streamlit_app.db_ops import (  # noqa: E402
    AppError,
    audit_log,
    authenticate,
    inspect_return,
    list_products,
    order_detail,
    place_order,
    process_refund,
    report_return_rates,
    request_return,
    set_return_status,
)


@pytest.fixture()
def db_cur():
    conn = get_db_connection()
    cur = conn.cursor()
    yield cur
    try:
        conn.rollback()
    except Exception:
        pass
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# Constraints enforced by the engine (TC-01..TC-05)
# ---------------------------------------------------------------------------
def test_tc01_invalid_quantity_blocked(db_cur):
    """CHECK (quantity > 0): quantity = 0 is rejected."""
    with pytest.raises(mysql.connector.Error):
        db_cur.execute(
            "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase)"
            " VALUES (1, 1, 0, 100.00)")


def test_tc02_negative_amount_blocked(db_cur):
    """CHECK (total_amount >= 0): negative totals are rejected."""
    with pytest.raises(mysql.connector.Error):
        db_cur.execute(
            "INSERT INTO Orders (customer_id, total_amount, order_status)"
            " VALUES (1, -50.00, 'Pending')")


def test_tc03_duplicate_provider_reference_blocked(db_cur):
    """UNIQUE provider_reference: duplicate gateway refs are rejected."""
    db_cur.execute("SELECT provider_reference FROM Payment LIMIT 1")
    existing = db_cur.fetchone()[0]
    with pytest.raises(mysql.connector.Error) as exc:
        db_cur.execute(
            "INSERT INTO Payment (order_id, provider_reference, amount)"
            " VALUES (1, %s, 199.99)", (existing,))
    assert "Duplicate entry" in str(exc.value)


def test_tc04_bad_status_enum_blocked(db_cur):
    """ENUM domain: illegal return status values are rejected."""
    with pytest.raises(mysql.connector.Error):
        db_cur.execute(
            "INSERT INTO ReturnRequest (order_id, customer_id, reason, return_status)"
            " VALUES (1, 1, 'Test', 'SuperStatus')")


def test_tc05_fk_restrict_blocked(db_cur):
    """ON DELETE RESTRICT: customers with orders cannot be deleted."""
    with pytest.raises(mysql.connector.Error) as exc:
        db_cur.execute("DELETE FROM Customer WHERE customer_id = 1")
    assert "foreign key constraint" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Procedure guard, lifecycle, rollback, duplicates (TC-06..TC-09)
# ---------------------------------------------------------------------------
def test_tc06_refund_requires_inspected_state():
    """sp_process_refund rejects returns not in 'Inspected' state."""
    res = place_order(1, [{"product_id": 1, "quantity": 1}], actor="customer_user")
    order_id = res["order_id"]
    item_id = order_detail(order_id)["items"][0]["order_item_id"]
    return_id = request_return(order_id, 1, "TC-06 guard",
                               [{"order_item_id": item_id, "quantity": 1}],
                               actor="customer_user")
    with pytest.raises(AppError) as exc:
        process_refund(order_id, return_id, actor="support_agent")
    assert "Inspected state" in str(exc.value)


def test_tc07_full_lifecycle_via_db_ops():
    """Order -> Requested -> Approved -> Received -> Inspected -> Refunded + audit."""
    assert len(list_products()) >= 5
    res = place_order(1, [{"product_id": 1, "quantity": 1}], actor="customer_user")
    order_id = res["order_id"]
    assert res["total_amount"] > 0
    item_id = order_detail(order_id)["items"][0]["order_item_id"]
    return_id = request_return(order_id, 1, "TC-07 lifecycle",
                               [{"order_item_id": item_id, "quantity": 1}],
                               actor="customer_user")
    set_return_status(return_id, "Approved", actor="support_agent")
    set_return_status(return_id, "Received", actor="warehouse_op")
    inspect_return(return_id, "GOOD", "TC-07 inspection", actor="warehouse_op")
    refund_id = process_refund(order_id, return_id, actor="support_agent")
    assert refund_id > 0
    det = order_detail(order_id)
    assert any(r["return_status"] == "Refunded" for r in det["returns"])
    actors = [a["actor"] for a in audit_log(100)]
    assert "support_agent" in actors or "warehouse_op" in actors
    assert len(report_return_rates()) >= 5


def test_tc08_rollback_on_procedure_error(db_cur):
    """Failed refund leaves no orphan Refund rows (atomic rollback)."""
    with pytest.raises(AppError):
        process_refund(99999, 99999, actor="support_agent")
    db_cur.execute("SELECT COUNT(*) FROM Refund WHERE return_id = 99999")
    assert db_cur.fetchone()[0] == 0


def test_tc09_duplicate_refund_blocked():
    """Second refund on the same return is rejected (exactly-once)."""
    with pytest.raises(AppError) as exc:
        request_return(3, 3, "TC-09 late", [{"order_item_id": 3, "quantity": 1}],
                       actor="customer_user")
    assert "Return window expired" in str(exc.value)

    res = place_order(2, [{"product_id": 2, "quantity": 1}], actor="support_agent")
    order_id = res["order_id"]
    item_id = order_detail(order_id)["items"][0]["order_item_id"]
    return_id = request_return(order_id, 2, "TC-09 duplicate",
                               [{"order_item_id": item_id, "quantity": 1}],
                               actor="support_agent")
    set_return_status(return_id, "Approved", actor="support_agent")
    set_return_status(return_id, "Received", actor="warehouse_op")
    inspect_return(return_id, "GOOD", "TC-09 inspection", actor="warehouse_op")
    first = process_refund(order_id, return_id, actor="support_agent")
    assert first > 0
    with pytest.raises(AppError) as exc2:
        process_refund(order_id, return_id, actor="support_agent")
    assert "uplicate refund" in str(exc2.value) or "Inspected state" in str(exc2.value)


# ---------------------------------------------------------------------------
# Auth / RBAC (TC-10)
# ---------------------------------------------------------------------------
def test_tc10_auth_and_rbac():
    """bcrypt login resolves all 4 roles; wrong passwords are rejected."""
    assert authenticate("admin_user", "password123")["role"] == "Admin"
    assert authenticate("customer_user", "password123")["role"] == "Customer"
    assert authenticate("support_agent", "password123")["role"] == "Support"
    assert authenticate("warehouse_op", "password123")["role"] == "Warehouse"
    with pytest.raises(AppError):
        authenticate("admin_user", "wrongpassword")
