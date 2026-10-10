"""Direct database operations for the Streamlit application.

Every function uses parameterized SQL against the 3NF MySQL 8 schema
(db/schema.sql). Business rules (return window, quantity limits, state
machine, audit trail, atomic refunds) are enforced inside the database
by triggers and sp_process_refund - this module only surfaces their
error messages to the UI via AppError.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector  # noqa: E402
from backend.database import get_db_connection  # noqa: E402
from backend.auth import verify_password  # noqa: E402
from backend.payment_gateway import MockPaymentGateway  # noqa: E402


class AppError(Exception):
    """User-facing error carrying the database/business-rule message."""


def _msg(err):
    text = getattr(err, "msg", str(err))
    return text


def _set_actor(cur, actor):
    cur.execute("SET @current_app_user = %s", (actor,))


# ---------------------------------------------------------------------------
# Authentication / RBAC (mirrors POST /api/auth/login)
# ---------------------------------------------------------------------------
def authenticate(username, password):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT u.user_id, u.username, u.password_hash, u.customer_id, r.role_name
            FROM AppUser u
            JOIN Role r ON u.role_id = r.role_id
            WHERE u.username = %s
            """,
            (username,),
        )
        user = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not user or not verify_password(password, user["password_hash"]):
        raise AppError("Invalid username or password")
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role_name"],
        "customer_id": user["customer_id"],
    }


# ---------------------------------------------------------------------------
# Customer operations
# ---------------------------------------------------------------------------
def list_products():
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT product_id, name, current_price, return_window_days FROM Product ORDER BY product_id")
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def place_order(customer_id, items, actor):
    """items: [{'product_id': int, 'quantity': int}]. Returns order summary dict."""
    if not items:
        raise AppError("Order must contain at least one item")
    conn = get_db_connection()
    try:
        conn.autocommit = False
        cur = conn.cursor(dictionary=True)
        prepared = []
        total = 0.0
        for it in items:
            if int(it["quantity"]) <= 0:
                raise AppError("Quantity must be positive")
            cur.execute("SELECT current_price FROM Product WHERE product_id = %s", (it["product_id"],))
            prod = cur.fetchone()
            if not prod:
                raise AppError("Product ID %s not found" % it["product_id"])
            price = float(prod["current_price"])
            total += price * int(it["quantity"])
            prepared.append((it["product_id"], int(it["quantity"]), price))
        total = round(total, 2)
        cur.execute(
            "INSERT INTO Orders (customer_id, order_date, total_amount, order_status)"
            " VALUES (%s, NOW(), %s, 'Delivered')",
            (customer_id, total),
        )
        order_id = cur.lastrowid
        for pid, qty, price in prepared:
            cur.execute(
                "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase)"
                " VALUES (%s, %s, %s, %s)",
                (order_id, pid, qty, price),
            )
        pay = MockPaymentGateway.process_payment(total, order_id)
        cur.execute(
            "INSERT INTO Payment (order_id, provider_reference, amount, payment_status)"
            " VALUES (%s, %s, %s, 'Completed')",
            (order_id, pay["provider_reference"], total),
        )
        conn.commit()
        cur.close()
        return {"order_id": order_id, "total_amount": total,
                "provider_reference": pay["provider_reference"]}
    except AppError:
        conn.rollback()
        raise
    except mysql.connector.Error as err:
        conn.rollback()
        raise AppError(_msg(err))
    finally:
        conn.autocommit = True
        conn.close()


def my_orders(customer_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT o.order_id, o.order_date, o.total_amount, o.order_status,
                   p.provider_reference, p.payment_status
            FROM Orders o LEFT JOIN Payment p ON o.order_id = p.order_id
            WHERE o.customer_id = %s ORDER BY o.order_date DESC
            """,
            (customer_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def order_detail(order_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT o.order_id, o.customer_id, c.name AS customer_name, o.order_date,
                   o.total_amount, o.order_status, p.provider_reference, p.payment_status
            FROM Orders o JOIN Customer c ON o.customer_id = c.customer_id
            LEFT JOIN Payment p ON o.order_id = p.order_id
            WHERE o.order_id = %s
            """,
            (order_id,),
        )
        order = cur.fetchone()
        cur.execute(
            """
            SELECT oi.order_item_id, p.name AS product_name, oi.quantity, oi.unit_price_at_purchase
            FROM OrderItem oi JOIN Product p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
            """,
            (order_id,),
        )
        items = cur.fetchall()
        cur.execute(
            """
            SELECT rr.return_id, rr.reason, rr.return_status, rr.requested_at,
                   insp.condition_status, rf.refund_id, rf.amount AS refunded_amount, rf.refund_status
            FROM ReturnRequest rr
            LEFT JOIN Inspection insp ON rr.return_id = insp.return_id
            LEFT JOIN Refund rf ON rr.return_id = rf.return_id
            WHERE rr.order_id = %s ORDER BY rr.return_id DESC
            """,
            (order_id,),
        )
        returns = cur.fetchall()
        cur.close()
        return {"order": order, "items": items, "returns": returns}
    finally:
        conn.close()


