"""Part 5: Streamlit-only report. Drops FastAPI/JWT, 10-test suite, new evidence."""
import docx, os
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from copy import deepcopy

OUT = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\REPORT_FINAL\25WU0102114_Prajvesh_DBMS_PBL_Report.docx"
SS = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\ecommerce_refund_dbms\docs\screenshots"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
d = docx.Document(OUT)


def has_image(p):
    return len(p._element.findall(".//%sdrawing" % W)) > 0


def replace_image_before_caption(caption_start, image_path, width=6.0):
    for j, p in enumerate(d.paragraphs):
        if p.text.strip().startswith(caption_start):
            for k in range(j - 1, max(j - 4, -1), -1):
                if has_image(d.paragraphs[k]):
                    d.paragraphs[k].text = ""
                    r = d.paragraphs[k].add_run()
                    r.add_picture(image_path, width=Inches(width))
                    d.paragraphs[k].alignment = WD_ALIGN_PARAGRAPH.CENTER
                    return True
    return False


def set_caption(caption_start, new_text):
    for p in d.paragraphs:
        if p.text.strip().startswith(caption_start):
            p.text = new_text
            return True
    return False


def add_row(ti, vals):
    t = d.tables[ti]
    row = t.add_row()
    for i, v in enumerate(vals):
        if i < len(row.cells):
            row.cells[i].text = v

# ---- Abstract ----
abstract = ("E-commerce post-purchase operations routinely fail when orders, returns, and refunds are tracked in disconnected spreadsheets, "
"causing untracked status changes, duplicate refunds, and missing audit evidence. The objective of this project is to design and implement a centralized ACID-compliant DBMS for the complete order-to-refund lifecycle. "
"The solution uses a 13-table Third Normal Form (3NF) MySQL 8 (InnoDB) schema covering customers, products, inventory, orders, payments, item-level returns, warehouse inspection, refunds, and an immutable audit log; five triggers enforce return-window eligibility, return-quantity limits, strict state transitions, and automatic auditing; and one stored procedure, sp_process_refund, executes atomic refund processing with duplicate-refund prevention and full rollback on error [5], [6]. "
"A role-based Streamlit application implements ordering, returning, approving, receiving, inspecting, refunding, auditing, and analytics through direct parameterized SQL, with session-state RBAC for Customer, Support, Warehouse, and Admin [7]. "
"The completed system demonstrates the full lifecycle Order \u2192 Requested \u2192 Approved \u2192 Received \u2192 Inspected \u2192 Refunded, passes 10/10 automated pytest cases, sustains sub-millisecond indexed lookups at 1K scale, and verifies backup/restore integrity at 111,025 orders. "
"The application provides a single queryable source of truth for post-purchase operations with enforced business rules and traceable refunds.")
print("abstract words:", len(abstract.split()))
for p in d.paragraphs:
    if p.text.startswith("E-commerce post-purchase operations routinely fail"):
        p.text = abstract
        break

# ---- Undertaking refs ----
for p in d.paragraphs:
    if "appropriate acknowledgement has been given" in p.text:
        p.text = (p.text.split(". The MySQL")[0]
                  + ". The MySQL 8 documentation, Streamlit documentation, and standard DBMS textbooks consulted are cited in the References [5]-[7].")
        break

# ---- Objectives (both dupes) ----
for p in d.paragraphs:
    if p.text.startswith("Validate the system with"):
        p.text = ("Validate the system with 10 automated pytest cases (100% pass) covering engine constraints, procedure guards, "
"full lifecycle, rollback, duplicate prevention, and auth/RBAC.")

# ---- 3.1 overview ----
for p in d.paragraphs:
    if p.text.startswith("The application was re-implemented in Streamlit"):
        p.text = ("The application is a role-based Streamlit multi-page app that connects directly to MySQL 8 with parameterized SQL "
"in streamlit_app/db_ops.py: login is verified with bcrypt against AppUser\u22c8Role and the session role gates six pages (Customer Portal, "
"Operations, Refunds, Analytics, Audit Log, Lifecycle Demo). Every screen operation maps to the 3NF schema in Chapter 2: ordering inserts "
"Orders/OrderItem/Payment in one explicit transaction, returning inserts ReturnRequest/ReturnItem (trigger-validated), approvals/receives/inspections "
"are constrained UPDATEs/INSERTs, and refunds execute only through sp_process_refund. Analytics screens run the six catalogued JOIN/GROUP BY queries with "
"st.metric/st.bar_chart/st.dataframe, and the Admin audit page reads AuditLog. Validation is performed by the pytest suite in tests/test_streamlit_ops.py "
"(TC-01\u2013TC-10), which drives the same database code the UI uses [7]. No screen uses isolated or static data.")
        break

