"""Part 3: Chapters 3-4, refs, appendices, screenshots."""
import docx, os
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from copy import deepcopy

OUT = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\REPORT_FINAL\25WU0102114_Prajvesh_DBMS_PBL_Report.docx"
SS = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\ecommerce_refund_dbms\docs\screenshots"
DIAG = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\REPORT_FINAL\diagrams"
d = docx.Document(OUT)

def add_row(ti, vals):
    t = d.tables[ti]
    row = t.add_row()
    for i, v in enumerate(vals):
        if i < len(row.cells):
            row.cells[i].text = v
    return row

def replace(substr, new):
    for p in d.paragraphs:
        if substr in p.text:
            p.text = new
            return True
    return False

# ---- 3.1 overview ----
replace("[Application overview - approximately 1 paragraph.]",
    "The application is a three-layer system: a responsive vanilla HTML5/CSS3/JS single-page dashboard (Customer Portal, Operations Dashboard, 7-state Demo Lifecycle Stepper), a FastAPI service layer with JWT authentication and four-role RBAC plus a deterministic mock payment gateway, and a MySQL 8 InnoDB data layer. Every screen operation maps to parameterized SQL on the 3NF schema in Chapter 2: ordering inserts Orders/OrderItem/Payment, returning inserts ReturnRequest/ReturnItem (trigger-validated), approvals/receives/inspections are constrained UPDATEs/INSERTs, and refunds are executed only through sp_process_refund. Analytics screens run the six catalogued JOIN/GROUP BY queries (Sec. 3.6), and the Admin audit screen reads AuditLog. No screen uses isolated or static data.")

# ---- Table 19 env (index 19) ----
t19 = d.tables[19]
t19.rows[0].cells[1].text = "Python 3.13"
t19.rows[1].cells[1].text = "MySQL 8.0.46 (InnoDB)"
t19.rows[2].cells[1].text = "FastAPI 0.x + Uvicorn; vanilla HTML5/CSS3/JS SPA; bcrypt + PyJWT"
t19.rows[3].cells[1].text = "mysql-connector-python (parameterized %s queries); SQLAlchemy not used"
t19.rows[4].cells[1].text = "Windows 11 + Docker Compose option (db port 3307); localhost:8000"
t19.rows[5].cells[1].text = "ecommerce_refund_dbms/ (backend/, frontend/index.html, db/*.sql, tests/, benchmarks/)"

# ---- Table 20 module mapping (index 20) ----
mods = [
    ("Auth + RBAC (/api/auth/login)", "JWT issue; role routing", "Role, AppUser", "SELECT AppUser\u22c8Role; bcrypt verify; create_access_token"),
    ("Customer portal (products, orders, returns)", "Browse, buy, track, return", "Product, Orders, OrderItem, Payment, ReturnRequest, ReturnItem", "SELECT products; INSERT Orders/OrderItem/Payment; INSERT ReturnRequest/ReturnItem"),
    ("Support queue (/api/returns approve, refund)", "Approve/reject; trigger refund", "ReturnRequest, Refund, Payment", "UPDATE status; CALL sp_process_refund"),
    ("Warehouse queue (receive, inspect)", "Receive + condition verdict", "ReturnRequest, Inspection, Inventory", "UPDATE Received; INSERT Inspection; UPDATE Inspected"),
    ("Analytics (/api/reports/*)", "6 operational/analytical views", "All sales/return tables", "JOIN + GROUP BY + DATE_FORMAT aggregations"),
    ("Admin audit (/api/audit)", "Immutable trail viewer (Admin only)", "AuditLog", "SELECT last 100 ORDER BY changed_at DESC; 403 otherwise"),
    ("System inventory (/api/system/inventory)", "Live counts for review", "information_schema", "COUNT tables/triggers/procedures + route count"),
]
t20 = d.tables[20]
for i in range(1, len(t20.rows)):
    for c in t20.rows[i].cells:
        c.text = ""
for i, vals in enumerate(mods):
    if i+1 < len(t20.rows):
        for j, v in enumerate(vals):
            t20.rows[i+1].cells[j].text = v
    else:
        add_row(20, list(vals))