def request_return(order_id, customer_id, reason, items, actor):
    """items: [{'order_item_id': int, 'quantity': int}]. Returns return_id."""
    if not reason or not reason.strip():
        raise AppError("Return reason is required")
    if not items:
        raise AppError("Select at least one order item to return")
    conn = get_db_connection()
    try:
        conn.autocommit = False
        cur = conn.cursor()
        _set_actor(cur, actor)
        cur.execute(
            "INSERT INTO ReturnRequest (order_id, customer_id, reason, return_status, requested_at)"
            " VALUES (%s, %s, %s, 'Requested', NOW())",
            (order_id, customer_id, reason.strip()[:120]),
        )
        return_id = cur.lastrowid
        for it in items:
            cur.execute(
                "INSERT INTO ReturnItem (return_id, order_item_id, quantity) VALUES (%s, %s, %s)",
                (return_id, it["order_item_id"], int(it["quantity"])),
            )
        conn.commit()
        cur.close()
        return return_id
    except AppError:
        conn.rollback()
        raise
    except mysql.connector.Error as err:
        conn.rollback()
        raise AppError(_msg(err))
    finally:
        conn.autocommit = True
        conn.close()


# ---------------------------------------------------------------------------
# Operations (support / warehouse)
# ---------------------------------------------------------------------------
def pending_returns():
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT rr.return_id, rr.order_id, c.name AS customer_name, c.email AS customer_email,
                   rr.reason, rr.return_status, rr.requested_at,
                   COUNT(ri.return_item_id) AS total_returned_items
            FROM ReturnRequest rr
            JOIN Customer c ON rr.customer_id = c.customer_id
            LEFT JOIN ReturnItem ri ON rr.return_id = ri.return_id
            WHERE rr.return_status IN ('Requested', 'Approved', 'Received', 'Inspected')
            GROUP BY rr.return_id, rr.order_id, c.name, c.email, rr.reason,
                     rr.return_status, rr.requested_at
            ORDER BY rr.requested_at ASC
            """
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def set_return_status(return_id, new_status, actor):
    """Used for approve/reject/receive. The state-machine trigger rejects illegal jumps."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        _set_actor(cur, actor)
        try:
            cur.execute("UPDATE ReturnRequest SET return_status = %s WHERE return_id = %s",
                        (new_status, return_id))
        except mysql.connector.Error as err:
            raise AppError(_msg(err))
        if cur.rowcount == 0:
            raise AppError("Return request %s not found" % return_id)
        cur.close()
    finally:
        conn.close()
    return new_status


def inspect_return(return_id, condition, notes, actor):
    if condition not in ("GOOD", "DAMAGED", "DEFECTIVE"):
        raise AppError("Condition must be GOOD, DAMAGED or DEFECTIVE")
    conn = get_db_connection()
    try:
        conn.autocommit = False
        cur = conn.cursor()
        _set_actor(cur, actor)
        try:
            cur.execute(
                "INSERT INTO Inspection (return_id, inspector, condition_status, notes, inspected_at)"
                " VALUES (%s, %s, %s, %s, NOW())",
                (return_id, actor, condition, (notes or "")[:255]),
            )
            cur.execute(
                "UPDATE ReturnRequest SET return_status = 'Inspected', inspected_at = NOW()"
                " WHERE return_id = %s",
                (return_id,),
            )
        except mysql.connector.Error as err:
            conn.rollback()
            raise AppError(_msg(err))
        conn.commit()
        cur.close()
    finally:
        conn.autocommit = True
        conn.close()
    return "Inspected"