# ---- Ch4 conclusion ----
for p in d.paragraphs:
    if p.text.startswith("This project addressed scattered"):
        p.text = ("This project addressed scattered, unauditable e-commerce after-sales handling by delivering a centralized MySQL 8 DBMS and a role-based "
"Streamlit application for the full order-to-refund lifecycle. The 13-table 3NF design with PK/FK, CHECK, UNIQUE, ENUM, and RESTRICT rules was implemented "
"with five triggers and the atomic sp_process_refund procedure, and all six Streamlit pages operate directly on this database through parameterized SQL with "
"bcrypt login and session-state RBAC. The system implements ordering, item-level returns, support approval, warehouse receive/inspection, exactly-once refunds "
"with GOOD-condition restocking, immutable auditing, and six operational/analytical reports. Validation achieved 10/10 automated tests, indexed query performance "
"to 100K scale, and verified disaster-recovery integrity. The outcome is a single queryable source of truth with enforced eligibility, state discipline, and "
"traceable refunds, and hands-on mastery of ER modelling, normalization, triggers, transactions, Streamlit-backed DBMS development, and empirical testing.")
        break

# ---- Table 19 ----
t19 = d.tables[19]
t19.rows[3].cells[1].text = "Streamlit 1.65 (six role-gated pages); bcrypt auth; session-state RBAC"
t19.rows[6].cells[1].text = ("ecommerce_refund_dbms/streamlit_app/ (app.py, db_ops.py, database.py, auth.py, payment_gateway.py), "
"tests/test_streamlit_ops.py (TC-01\u2013TC-10)")

# ---- Table 22 RBAC rows ----
t22 = d.tables[22]
for r in t22.rows[1:]:
    cells = [c.text for c in r.cells]
    if any("JWT require_roles" in c for c in cells):
        r.cells[1].text = ("mysql-connector %s parameterized queries; bcrypt login; session-role page gating; "
"@current_app_user for audit actor")
        r.cells[2].text = "Wrong password rejected; Audit page hidden for non-admin roles"
    if any("/api/audit" in c for c in cells) and any("403" in c for c in cells):
        r.cells[1].text = "Destructive/terminal actions confirmed in UI; terminal states frozen by trigger"
        r.cells[2].text = "Rejected/Refunded returns cannot move; TC-05 RESTRICT delete blocked"

# ---- Table 8: drop JWT + SPA rows ----
t8 = d.tables[8]
for r in list(t8.rows)[1:]:
    if r.cells[0].text.strip() in ("JWT", "SPA"):
        r._element.getparent().remove(r._element)

# ---- Table 24: rewrite 10 rows ----
t24 = d.tables[24]
for r in list(t24.rows)[1:]:
    r._element.getparent().remove(r._element)
tests = [
    ("TC-01", "CHECK quantity > 0", "INSERT OrderItem quantity=0", "Rejected by engine", "Rejected (CHECK)", "Pass"),
    ("TC-02", "CHECK total_amount >= 0", "INSERT Orders total=-50.00", "Rejected", "Rejected (CHECK)", "Pass"),
    ("TC-03", "UNIQUE provider_reference", "Duplicate existing gateway ref", "Duplicate-entry error", "Duplicate-entry error", "Pass"),
    ("TC-04", "ENUM status domain", "ReturnRequest status='SuperStatus'", "ENUM/truncation error", "Error as expected", "Pass"),
    ("TC-05", "FK ON DELETE RESTRICT", "DELETE Customer 1 (has orders)", "FK-constraint block", "FK-constraint block", "Pass"),
    ("TC-06", "Procedure state guard", "db_ops refund on Requested return", "Error 'must be Inspected'", "Error as expected", "Pass"),
    ("TC-07", "Full lifecycle (db_ops)", "Chain order\u2192return\u2192refund + reports", "Refunded + audit entries", "Refunded + audited", "Pass"),
    ("TC-08", "Atomic rollback", "process_refund(99999,99999)", "AppError; zero Refund rows", "Zero orphan rows", "Pass"),
    ("TC-09", "Late + duplicate guards", "Order-3 late return; 2nd refund", "Window-expiry + duplicate errors", "Both blocked", "Pass"),
    ("TC-10", "Auth + RBAC", "4 role logins; bad password", "Roles resolved; rejection", "Roles resolved; rejected", "Pass"),
]
for vals in tests:
    add_row(24, list(vals))