# ---- Table 21 CRUD (index 21) ----
t21 = d.tables[21]
t21.rows[1].cells[1].text = "Customer portal \u2192 Place Order; Submit Return"
t21.rows[1].cells[2].text = "Orders, OrderItem, Payment; ReturnRequest, ReturnItem"
t21.rows[1].cells[3].text = "Fig. 2 customer portal; POST /api/orders, /api/returns (201)"
t21.rows[1].cells[0].text = "Create"
t21.rows[2].cells[0].text = "Read / Search"
t21.rows[2].cells[1].text = "Order status tracker; pending-returns queue; analytics"
t21.rows[2].cells[2].text = "Orders + Payment + ReturnRequest + Refund; Product + OrderItem + ReturnItem"
t21.rows[2].cells[3].text = "GET /api/orders/{id}/status; /api/reports/*; Figs. 3\u20134"
t21.rows[3].cells[0].text = "Update"
t21.rows[3].cells[1].text = "Approve/Reject; Receive; Inspect (GOOD/DAMAGED/DEFECTIVE)"
t21.rows[3].cells[2].text = "ReturnRequest; Inspection"
t21.rows[3].cells[3].text = "PUT /approve, /receive, /inspect; trigger blocks skips (Fig. lifecycle)"
t21.rows[4].cells[0].text = "Delete / Controlled Removal"
t21.rows[4].cells[1].text = "No hard deletes; Rejected/terminal states + ON DELETE RESTRICT"
t21.rows[4].cells[2].text = "All (FK RESTRICT); ReturnRequest terminal"
t21.rows[4].cells[3].text = "DELETE Customer blocked (TC-05); destructive admin guarded"

# ---- Table 22 rules (index 22) ----
rules = [
    ("Late return blocked (return window)", "BEFORE INSERT trigger trg_validate_return_window: MIN(return_window_days) vs DATEDIFF(order_date, NOW())", "400 \u2018Return window expired\u2019; Fig. blocked_late_return (Order 3, 45d vs 7d)"),
    ("Excess quantity blocked", "BEFORE INSERT trg_validate_return_quantity: NEW.qty <= purchased - already-returned (excluding Rejected)", "400 \u2018Excess return quantity\u2019; TC-01 CHECK + trigger"),
    ("Invalid state jump blocked", "BEFORE UPDATE trg_check_return_state_transition: Requested\u2192Approved/Rejected\u2192Received\u2192Inspected\u2192Refunded/Rejected", "400 invalid-transition; terminal states frozen; TC-06"),
    ("Duplicate refund prevented", "sp_process_refund checks status=Inspected + COUNT(Processed)=0; FOR UPDATE lock", "2nd concurrent call \u2192 400; TC-09 exactly 1\u00d7200 + 1\u00d7400"),
    ("Atomic refund + rollback", "Procedure SQLEXCEPTION EXIT HANDLER \u2192 ROLLBACK + RESIGNAL; audit + restock in same txn", "TC-08: invalid IDs leave zero orphan Refund rows"),
    ("Injection / auth / RBAC", "mysql-connector %s parameterized queries; bcrypt; JWT require_roles; @current_app_user for audit actor", "401 bad login; 403 /api/audit for non-admin (Fig. access_denied_403)"),
    ("GOOD restock + audit", "Procedure restocks Inventory\u2192AVAILABLE only if condition=GOOD; AFTER UPDATE triggers log every change", "AuditLog viewer (Fig. 5); actor stamped per caller"),
]
t22 = d.tables[22]
for i in range(1, len(t22.rows)):
    for c in t22.rows[i].cells:
        c.text = ""
for i, vals in enumerate(rules):
    if i+1 < len(t22.rows):
        for j, v in enumerate(vals):
            t22.rows[i+1].cells[j].text = v
    else:
        add_row(22, list(vals))

# ---- Table 23 reports (index 23) ----
reps = [
    ("Order history with returns (Query a)", "Multi-LEFT JOIN Orders\u22c8Customer\u22c8Payment\u22c8ReturnRequest\u22c8Refund; ORDER BY date DESC", "Full order + payment + return + refunded amount table"),
    ("Pending returns queue (Query b)", "JOIN + WHERE status IN (Approved, Received) + GROUP BY + COUNT items", "Warehouse/support worklist ordered oldest-first"),
    ("Refund status by order (Query c)", "LEFT JOIN + COALESCE(amount,0); payment vs refunded", "Per-order paid vs credited reconciliation"),
    ("Return rate per product (Query d)", "LEFT JOIN + SUM(sold)/SUM(returned) + ROUND %; GROUP BY product", "Analytics bar: highest-return product first"),
    ("Monthly refund totals (Query e)", "DATE_FORMAT(%Y-%m) + COUNT/SUM WHERE Processed; GROUP BY month", "Finance month-wise refund count + value"),
    ("Top return reasons (Query f)", "GROUP BY reason + COUNT + SUM(refunded); ORDER BY frequency", "Pareto of Defective/Wrong-size/Late/Damaged reasons"),
]
t23 = d.tables[23]
for i in range(1, len(t23.rows)):
    for c in t23.rows[i].cells:
        c.text = ""