def process_refund(order_id, return_id, actor):
    """Atomic refund via sp_process_refund. Returns refund_id."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        _set_actor(cur, actor)
        try:
            cur.callproc("sp_process_refund", (order_id, return_id, actor, 0))
            for res in cur.stored_results():
                res.fetchall()
        except mysql.connector.Error as err:
            raise AppError(_msg(err))
        finally:
            cur.close()
        cur2 = conn.cursor(dictionary=True)
        cur2.execute("SELECT refund_id FROM Refund WHERE return_id = %s ORDER BY refund_id DESC LIMIT 1",
                     (return_id,))
        row = cur2.fetchone()
        cur2.close()
        if not row:
            raise AppError("Refund procedure completed but no refund record was found")
        return row["refund_id"]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reports / analytics (queries a-f) and audit
# ---------------------------------------------------------------------------
def _report(sql, params=None):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def report_order_history():
    return _report(
        """
        SELECT o.order_id, o.customer_id, c.name AS customer_name, o.order_date, o.total_amount,
               o.order_status, p.payment_status, p.provider_reference, rr.return_id,
               rr.return_status, rr.reason AS return_reason, rf.amount AS refunded_amount
        FROM Orders o JOIN Customer c ON o.customer_id = c.customer_id
        LEFT JOIN Payment p ON o.order_id = p.order_id
        LEFT JOIN ReturnRequest rr ON o.order_id = rr.order_id
        LEFT JOIN Refund rf ON rr.return_id = rf.return_id
        ORDER BY o.order_date DESC LIMIT 100
        """
    )


def report_refund_status():
    return _report(
        """
        SELECT o.order_id, c.name AS customer_name, o.total_amount AS order_total,
               p.provider_reference, p.payment_status, rr.return_id, rr.return_status,
               COALESCE(rf.amount, 0.00) AS amount_refunded, rf.refund_status, rf.processed_at
        FROM Orders o JOIN Customer c ON o.customer_id = c.customer_id
        LEFT JOIN Payment p ON o.order_id = p.order_id
        LEFT JOIN ReturnRequest rr ON o.order_id = rr.order_id
        LEFT JOIN Refund rf ON rr.return_id = rf.return_id
        ORDER BY o.order_id DESC LIMIT 100
        """
    )


def report_return_rates():
    return _report(
        """
        SELECT p.name AS product_name,
               COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
               COALESCE(SUM(ri.quantity), 0) AS total_units_returned,
               ROUND(IF(COALESCE(SUM(oi.quantity), 0) = 0, 0.0,
                   (COALESCE(SUM(ri.quantity), 0) / SUM(oi.quantity)) * 100.0), 2)
                   AS return_rate_percentage
        FROM Product p
        LEFT JOIN OrderItem oi ON p.product_id = oi.product_id
        LEFT JOIN ReturnItem ri ON oi.order_item_id = ri.order_item_id
        GROUP BY p.product_id, p.name ORDER BY return_rate_percentage DESC
        """
    )


def report_monthly_refunds():
    return _report(
        """
        SELECT DATE_FORMAT(rf.processed_at, '%Y-%m') AS month_year,
               COUNT(rf.refund_id) AS total_refund_count,
               SUM(rf.amount) AS total_refund_amount
        FROM Refund rf WHERE rf.refund_status = 'Processed'
        GROUP BY DATE_FORMAT(rf.processed_at, '%Y-%m') ORDER BY month_year DESC
        """
    )


def report_top_reasons():
    return _report(
        """
        SELECT rr.reason AS return_reason, COUNT(rr.return_id) AS total_requests,
               COALESCE(SUM(rf.amount), 0.00) AS total_refunded_value
        FROM ReturnRequest rr LEFT JOIN Refund rf ON rr.return_id = rf.return_id
        GROUP BY rr.reason ORDER BY total_requests DESC
        """
    )


def audit_log(limit=100):
    return _report(
        """
        SELECT log_id, entity_type, entity_id, old_status, new_status, actor, note, changed_at
        FROM AuditLog ORDER BY changed_at DESC LIMIT %s
        """,
        (limit,),
    )


def system_inventory():
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema = 'ecommerce_db'")
        tables = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) AS cnt FROM information_schema.triggers WHERE trigger_schema = 'ecommerce_db'")
        triggers = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) AS cnt FROM information_schema.routines "
                    "WHERE routine_schema = 'ecommerce_db' AND routine_type = 'PROCEDURE'")
        procedures = cur.fetchone()["cnt"]
        cur.close()
        return {"tables_count": tables, "triggers_count": triggers,
                "procedures_count": procedures}
    finally:
        conn.close()
