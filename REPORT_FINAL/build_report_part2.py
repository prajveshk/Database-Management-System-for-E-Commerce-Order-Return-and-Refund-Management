"""Part 2: Chapters 2-4, references, appendices, figures."""
import docx
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from copy import deepcopy

OUT = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\REPORT_FINAL\25WU0102114_Prajvesh_DBMS_PBL_Report.docx"
ER_IMG = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\ecommerce_refund_dbms\docs\er_diagram.png"
SS_DIR = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\ecommerce_refund_dbms\docs\screenshots"
DIAG_DIR = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\REPORT_FINAL\diagrams"
import os
d = docx.Document(OUT)

def add_row(ti, vals):
    t = d.tables[ti]
    row = t.add_row()
    for i, v in enumerate(vals):
        if i < len(row.cells):
            row.cells[i].text = v
    return row

def replace_para_containing(substr, new_text):
    for p in d.paragraphs:
        if substr in p.text:
            p.text = new_text
            return True
    return False

def insert_image_at_match(match_text, image_path, width=6.0, replace=True):
    for p in d.paragraphs:
        if match_text in p.text:
            if replace:
                p.text = ""
            r = p.add_run()
            r.add_picture(image_path, width=Inches(width))
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            return True
    return False

# ============ CHAPTER 2 ============
# Table 14 relational schema (index 14)
schemas = [
    ("1", "Role(role_id, role_name)", "RBAC master; role_name UNIQUE."),
    ("2", "Customer(customer_id, name, email, phone, created_at)", "Buyer profile; email UNIQUE."),
    ("3", "AppUser(user_id, username, password_hash, role_id\u2192Role, customer_id\u2192Customer)", "Credentials; bcrypt hash; nullable customer for staff."),
    ("4", "Product(product_id, name, current_price, return_window_days)", "Catalogue; price \u22650; window in days."),
    ("5", "Inventory(inventory_id, product_id\u2192Product, serial_or_sku, status, updated_at)", "Stock units; SKU UNIQUE; 5-state ENUM."),
    ("6", "Orders(order_id, customer_id\u2192Customer, order_date, total_amount, order_status)", "Order header; total \u22650."),
    ("7", "OrderItem(order_item_id, order_id\u2192Orders, product_id\u2192Product, quantity, unit_price_at_purchase)", "Line items; qty>0; frozen history price."),
    ("8", "Payment(payment_id, order_id\u2192Orders, provider_reference, amount, payment_status)", "Gateway record; reference UNIQUE."),
    ("9", "ReturnRequest(return_id, order_id\u2192Orders, customer_id\u2192Customer, reason, return_status, requested_at, inspected_at)", "Return header; 6-state ENUM."),
    ("10", "ReturnItem(return_item_id, return_id\u2192ReturnRequest, order_item_id\u2192OrderItem, quantity)", "Partial returns; qty>0."),
    ("11", "Inspection(inspection_id, return_id\u2192ReturnRequest UNIQUE, inspector, condition_status, notes, inspected_at)", "1:1 inspection verdict."),
    ("12", "Refund(refund_id, return_id\u2192ReturnRequest, payment_id\u2192Payment, amount, refund_status, processed_at)", "Credit record; amount \u22650."),
    ("13", "AuditLog(log_id, entity_type, entity_id, old_status, new_status, actor, note, changed_at)", "Append-only trail; no FK (generic)."),
]
t14 = d.tables[14]
for i in range(1, len(t14.rows)):
    for c in t14.rows[i].cells:
        c.text = ""
for i, (a, b, c_) in enumerate(schemas):
    if i+1 < len(t14.rows):
        t14.rows[i+1].cells[0].text = a
        t14.rows[i+1].cells[1].text = b
        t14.rows[i+1].cells[2].text = c_
    else:
        add_row(14, [a, b, c_])

