"""Streamlit data-layer tests (TC-10..TC-12).

Exercises streamlit_app/db_ops.py directly against MySQL 8 on 127.0.0.1:3307:
authentication/RBAC, full order-to-refund lifecycle, and database-enforced
guards (late-return window, duplicate refund).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector  # noqa: E402
import pytest  # noqa: E402

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


def test_streamlit_auth_and_rbac():
    """TC-10: valid logins resolve 4 RBAC roles; wrong password is rejected."""
    admin = authenticate("admin_user", "password123")
    assert admin["role"] == "Admin"
    assert authenticate("customer_user", "password123")["role"] == "Customer"
    assert authenticate("support_agent", "password123")["role"] == "Support"
    assert authenticate("warehouse_op", "password123")["role"] == "Warehouse"
    with pytest.raises(AppError) as exc:
        authenticate("admin_user", "wrongpassword")
    assert "Invalid username or password" in str(exc.value)


def test_streamlit_full_lifecycle_via_db_ops():
    """TC-11: db_ops chain Order -> Requested -> Approved -> Received -> Inspected -> Refunded."""
    res = place_order(1, [{"product_id": 1, "quantity": 1}], actor="customer_user")
    order_id = res["order_id"]
    assert res["total_amount"] > 0

    det = order_detail(order_id)
    item_id = det["items"][0]["order_item_id"]

    return_id = request_return(order_id, 1, "Streamlit ops test",
                               [{"order_item_id": item_id, "quantity": 1}],
                               actor="customer_user")
    set_return_status(return_id, "Approved", actor="support_agent")
    set_return_status(return_id, "Received", actor="warehouse_op")
    inspect_return(return_id, "GOOD", "Streamlit test inspection", actor="warehouse_op")
    refund_id = process_refund(order_id, return_id, actor="support_agent")
    assert refund_id > 0

    det2 = order_detail(order_id)
    assert any(r["return_status"] == "Refunded" for r in det2["returns"])
    actors = [a["actor"] for a in audit_log(100)]
    assert "support_agent" in actors or "warehouse_op" in actors


def test_streamlit_guards_late_return_and_duplicate_refund():
    """TC-12: trigger blocks Order-3 late return; procedure blocks a second refund."""
    with pytest.raises(AppError) as exc:
        request_return(3, 3, "Late test", [{"order_item_id": 3, "quantity": 1}],
                       actor="customer_user")
    assert "Return window expired" in str(exc.value)

    res = place_order(2, [{"product_id": 2, "quantity": 1}], actor="admin_user")
    order_id = res["order_id"]
    item_id = order_detail(order_id)["items"][0]["order_item_id"]
    return_id = request_return(order_id, 2, "Duplicate guard test",
                               [{"order_item_id": item_id, "quantity": 1}], actor="admin_user")
    set_return_status(return_id, "Approved", actor="admin_user")
    set_return_status(return_id, "Received", actor="admin_user")
    inspect_return(return_id, "GOOD", "notes", actor="admin_user")
    process_refund(order_id, return_id, actor="admin_user")
    with pytest.raises(AppError) as exc2:
        process_refund(order_id, return_id, actor="admin_user")
    assert "uplicate refund" in str(exc2.value) or "Inspected state" in str(exc2.value)


def test_streamlit_catalog_and_analytics_queries():
    """Sanity: catalogue and analytical reports return rows."""
    assert len(list_products()) >= 5
    assert len(report_return_rates()) >= 5