for i, vals in enumerate(reps):
    if i+1 < len(t23.rows):
        for j, v in enumerate(vals):
            t23.rows[i+1].cells[j].text = v
    else:
        add_row(23, list(vals))

# ---- 3.7 screenshots: map placeholders ----
# Placeholders: four "[Insert application screenshot here]" paras with Figure 2-5 captions after each.
shots = [
    (os.path.join(SS, "customer_portal.png"), "Figure 2. Customer Portal \u2014 product catalogue, place order, request return, live order-status tracker"),
    (os.path.join(SS, "ops_dashboard.png"), "Figure 3. Operations Dashboard \u2014 support approval queue and warehouse receive/inspect queue"),
    (os.path.join(SS, "analytics_dashboard.png"), "Figure 4. Analytics Dashboard \u2014 return rate per product, monthly refunds, top reasons"),
    (os.path.join(SS, "audit_log.png"), "Figure 5. Admin Audit Log \u2014 immutable trigger-written trail (actor, old/new status, timestamp)"),
]
# find placeholder paras
ph = [p for p in d.paragraphs if p.text.strip() == "[Insert application screenshot here]"]
for p, (img, cap) in zip(ph[:4], shots):
    p.text = ""
    r = p.add_run()
    if os.path.exists(img):
        r.add_picture(img, width=Inches(6.0))
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
# update captions Figure 2-5
caps = [p for p in d.paragraphs if p.text.strip().startswith("Figure ")]
# caps include Figure 1 ER + Figure 2-5; update 2-5
for p, (img, cap) in zip([c for c in caps if not c.text.strip().startswith("Figure 1")][:4], shots):
    p.text = cap

# update Figure 1 caption (keep but ensure title)
for p in d.paragraphs:
    if p.text.strip().startswith("Figure 1"):
        p.text = "Figure 1. Entity-Relationship Diagram of the Proposed System (13 entities; 1:1 Inspection, 1:N Refund; item-level returns)"
        break

# ---- 3.8 tests Table 24 (index 24) ----
tests = [
    ("TC-01", "CHECK quantity > 0", "INSERT OrderItem quantity=0", "Rejected by engine", "Rejected (CHECK)", "Pass"),
    ("TC-02", "CHECK total_amount >= 0", "INSERT Orders total=-50.00", "Rejected", "Rejected (CHECK)", "Pass"),
    ("TC-03", "UNIQUE provider_reference", "Duplicate PAY-DEMO-001", "Duplicate-entry error", "Duplicate-entry error", "Pass"),
    ("TC-04", "ENUM domain", "ReturnRequest status='SuperStatus'", "Truncated/ENUM error", "Truncated/ENUM error", "Pass"),
    ("TC-05", "FK ON DELETE RESTRICT", "DELETE Customer 1 (has orders)", "FK-constraint block", "FK-constraint block", "Pass"),
    ("TC-06", "sp_process_refund state guard", "CALL on Approved (not Inspected) return", "Error \u2018must be Inspected\u2019", "Error as expected", "Pass"),
    ("TC-07", "Full lifecycle integration", "API: order\u2192return\u2192approve\u2192receive\u2192inspect\u2192refund", "201/200 chain, status Refunded", "Refunded end-to-end", "Pass"),
    ("TC-08", "Rollback on error (FIX 03)", "CALL sp_process_refund (99999,99999)", "ROLLBACK; zero Refund rows", "Zero orphan rows", "Pass"),
    ("TC-09", "Concurrent duplicate refund (FIX 02)", "2 parallel POST refund threads", "Exactly 1\u00d7200 + 1\u00d7400", "1\u00d7200 + 1\u00d7400 observed", "Pass"),
]
t24 = d.tables[24]
for i in range(1, len(t24.rows)):
    for c in t24.rows[i].cells:
        c.text = ""