# Table 15 keys (index 15) — rebuild
keys = [
    ("Role", "Primary Key", "role_id", "One row per role."),
    ("Role", "Unique", "role_name", "No duplicate role names."),
    ("Customer", "Primary Key", "customer_id", "One row per customer."),
    ("Customer", "Unique + Not Null", "email", "Login identity; required."),
    ("AppUser", "Primary Key", "user_id", "One row per login."),
    ("AppUser", "Unique", "username", "Login uniqueness."),
    ("AppUser", "Foreign Key (RESTRICT)", "role_id \u2192 Role", "Cannot delete referenced role."),
    ("AppUser", "Foreign Key (RESTRICT)", "customer_id \u2192 Customer", "Staff rows allow NULL."),
    ("Product", "Primary Key", "product_id", "One row per product."),
    ("Product", "Check", "current_price >= 0", "No negative prices."),
    ("Product", "Check + Default", "return_window_days >= 0 (default 30)", "Non-negative window."),
    ("Inventory", "Primary + Unique + FK", "inventory_id; serial_or_sku UNIQUE; product_id \u2192 Product RESTRICT", "Traceable units; ENUM status."),
    ("Orders", "Primary + FK + Check", "order_id; customer_id \u2192 Customer RESTRICT; total_amount >= 0", "Order integrity; ENUM status."),
    ("OrderItem", "Primary + 2 FK + Check", "order_item_id; order_id, product_id RESTRICT; quantity > 0; unit_price >= 0", "Valid line quantities."),
    ("Payment", "Primary + FK + Unique + Check", "payment_id; order_id RESTRICT; provider_reference UNIQUE; amount >= 0", "No duplicate gateway refs."),
    ("ReturnRequest", "Primary + 2 FK", "return_id; order_id, customer_id RESTRICT; ENUM return_status", "Controlled 6-state domain."),
    ("ReturnItem", "Primary + 2 FK + Check", "return_item_id; return_id, order_item_id RESTRICT; quantity > 0", "Partial-return integrity."),
    ("Inspection", "Primary + Unique FK", "inspection_id; return_id UNIQUE \u2192 ReturnRequest (1:1)", "One verdict per return; ENUM condition."),
    ("Refund", "Primary + 2 FK + Check", "refund_id; return_id, payment_id RESTRICT; amount >= 0", "Exact-once credit; ENUM status."),
    ("AuditLog", "Primary Key", "log_id", "Append-only; written by triggers/procedure."),
]
t15 = d.tables[15]
for i in range(1, len(t15.rows)):
    for c in t15.rows[i].cells:
        c.text = ""
for i, (a, b, c_, e) in enumerate(keys):
    if i+1 < len(t15.rows):
        t15.rows[i+1].cells[0].text = a
        t15.rows[i+1].cells[1].text = b
        t15.rows[i+1].cells[2].text = c_
        t15.rows[i+1].cells[3].text = e
    else:
        add_row(15, [a, b, c_, e])

# 2.3 FDs
replace_para_containing("[Example format: Key -> non-key",
    "Key FDs (all relations have atomic single-attribute PKs, so no partial dependencies): "
    "role_id \u2192 role_name; customer_id \u2192 name, email, phone, created_at; user_id \u2192 username, password_hash, role_id, customer_id; "
    "product_id \u2192 name, current_price, return_window_days; inventory_id \u2192 product_id, serial_or_sku, status, updated_at; "
    "order_id \u2192 customer_id, order_date, total_amount, order_status; order_item_id \u2192 order_id, product_id, quantity, unit_price_at_purchase; "
    "payment_id \u2192 order_id, provider_reference, amount, payment_status; return_id \u2192 order_id, customer_id, reason, return_status, requested_at, inspected_at; "
    "return_item_id \u2192 return_id, order_item_id, quantity; inspection_id \u2192 return_id, inspector, condition_status, notes, inspected_at; "
    "refund_id \u2192 return_id, payment_id, amount, refund_status, processed_at; log_id \u2192 entity_type, entity_id, old_status, new_status, actor, note, changed_at. "
    "Transitive risks removed: product name/price kept only in Product (OrderItem keeps frozen unit_price_at_purchase as history, not a transitive fact); customer details kept only in Customer.")

# Table 16 normalization (index 16)
norms = [
    ("Role, Customer, AppUser", "Yes", "Yes", "Yes", "Yes", "Atomic cols; full-key dependent; no transitives."),
    ("Product, Inventory", "Yes", "Yes", "Yes", "Yes", "SKU/status depend on full key only."),
    ("Orders, OrderItem", "Yes", "Yes", "Yes", "Yes", "History price is a purchase fact, not product transitive."),
    ("Payment", "Yes", "Yes", "Yes", "Yes", "Gateway ref unique; amount depends on key."),
    ("ReturnRequest, ReturnItem", "Yes", "Yes", "Yes", "Yes", "Reason/status per return; qty per return-item."),
    ("Inspection, Refund, AuditLog", "Yes", "Yes", "Yes", "Yes", "1:1/1:N preserved via UNIQUE/FK; no redundancy."),
]
t16 = d.tables[16]
for i in range(len(t16.rows)-1):
    pass
