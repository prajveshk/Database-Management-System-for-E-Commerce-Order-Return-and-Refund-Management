import os
import subprocess
import requests
import json
import matplotlib.pyplot as plt

API_BASE = "http://127.0.0.1:8000"

def create_styled_card_image(title, subtitle, content_text, filename, accent_color='#3498db'):
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    fig.patch.set_facecolor('#f4f6f9')
    ax.set_facecolor('#ffffff')
    ax.axis('off')
    
    # Title box
    ax.text(0.03, 0.92, title, fontsize=16, fontweight='bold', color='#2c3e50', va='top')
    ax.text(0.03, 0.86, subtitle, fontsize=11, color='#7f8c8d', va='top')
    ax.plot([0.03, 0.97], [0.83, 0.83], color=accent_color, lw=3)
    
    # Content area
    ax.text(0.04, 0.78, content_text, fontsize=9.5, family='monospace', color='#1e272e', va='top', wrap=True)
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    plt.savefig(filename, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

def generate_fallback_screenshots():
    os.makedirs("docs/screenshots", exist_ok=True)
    
    # 1. Customer Portal
    p_res = requests.get(f"{API_BASE}/api/products").json()
    cust_text = "AVAILABLE PRODUCTS (3NF Catalog):\n" + json.dumps(p_res, indent=2)
    create_styled_card_image("Customer Portal View", "Products Catalog & Order Management", cust_text, "docs/screenshots/customer_portal.png", "#3498db")

    # 2. Ops Dashboard
    login_res = requests.post(f"{API_BASE}/api/auth/login", json={"username": "support_agent", "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {login_res['access_token']}"}
    pending = requests.get(f"{API_BASE}/api/reports/pending-returns", headers=headers).json()
    ops_text = "SUPPORT AGENT & WAREHOUSE INSPECTION QUEUE:\n" + json.dumps(pending, indent=2)
    create_styled_card_image("Operations Dashboard", "Support Approval & Warehouse Inspection Queue", ops_text, "docs/screenshots/ops_dashboard.png", "#f39c12")

    # 3. API Flow / Stepper
    order_status = requests.get(f"{API_BASE}/api/orders/4/status", headers=headers).json()
    flow_text = "LIVE DATABASE STATE FOR LIFECYCLE STEPPER (Order #4):\n" + json.dumps(order_status, indent=2)
    create_styled_card_image("Demo Lifecycle Stepper (7 States)", "Live MySQL Query Response for Order #4", flow_text, "docs/screenshots/api_flow.png", "#27ae60")

    # 4. Access Denied 403
    cust_login = requests.post(f"{API_BASE}/api/auth/login", json={"username": "customer_user", "password": "password123"}).json()
    cust_headers = {"Authorization": f"Bearer {cust_login['access_token']}"}
    audit_err = requests.get(f"{API_BASE}/api/audit", headers=cust_headers)
    denied_text = f"HTTP {audit_err.status_code} FORBIDDEN RESPONSE:\n\n" + json.dumps(audit_err.json(), indent=2)
    create_styled_card_image("Access Denied (HTTP 403 Forbidden)", "Role-Based Access Control Rejection for Non-Admin User", denied_text, "docs/screenshots/access_denied_403.png", "#e74c3c")

    # 5. Audit Log
    admin_login = requests.post(f"{API_BASE}/api/auth/login", json={"username": "admin_user", "password": "password123"}).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}
    audit_log = requests.get(f"{API_BASE}/api/audit", headers=admin_headers).json()
    audit_text = "IMMUTABLE AUDIT TRAIL LOG (Admin View):\n" + json.dumps(audit_log[:5], indent=2)
    create_styled_card_image("System Audit Log", "Database Trigger Audit Log Entries", audit_text, "docs/screenshots/audit_log.png", "#8e44ad")

    # 6. Analytics Dashboard
    rates = requests.get(f"{API_BASE}/api/reports/return-rates", headers=admin_headers).json()
    reasons = requests.get(f"{API_BASE}/api/reports/top-reasons", headers=admin_headers).json()
    analytics_text = "ANALYTICAL REPORT DATA (Return Rates & Reasons):\n\n" + "Return Rates:\n" + json.dumps(rates[:3], indent=2) + "\n\nTop Reasons:\n" + json.dumps(reasons, indent=2)
    create_styled_card_image("Analytics Dashboard", "Return Rates per Product and Top Reasons Analysis", analytics_text, "docs/screenshots/analytics_dashboard.png", "#16a085")

    # 7. Blocked Late Return
    blocked_res = requests.post(f"{API_BASE}/api/returns", json={"order_id": 3, "reason": "Late return", "items": [{"order_item_id": 3, "quantity": 1}]}, headers=cust_headers)
    blocked_text = f"DATABASE TRIGGER REJECTION (HTTP {blocked_res.status_code}):\n\n" + json.dumps(blocked_res.json(), indent=2)
    create_styled_card_image("Blocked Late Return Rejection", "MySQL BEFORE INSERT Trigger Enforcement Result", blocked_text, "docs/screenshots/blocked_late_return.png", "#d35400")

    print("Fallback screenshots generated successfully!")

if __name__ == "__main__":
    generate_fallback_screenshots()
