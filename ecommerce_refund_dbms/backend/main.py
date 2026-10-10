import os
import mysql.connector
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from backend.database import get_db_connection
from backend.auth import (
    verify_password, create_access_token, get_current_user, require_roles
)
from backend.models import (
    LoginRequest, TokenResponse, OrderCreate, ReturnCreate, InspectionCreate
)
from backend.payment_gateway import MockPaymentGateway

app = FastAPI(
    title="E-Commerce Order, Return and Refund Management DBMS",
    description="B.Tech AI & ML Project REST API backend with MySQL 8 database enforcement",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# AUTHENTICATION ENDPOINTS
# -----------------------------------------------------------------------------
@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT u.user_id, u.username, u.password_hash, u.customer_id, r.role_name
        FROM AppUser u
        JOIN Role r ON u.role_id = r.role_id
        WHERE u.username = %s
    """, (req.username,))
    
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user or not verify_password(req.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
        
    token_data = {
        "sub": user["username"],
        "user_id": user["user_id"],
        "role": user["role_name"],
        "customer_id": user["customer_id"]
    }
    access_token = create_access_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        user_id=user["user_id"],
        username=user["username"],
        role=user["role_name"],
        customer_id=user["customer_id"]
    )

# -----------------------------------------------------------------------------
# CUSTOMER ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/products")
def list_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, name, current_price, return_window_days FROM Product")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return products

@app.post("/api/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    req: OrderCreate,
    current_user: dict = Depends(require_roles(["Customer", "Admin"]))
):
    customer_id = current_user.get("customer_id")
    if not customer_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=400, detail="User account is not associated with a customer record.")
    if not customer_id:
        customer_id = 1
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        total_amount = 0.0
        order_items_prepared = []
        for item in req.items:
            cursor.execute("SELECT current_price FROM Product WHERE product_id = %s", (item.product_id,))
            p = cursor.fetchone()
            if not p:
                raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found.")
            price = float(p["current_price"])
            total_amount += price * item.quantity
            order_items_prepared.append((item.product_id, item.quantity, price))
            
        total_amount = round(total_amount, 2)
        
        cursor.execute(
            "INSERT INTO Orders (customer_id, order_date, total_amount, order_status) VALUES (%s, NOW(), %s, 'Delivered')",
            (customer_id, total_amount)
        )
        order_id = cursor.lastrowid
        
        for p_id, qty, unit_price in order_items_prepared:
            cursor.execute(
                "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase) VALUES (%s, %s, %s, %s)",
                (order_id, p_id, qty, unit_price)
            )
            
        pg_res = MockPaymentGateway.process_payment(total_amount, order_id)
        cursor.execute(
            "INSERT INTO Payment (order_id, provider_reference, amount, payment_status) VALUES (%s, %s, %s, 'Completed')",
            (order_id, pg_res["provider_reference"], total_amount)
        )
        
        return {
            "message": "Order created successfully",
            "order_id": order_id,
            "total_amount": total_amount,
            "provider_reference": pg_res["provider_reference"]
        }
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=err.msg)
    finally:
        cursor.close()
        conn.close()

@app.post("/api/returns", status_code=status.HTTP_201_CREATED)
def create_return_request(
    req: ReturnCreate,
    current_user: dict = Depends(require_roles(["Customer", "Admin"]))
):
    customer_id = current_user.get("customer_id")
    if not customer_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=400, detail="User account is not associated with a customer record.")
    if not customer_id:
        customer_id = 1
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SET @current_app_user = %s", (current_user["sub"],))
        
        cursor.execute(
            "INSERT INTO ReturnRequest (order_id, customer_id, reason, return_status, requested_at) VALUES (%s, %s, %s, 'Requested', NOW())",
            (req.order_id, customer_id, req.reason)
        )
        return_id = cursor.lastrowid
        
        for item in req.items:
            cursor.execute(
                "INSERT INTO ReturnItem (return_id, order_item_id, quantity) VALUES (%s, %s, %s)",
                (return_id, item.order_item_id, item.quantity)
            )
            
        return {
            "message": "Return request submitted successfully",
            "return_id": return_id,
            "order_id": req.order_id,
            "status": "Requested"
        }
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=err.msg)
    finally:
        cursor.close()
        conn.close()

@app.get("/api/orders/{order_id}/status")
def get_order_status(
    order_id: int,
    current_user: dict = Depends(require_roles(["Customer", "Support", "Warehouse", "Admin"]))
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT o.order_id, o.customer_id, c.name AS customer_name, o.order_date, o.total_amount, o.order_status,
               p.provider_reference, p.payment_status
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        LEFT JOIN Payment p ON o.order_id = p.order_id
        WHERE o.order_id = %s
    """, (order_id,))
    order = cursor.fetchone()
    if not order:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
        
    cursor.execute("""
        SELECT oi.order_item_id, p.name AS product_name, oi.quantity, oi.unit_price_at_purchase
        FROM OrderItem oi
        JOIN Product p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()
    
    cursor.execute("""
        SELECT rr.return_id, rr.reason, rr.return_status, rr.requested_at, rr.inspected_at,
               insp.condition_status, insp.inspector, insp.notes AS inspection_notes,
               rf.refund_id, rf.amount AS refunded_amount, rf.refund_status, rf.processed_at
        FROM ReturnRequest rr
        LEFT JOIN Inspection insp ON rr.return_id = insp.return_id
        LEFT JOIN Refund rf ON rr.return_id = rf.return_id
        WHERE rr.order_id = %s
    """, (order_id,))
    returns = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {
        "order": order,
        "items": items,
        "returns": returns
    }

# -----------------------------------------------------------------------------
# OPERATIONS DASHBOARD ENDPOINTS
# -----------------------------------------------------------------------------
@app.put("/api/returns/{return_id}/approve")
def approve_return(
    return_id: int,
    action: str = "approve",
    current_user: dict = Depends(require_roles(["Support", "Admin"]))
):
    new_status = "Approved" if action.lower() == "approve" else "Rejected"
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SET @current_app_user = %s", (current_user["sub"],))
        cursor.execute(
            "UPDATE ReturnRequest SET return_status = %s WHERE return_id = %s",
            (new_status, return_id)
        )
        return {"message": f"Return request {return_id} set to {new_status}", "return_id": return_id, "status": new_status}
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=err.msg)
    finally:
        cursor.close()
        conn.close()

@app.put("/api/returns/{return_id}/receive")
def receive_return(
    return_id: int,
    current_user: dict = Depends(require_roles(["Warehouse", "Admin"]))
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SET @current_app_user = %s", (current_user["sub"],))
        cursor.execute(
            "UPDATE ReturnRequest SET return_status = 'Received' WHERE return_id = %s",
            (return_id,)
        )
        return {"message": f"Return request {return_id} marked as Received", "return_id": return_id, "status": "Received"}
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=err.msg)
    finally:
        cursor.close()
        conn.close()

@app.put("/api/returns/{return_id}/inspect")
def inspect_return(
    return_id: int,
    req: InspectionCreate,
    current_user: dict = Depends(require_roles(["Warehouse", "Admin"]))
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SET @current_app_user = %s", (current_user["sub"],))
        
        cursor.execute(
            "INSERT INTO Inspection (return_id, inspector, condition_status, notes, inspected_at) VALUES (%s, %s, %s, %s, NOW())",
            (return_id, current_user["sub"], req.condition_status, req.notes)
        )
        
        cursor.execute(
            "UPDATE ReturnRequest SET return_status = 'Inspected', inspected_at = NOW() WHERE return_id = %s",
            (return_id,)
        )
        return {
            "message": f"Return request {return_id} inspected successfully",
            "return_id": return_id,
            "condition": req.condition_status,
            "status": "Inspected"
        }
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=err.msg)
    finally:
        cursor.close()
        conn.close()

@app.post("/api/returns/{return_id}/refund")
def process_refund(
    return_id: int,
    current_user: dict = Depends(require_roles(["Support", "Admin"]))
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT order_id FROM ReturnRequest WHERE return_id = %s", (return_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Return request not found")
        order_id = row["order_id"]
        
        args = (order_id, return_id, current_user["sub"], 0)
        cursor.callproc("sp_process_refund", args)
        
        cursor.execute("SELECT refund_id FROM Refund WHERE return_id = %s ORDER BY refund_id DESC LIMIT 1", (return_id,))
        ref_row = cursor.fetchone()
        refund_id = ref_row["refund_id"] if ref_row else None
        
        return {
            "message": "Refund processed successfully via sp_process_refund stored procedure",
            "refund_id": refund_id,
            "return_id": return_id,
            "order_id": order_id,
            "status": "Refunded"
        }
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=err.msg)
    finally:
        cursor.close()
        conn.close()

# -----------------------------------------------------------------------------
# ADMIN ONLY ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/audit")
def get_audit_log(
    current_user: dict = Depends(require_roles(["Admin"]))
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT log_id, entity_type, entity_id, old_status, new_status, actor, note, changed_at
        FROM AuditLog
        ORDER BY changed_at DESC
        LIMIT 100
    """)
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return logs