# clear data rows
for i in range(1, len(t16.rows)):
    for c in t16.rows[i].cells:
        c.text = ""
for i, vals in enumerate(norms):
    if i+1 < len(t16.rows):
        for j, v in enumerate(vals):
            t16.rows[i+1].cells[j].text = v
    else:
        add_row(16, list(vals))

# Table 17 data dictionary (index 17) — condensed full
dd = [
    ("Role", "role_id", "INT AUTO_INCREMENT", "PK", "Role surrogate key."),
    ("Role", "role_name", "VARCHAR(50)", "UNIQUE NOT NULL", "Customer/Support/Warehouse/Admin."),
    ("Customer", "customer_id", "INT AUTO_INCREMENT", "PK", "Customer key."),
    ("Customer", "name / email / phone", "VARCHAR(100/100/20)", "NOT NULL / UNIQUE / NULL", "Profile; email unique."),
    ("AppUser", "user_id / username", "INT / VARCHAR(50)", "PK / UNIQUE NOT NULL", "Login identity."),
    ("AppUser", "password_hash", "VARCHAR(255)", "NOT NULL", "bcrypt hash; never plaintext."),
    ("AppUser", "role_id / customer_id", "INT / INT NULL", "FK RESTRICT", "Role link; customer NULL for staff."),
    ("Product", "product_id / name", "INT / VARCHAR(150)", "PK / NOT NULL", "Catalogue item."),
    ("Product", "current_price", "DECIMAL(10,2)", "CHECK >= 0", "Live price."),
    ("Product", "return_window_days", "INT DEFAULT 30", "CHECK >= 0", "Eligibility window."),
    ("Inventory", "inventory_id / product_id", "INT / INT", "PK / FK RESTRICT", "Stock unit of product."),
    ("Inventory", "serial_or_sku", "VARCHAR(100)", "UNIQUE", "Traceable unit code."),
    ("Inventory", "status", "ENUM(5 values)", "NOT NULL DEFAULT AVAILABLE", "AVAILABLE..DAMAGED."),
    ("Orders", "order_id / customer_id", "INT / INT", "PK / FK RESTRICT", "Order header."),
    ("Orders", "total_amount", "DECIMAL(10,2)", "CHECK >= 0", "Sum of line prices."),
    ("Orders", "order_status", "ENUM(5)", "DEFAULT Pending", "Pending..Cancelled."),
    ("OrderItem", "order_item_id", "INT", "PK", "Line key."),
    ("OrderItem", "order_id / product_id", "INT / INT", "FK RESTRICT", "Order\u2013product link."),
    ("OrderItem", "quantity / unit_price_at_purchase", "INT / DECIMAL(10,2)", "CHECK >0 / >=0", "Qty + frozen history price."),
    ("Payment", "payment_id / order_id", "INT / INT", "PK / FK RESTRICT", "Payment for order."),
    ("Payment", "provider_reference", "VARCHAR(100)", "UNIQUE NOT NULL", "Mock gateway ref."),
    ("Payment", "amount / payment_status", "DECIMAL / ENUM(4)", "CHECK>=0 / DEFAULT Completed", "Paid amount + state."),
    ("ReturnRequest", "return_id", "INT", "PK", "Return header key."),
    ("ReturnRequest", "order_id / customer_id", "INT / INT", "FK RESTRICT", "Which order/customer."),
    ("ReturnRequest", "reason / return_status", "VARCHAR(120) / ENUM(6)", "NOT NULL / DEFAULT Requested", "6-state lifecycle."),
    ("ReturnItem", "return_item_id", "INT", "PK", "Return line key."),
    ("ReturnItem", "return_id / order_item_id", "INT / INT", "FK RESTRICT", "Partial return link."),
    ("ReturnItem", "quantity", "INT", "CHECK > 0", "Returned units."),
    ("Inspection", "inspection_id / return_id", "INT / INT", "PK / UNIQUE FK", "1:1 verdict per return."),
    ("Inspection", "inspector / condition_status", "VARCHAR(100) / ENUM(3)", "NOT NULL", "Who + GOOD/DAMAGED/DEFECTIVE."),
    ("Refund", "refund_id", "INT", "PK", "Credit key."),
    ("Refund", "return_id / payment_id", "INT / INT", "FK RESTRICT", "Return credited to payment."),
    ("Refund", "amount / refund_status", "DECIMAL / ENUM(3)", "CHECK>=0 / DEFAULT Processed", "Credited sum."),
    ("AuditLog", "log_id", "INT", "PK", "Trail key."),
    ("AuditLog", "entity_type / entity_id", "VARCHAR(50) / INT", "NOT NULL", "E.g. ReturnRequest/14."),
    ("AuditLog", "old_status / new_status / actor", "VARCHAR / VARCHAR / VARCHAR(100)", "NULL ok / NOT NULL", "Transition + who."),
]
t17 = d.tables[17]
for i in range(1, len(t17.rows)):
    for c in t17.rows[i].cells:
        c.text = ""