for p in d.paragraphs:
    if p.text.startswith("Key results: 13/13"):
        p.text = ("Key results: 10/10 tests passed (100%, TC-01\u2013TC-10, Streamlit suite). Constraint tests (TC-01\u2013TC-05) prove the engine rejects "
"bad quantities, negative amounts, duplicate gateway references, illegal ENUM states, and restricted deletes \u2014 independent of any client. TC-06 proves the "
"procedure refuses non-Inspected returns through the same db_ops path the UI calls. TC-07 proves the full Order\u2192Refunded chain with audit entries and "
"working catalogue/analytics queries. TC-08 proves atomic rollback with zero orphan rows. TC-09 proves the late-return window trigger and the exactly-once "
"refund guard. TC-10 proves bcrypt login resolves all four RBAC roles and rejects bad passwords. Benchmarks (benchmarks/run_benchmarks.py): pending-returns "
"median 0.22 ms (1K indexed) to 2.95 ms (100K indexed); sp_process_refund median 1.23 ms; mysqldump backup/restore of 111,025 orders verified with checksum PASS. "
"Together this confirms the Streamlit application correctly uses the designed database and enforces all critical business rules [6].")
        break

# ---- Figures 8 + 10 ----
replace_image_before_caption("Figure 8.", os.path.join(SS, "test_run_output.png"))
set_caption("Figure 8.", "Figure 8. Automated test evidence \u2014 pytest 10/10 passed (TC-01\u2013TC-10, Streamlit suite)")
replace_image_before_caption("Figure 10.", os.path.join(SS, "st_blocked_return.png"))
set_caption("Figure 10.", "Figure 10. Business-rule evidence \u2014 Streamlit late-return guard: trigger blocks Order 3 (45 days vs 7-day window)")
print("fig8/10 swapped")

# ---- Appendix B / C ----
for p in d.paragraphs:
    if p.text.startswith("Appendix B (ecommerce_refund_dbms/"):
        p.text = ("Appendix B (ecommerce_refund_dbms/): streamlit_app/app.py (6 role-gated pages: Customer Portal, Operations, Refunds, Analytics, "
"Audit Log, Lifecycle Demo), streamlit_app/db_ops.py (parameterized operations + AppError surfacing of trigger/procedure messages), "
"streamlit_app/database.py (pooled MySQL connector), auth.py (bcrypt), payment_gateway.py (mock), tests/test_streamlit_ops.py (TC-01\u2013TC-10), "
"db/*.sql (schema, triggers, procedures, indexes, queries), benchmarks/run_benchmarks.py. "
"Run: streamlit run streamlit_app/app.py --server.port 8501 \u2192 http://127.0.0.1:8501. Demo logins (password123): customer_user / support_agent / warehouse_op / admin_user.")
        break
for p in d.paragraphs:
    if p.text.startswith("Appendix C:"):
        p.text = ("Appendix C: docs/screenshots/ (st_customer_portal, st_ops_dashboard, st_analytics, st_audit_log, st_lifecycle, st_blocked_return, "
"test_run_output 10/10, benchmark_chart); docs/er_diagram.png + .mmd; docs/REPORT.md; docs/test_report.md (TC-01\u2013TC-10 matrix); "
"Presentations/PPT1\u2013PPT3 + PPT3_Script.md. Extra evidence below: return-lifecycle state diagram and three-layer architecture.")
        break

# ---- Figure 7 caption ----
set_caption("Figure 7.", "Figure 7. Three-layer system architecture: Streamlit app (direct SQL), MySQL 8 data layer")

# ---- References: delete [6] + [8], renumber [7]->[6], [9]->[7] ----
for p in list(d.paragraphs):
    if p.text.startswith("[6] S. Ram") or p.text.startswith("[8] M. Jones"):
        p._element.getparent().remove(p._element)
print("refs removed")
for p in d.paragraphs:
    if "[9]" in p.text and not p.text.startswith("Example"):
        p.text = p.text.replace("[9]", "\u27e6CIT_S\u27e7")
for p in d.paragraphs:
    if "[8]" in p.text and ("Example" not in p.text and "for example" not in p.text):
        # drop JWT cite remnants (only in-text, non-example)
        p.text = p.text.replace("[8], ", "").replace("[8]", "")
for p in d.paragraphs:
    if "[7]" in p.text and not p.text.startswith("Example"):
        p.text = p.text.replace("[7]", "[6]")
for p in d.paragraphs:
    if "\u27e6CIT_S\u27e7" in p.text:
        p.text = p.text.replace("\u27e6CIT_S\u27e7", "[7]")
# rename entries
for p in d.paragraphs:
    if p.text.startswith("[7] Python Software"):
        p.text = "[6]" + p.text[3:]
    if p.text.startswith("[9] Streamlit"):
        p.text = "[7]" + p.text[3:]

# ---- LOF rows ----
t7 = d.tables[7]
for r in t7.rows:
    if r.cells[0].text.strip() == "Figure 8":
        r.cells[1].text = "Automated test evidence (10/10 passed)"
    if r.cells[0].text.strip() == "Figure 10":
        r.cells[1].text = "Streamlit late-return trigger block evidence"

print("part5 done")
d.save(OUT)