# -----------------------------------------------------------------------------
# REPORT & ANALYTICS ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/reports/order-history")
def report_order_history(current_user: dict = Depends(require_roles(["Support", "Warehouse", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.customer_id, c.name AS customer_name, o.order_date, o.total_amount, o.order_status,
               p.payment_status, p.provider_reference, rr.return_id, rr.return_status, rr.reason AS return_reason,
               rf.amount AS refunded_amount
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        LEFT JOIN Payment p ON o.order_id = p.order_id
        LEFT JOIN ReturnRequest rr ON o.order_id = rr.order_id
        LEFT JOIN Refund rf ON rr.return_id = rf.return_id
        ORDER BY o.order_date DESC LIMIT 100
    """)
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res

@app.get("/api/reports/pending-returns")
def report_pending_returns(current_user: dict = Depends(require_roles(["Support", "Warehouse", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT rr.return_id, rr.order_id, c.name AS customer_name, c.email AS customer_email,
               rr.reason, rr.return_status, rr.requested_at
        FROM ReturnRequest rr
        JOIN Customer c ON rr.customer_id = c.customer_id
        WHERE rr.return_status IN ('Requested', 'Approved', 'Received', 'Inspected')
        ORDER BY rr.requested_at ASC
    """)
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res

@app.get("/api/reports/refund-status")
def report_refund_status(current_user: dict = Depends(require_roles(["Support", "Warehouse", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, c.name AS customer_name, o.total_amount AS order_total,
               p.provider_reference, p.payment_status, rr.return_id, rr.return_status,
               COALESCE(rf.amount, 0.00) AS amount_refunded, rf.refund_status, rf.processed_at
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        LEFT JOIN Payment p ON o.order_id = p.order_id
        LEFT JOIN ReturnRequest rr ON o.order_id = rr.order_id
        LEFT JOIN Refund rf ON rr.return_id = rf.return_id
        ORDER BY o.order_id DESC LIMIT 100
    """)
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res

@app.get("/api/reports/return-rates")
def report_return_rates(current_user: dict = Depends(require_roles(["Customer", "Support", "Warehouse", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.product_id, p.name AS product_name,
               COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
               COALESCE(SUM(ri.quantity), 0) AS total_units_returned,
               ROUND(
                   IF(COALESCE(SUM(oi.quantity), 0) = 0, 0.0,
                       (COALESCE(SUM(ri.quantity), 0) / SUM(oi.quantity)) * 100.0
                   ), 2
               ) AS return_rate_percentage
        FROM Product p
        LEFT JOIN OrderItem oi ON p.product_id = oi.product_id
        LEFT JOIN ReturnItem ri ON oi.order_item_id = ri.order_item_id
        GROUP BY p.product_id, p.name
        ORDER BY return_rate_percentage DESC
    """)
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res

@app.get("/api/reports/monthly-refunds")
def report_monthly_refunds(current_user: dict = Depends(require_roles(["Customer", "Support", "Warehouse", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DATE_FORMAT(rf.processed_at, '%Y-%m') AS month_year,
               COUNT(rf.refund_id) AS total_refund_count,
               SUM(rf.amount) AS total_refund_amount
        FROM Refund rf
        WHERE rf.refund_status = 'Processed'
        GROUP BY DATE_FORMAT(rf.processed_at, '%Y-%m')
        ORDER BY month_year DESC
    """)
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res

@app.get("/api/reports/top-reasons")
def report_top_reasons(current_user: dict = Depends(require_roles(["Customer", "Support", "Warehouse", "Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT rr.reason AS return_reason,
               COUNT(rr.return_id) AS total_requests,
               COALESCE(SUM(rf.amount), 0.00) AS total_refunded_value
        FROM ReturnRequest rr
        LEFT JOIN Refund rf ON rr.return_id = rf.return_id
        GROUP BY rr.reason
        ORDER BY total_requests DESC
    """)
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res

# -----------------------------------------------------------------------------
# SYSTEM INVENTORY ENDPOINT
# -----------------------------------------------------------------------------
@app.get("/api/system/inventory")
def get_system_inventory():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema = 'ecommerce_db'")
    table_count = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT COUNT(*) AS cnt FROM information_schema.triggers WHERE trigger_schema = 'ecommerce_db'")
    trigger_count = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT COUNT(*) AS cnt FROM information_schema.routines WHERE routine_schema = 'ecommerce_db' AND routine_type = 'PROCEDURE'")
    procedure_count = cursor.fetchone()["cnt"]
    
    cursor.close()
    conn.close()
    
    api_endpoint_count = len([route for route in app.routes if hasattr(route, "path") and route.path.startswith("/api/")])
    
    return {
        "tables_count": table_count,
        "triggers_count": trigger_count,
        "procedures_count": procedure_count,
        "api_endpoints_count": api_endpoint_count
    }

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("frontend/index.html")