for i, vals in enumerate(tests):
    if i+1 < len(t24.rows):
        for j, v in enumerate(vals):
            t24.rows[i+1].cells[j].text = v
    else:
        add_row(24, list(vals))

replace("[Key results and observations.]",
    "Key results: 9/9 tests passed (100%). Constraints (TC-01\u2013TC-05) prove the engine rejects bad quantities, negative amounts, duplicate gateway references, illegal ENUM states, and restricted deletes. TC-06/TC-08 prove the procedure guards state and rolls back fully on error with no orphan rows. TC-07 proves the API-to-database chain completes Order\u2192Refunded through all six states. TC-09 proves exactly-once refund under concurrency (one 200, one 400). Benchmarks (benchmarks/run_benchmarks.py): pending-returns median 0.22 ms (1K indexed) to 2.95 ms (100K indexed); sp_process_refund median 1.23 ms; mysqldump backup/restore of 111,025 orders verified with checksum PASS. Together this confirms the application correctly uses the designed database and enforces all critical business rules.")

# ---- Chapter 4 ----
replace("[Conclusion - approximately 1 to 2 paragraphs.]",
    "This project addressed scattered, unauditable e-commerce after-sales handling by delivering a centralized MySQL 8 DBMS and a FastAPI dashboard for the full order-to-refund lifecycle. The 13-table 3NF design with PK/FK, CHECK, UNIQUE, ENUM, and RESTRICT rules was implemented with five triggers and the atomic sp_process_refund procedure, and all 17 REST endpoints operate directly on this database through parameterized SQL with JWT RBAC. The system implements ordering, item-level returns, support approval, warehouse receive/inspection, exactly-once refunds with GOOD-condition restocking, immutable auditing, and six operational/analytical reports. Validation achieved 9/9 automated tests, indexed query performance to 100K scale, and verified disaster-recovery integrity. The outcome is a single queryable source of truth with enforced eligibility, state discipline, and traceable refunds, and hands-on mastery of ER modelling, normalization, triggers, transactions, API-backed DBMS development, and empirical testing.")
bullets = [
    "Simulated payment gateway \u2014 deterministic mock provider references only; no real bank/card network. Enhancement: PCI-scoped PSP integration (Razorpay/Stripe) with webhook reconciliation.",
    "Single-instance local scope \u2014 validated to 100K orders on one MySQL instance without replication. Enhancement: AWS RDS master\u2013replica with automated failover and read scaling.",
    "Manual inspection verdict \u2014 condition (GOOD/DAMAGED/DEFECTIVE) entered by warehouse role. Enhancement: ML return-risk prediction at order time and vision-assisted inspection plus SMS/email refund notifications.",
]
i = 0
for p in d.paragraphs:
    if p.text.strip() in ("[Limitation / Future enhancement 1]", "[Limitation / Future enhancement 2]", "[Limitation / Future enhancement 3]"):
        p.text = bullets[i]; i += 1

# ---- References ----
refs = [
    "[1] R. Elmasri and S. B. Navathe, Fundamentals of Database Systems, 7th ed. Boston, MA, USA: Pearson, 2016.",
    "[2] A. Silberschatz, H. F. Korth, and S. Sudarshan, Database System Concepts, 7th ed. New York, NY, USA: McGraw-Hill, 2020.",
    "[3] C. J. Date, An Introduction to Database Systems, 8th ed. Boston, MA, USA: Addison-Wesley, 2004.",
    "[4] T. Connolly and C. Begg, Database Systems: A Practical Approach to Design, Implementation, and Management, 6th ed. Boston, MA, USA: Pearson, 2015.",
    "[5] Oracle Corporation, MySQL 8.0 Reference Manual: Triggers, Stored Programs, and InnoDB Storage Engine. Accessed: Oct. 8, 2026. [Online]. Available: https://dev.mysql.com/doc/refman/8.0/en/",
    "[6] S. Ram\u00edrez, FastAPI Documentation \u2014 Modern Python Web APIs. Accessed: Oct. 8, 2026. [Online]. Available: https://fastapi.tiangolo.com/",
    "[7] Python Software Foundation, mysql-connector-python Developer Guide (parameterized queries and transactions). Accessed: Oct. 8, 2026. [Online]. Available: https://dev.mysql.com/doc/connector-python/en/",
    "[8] M. Jones, J. Bradley, and N. Sakimura, \u201cJSON Web Token (JWT),\u201d IETF RFC 7519, May 2015, doi: 10.17487/RFC7519.",
]
ri = 0
for p in d.paragraphs:
    if p.text.strip() == "[Replace with an actual source cited in the report.]" and ri < len(refs):
        p.text = refs[ri]; ri += 1