for i, vals in enumerate(dd):
    if i+1 < len(t17.rows):
        for j, v in enumerate(vals):
            t17.rows[i+1].cells[j].text = v
    else:
        add_row(17, list(vals))

# Table 18 env (index 18)
t18 = d.tables[18]
t18.rows[0].cells[1].text = "MySQL 8.0 (InnoDB, ACID)"
t18.rows[1].cells[1].text = "8.0.46"
t18.rows[2].cells[1].text = "13 (3NF)"
t18.rows[3].cells[1].text = "5 demo orders + 5 products + 50 inventory units + users/roles; bulk scale to 100K via seed_bulk_data."

replace_para_containing("[Insert representative DDL snippets",
    "Representative DDL (complete script in Appendix A, db/schema.sql). Engine InnoDB is specified on every table for ACID transactions and FK enforcement:")
# insert DDL code + sample data note right after that para
for p in d.paragraphs:
    if p.text.startswith("Representative DDL"):
        # add code paragraphs after p by inserting new elements
        codes = [
            "CREATE TABLE Product (product_id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(150) NOT NULL,",
            "  current_price DECIMAL(10,2) NOT NULL CHECK (current_price >= 0),",
            "  return_window_days INT NOT NULL DEFAULT 30 CHECK (return_window_days >= 0)) ENGINE=InnoDB;",
            "CREATE TABLE OrderItem (order_item_id INT AUTO_INCREMENT PRIMARY KEY, order_id INT NOT NULL, product_id INT NOT NULL,",
            "  quantity INT NOT NULL CHECK (quantity > 0), unit_price_at_purchase DECIMAL(10,2) NOT NULL CHECK (unit_price_at_purchase >= 0),",
            "  FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE RESTRICT,",
            "  FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE RESTRICT) ENGINE=InnoDB;",
            "CREATE TABLE Inspection (inspection_id INT AUTO_INCREMENT PRIMARY KEY, return_id INT NOT NULL UNIQUE,",
            "  inspector VARCHAR(100) NOT NULL, condition_status ENUM('GOOD','DAMAGED','DEFECTIVE') NOT NULL,",
            "  FOREIGN KEY (return_id) REFERENCES ReturnRequest(return_id) ON DELETE RESTRICT) ENGINE=InnoDB;",
            "Sample data (db/seed.py): Alice Smith (customer_user), Bob Jones, Charlie Brown; 5 products (Headphones Rs.199.99/30d, Keyboard Rs.129.50/14d, Monitor Rs.349/30d, Watch Rs.149.99/7d, Dock Rs.79.99/30d); Order 1 (eligible), Order 3 (45 days old, 7-day window \u2014 used to prove late-return blocking), Order 4 (Inspected, ready to refund), Order 5 (Approved, awaiting warehouse).",
        ]
        from copy import deepcopy as dc
        last_el = p._element
        for code in codes:
            new_el = dc(p._element)
            # set text
            # clear runs text
            for t_el in new_el.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                t_el.text = ""
            # set first t
            t_els = new_el.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
            if t_els:
                t_els[0].text = code
            last_el.addnext(new_el)
            last_el = new_el
        break

print("Chapter 2 done")
d.save(OUT)