# ---- Appendices ----
replace("[Database script / file reference]",
    "Appendix A files (ecommerce_refund_dbms/db/): schema.sql (13 CREATE TABLEs, InnoDB, 3NF), triggers.sql (5 triggers: return-window, quantity, state machine, 2 audit), procedures.sql (sp_process_refund, atomic, duplicate-safe, rollback handler), indexes.sql (10 B-Tree indexes), queries.sql (queries a\u2013f), seed.py (demo seed + bulk generator to 100K). Restore: python db/seed.py; backup: mysqldump --single-transaction --routines --triggers ecommerce_db > backup.sql (verified 111,025 orders).")
replace("[Source-code / repository reference]",
    "Appendix B (ecommerce_refund_dbms/): backend/main.py (17 REST endpoints), backend/auth.py (bcrypt + JWT RBAC), backend/database.py (parameterized connector), backend/models.py, backend/payment_gateway.py (mock), frontend/index.html (SPA dashboard), tests/test_suite.py (9 pytest cases), benchmarks/run_benchmarks.py, docker-compose.yml. Run: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 \u2192 http://127.0.0.1:8000. Demo logins (password123): customer_user / support_agent / warehouse_op / admin_user.")
replace("[Additional supporting material]",
    "Appendix C: docs/screenshots/ (customer_portal, ops_dashboard, api_flow 7-state stepper, access_denied_403, audit_log, analytics_dashboard, blocked_late_return, test_run_output 9/9, benchmark_chart); docs/er_diagram.png + .mmd; docs/REPORT.md (inventory metrics); docs/test_report.md (9-test matrix); Presentations/PPT1\u2013PPT3 (Review 1\u20133). Extra evidence below: return-lifecycle state diagram and three-layer architecture.")

# ---- Extra figures at end (lifecycle + architecture + benchmark/test evidence) ----
# append at end of document
extra = [
    (os.path.join(DIAG, "lifecycle.png"), "Figure 6. Return lifecycle state machine enforced by trg_check_return_state_transition (terminal states Refunded / Rejected)"),
    (os.path.join(DIAG, "architecture.png"), "Figure 7. Three-layer system architecture: SPA client, FastAPI + JWT service, MySQL 8 data layer"),
    (os.path.join(SS, "test_run_output.png"), "Figure 8. Automated test evidence \u2014 pytest 9/9 passed (constraints, procedure, lifecycle, rollback, concurrency)"),
    (os.path.join(SS, "benchmark_chart.png"), "Figure 9. Performance benchmark \u2014 indexed query latency at 1K/10K/100K scales; sp_process_refund median 1.23 ms"),
    (os.path.join(SS, "blocked_late_return.png"), "Figure 10. Business-rule evidence \u2014 trigger blocks late return outside product window (Order 3, 45 days vs 7-day window)"),
]
for img, cap in extra:
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    if os.path.exists(img):
        r.add_picture(img, width=Inches(6.0))
    c = d.add_paragraph(cap)
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER

# ---- List of Tables / Figures titles update (Tables 6,7) ----
# Table 6 LOT is d.tables[6]: update page nos blank (leave), titles already ok
# Table 7 LOF d.tables[7]: update Fig2-5 titles + add Fig6-10
lof_titles = [
    "Entity-Relationship Diagram of the Proposed System",
    "Customer Portal \u2014 catalogue, ordering, returns, status tracker",
    "Operations Dashboard \u2014 support and warehouse queues",
    "Analytics Dashboard \u2014 return rates, monthly refunds, top reasons",
    "Admin Audit Log \u2014 immutable trail",
]
t7 = d.tables[7]
for i, t_ in enumerate(lof_titles):
    if i+1 < len(t7.rows):
        t7.rows[i+1].cells[1].text = t_
extra_lof = [
    ("Figure 6", "Return lifecycle state machine"),
    ("Figure 7", "Three-layer system architecture"),
    ("Figure 8", "Automated test evidence (9/9 passed)"),
    ("Figure 9", "Performance benchmark chart"),
    ("Figure 10", "Late-return trigger block evidence"),
]
for a, b in extra_lof:
    add_row(7, [a, b, ""])

print("Part3 done")
d.save(OUT)
