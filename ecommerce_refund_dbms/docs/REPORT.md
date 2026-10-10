# Project Evaluation Report: Design and Implementation of a Database Management System for E-Commerce Order, Return and Refund Management

**Degree Program:** B.Tech Artificial Intelligence & Machine Learning  
**Subject:** Database Management Systems (DBMS) Final Project  
**Engine:** MySQL 8.0.46 (InnoDB Engine, ACID Compliant)  
**App:** Python 3.13 + Streamlit 1.65 (direct parameterized SQL, session-state RBAC)  

---

## 1. System Inventory Metrics (Empirical Count)

| Inventory Component | Count | System Notes & Implementation File |
| :--- | :---: | :--- |
| **Relational Tables (3NF)** | **13** | `Role`, `AppUser`, `Customer`, `Product`, `Inventory`, `Orders`, `OrderItem`, `Payment`, `ReturnRequest`, `ReturnItem`, `Inspection`, `Refund`, `AuditLog` ([schema.sql](file:///C:/Users/Prajvesh/.gemini/antigravity/scratch/ecommerce_refund_dbms/db/schema.sql)) |
| **Database Triggers** | **5** | Return window validation, Return quantity validation, Invalid state transition check (FIX 01), Return audit log, Refund audit log ([triggers.sql](file:///C:/Users/Prajvesh/.gemini/antigravity/scratch/ecommerce_refund_dbms/db/triggers.sql)) |
| **Stored Procedures** | **1** | `sp_process_refund`: Atomic transaction with exit handler rollback (FIX 03) and duplicate refund prevention (FIX 02) ([procedures.sql](file:///C:/Users/Prajvesh/.gemini/antigravity/scratch/ecommerce_refund_dbms/db/procedures.sql)) |
| **Streamlit App Pages** | **6** | Sidebar login + session-state RBAC; Customer Portal; Operations; Refunds; Analytics; Audit Log (Admin); Lifecycle Demo stepper (`streamlit_app/app.py` + `streamlit_app/db_ops.py` with direct parameterized SQL) |

---

## 2. Automated Test Suite Results

The system was evaluated against 10 automated pytest cases (TC-01–TC-10, `tests/test_streamlit_ops.py`) covering engine constraints, procedure guards, the full db_ops lifecycle, atomic rollback, duplicate/late-return guards, and auth/RBAC.

| Category | Test Case | Result | Empirical Result & Verification Details |
| :--- | :--- | :---: | :--- |
| **Constraint** | `test_tc01_invalid_quantity_blocked` | **PASSED** | Engine blocked `quantity = 0` via `CHECK (quantity > 0)`. |
| **Constraint** | `test_tc02_negative_amount_blocked` | **PASSED** | Engine blocked `total_amount = -50.00` via `CHECK (total_amount >= 0)`. |
| **Constraint** | `test_tc03_duplicate_provider_reference_blocked` | **PASSED** | Engine blocked duplicate `provider_reference` via `UNIQUE` constraint. |
| **Constraint** | `test_tc04_bad_status_enum_blocked` | **PASSED** | Engine blocked invalid status `'SuperStatus'` via `ENUM` status domain. |
| **Constraint** | `test_tc05_fk_restrict_blocked` | **PASSED** | Engine blocked `DELETE FROM Customer` via `ON DELETE RESTRICT`. |
| **Guard** | `test_tc06_refund_requires_inspected_state` | **PASSED** | Stored procedure `sp_process_refund` rejected return not in `'Inspected'` state. |
| **Lifecycle** | `test_tc07_full_lifecycle_via_db_ops` | **PASSED** | Full db_ops lifecycle: Order -> Requested -> Approved -> Received -> Inspected -> Refunded, with audit entries. |
| **Rollback** | `test_tc08_rollback_on_procedure_error` | **PASSED** | Failed refund left zero orphan `Refund` rows (atomic rollback). |
| **Guards** | `test_tc09_duplicate_refund_blocked` | **PASSED** | Late return (order 3) blocked by window trigger; second refund rejected as duplicate. |
| **Auth** | `test_tc10_auth_and_rbac` | **PASSED** | bcrypt login resolves all 4 RBAC roles; wrong password rejected. |

**Overall Test Result:** 10 / 10 Passed (100% Pass Rate). See [test_report.md](file:///C:/Users/Prajvesh/.gemini/antigravity/scratch/ecommerce_refund_dbms/docs/test_report.md).

---

## 3. Database Performance & Recovery Benchmarks

### 3.1 Query Execution Latency Across Data Scales (1K, 10K, 100K Records)

Measurements were taken using high-precision performance counters across 5 runs per configuration (median reported in milliseconds):

| Query Category | Scale: 1K (Indexed) | Scale: 1K (Unindexed) | Scale: 10K (Indexed) | Scale: 10K (Unindexed) | Scale: 100K (Indexed) | Scale: 100K (Unindexed) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pending Returns** (`b`) | **0.22 ms** | 0.32 ms | **0.55 ms** | 0.61 ms | **2.95 ms** | 2.59 ms |
| **Order History** (`a`) | **5.98 ms** | 4.86 ms | **54.10 ms** | 50.67 ms | **692.29 ms** | 584.52 ms |
| **Refund Status** (`c`) | **4.96 ms** | 4.48 ms | **53.40 ms** | 44.91 ms | **601.94 ms** | 597.84 ms |

### 3.2 EXPLAIN Optimization Plan Analysis (Scale: 10K)

- **Query:** `Pending Returns Awaiting Inspection`
- **Indexed Access Plan:** `type: ref / eq_ref`, key used: `idx_return_status` (Filtered rows: 100%, 0 temporary tables created).
- **Unindexed Access Plan:** `type: ALL`, full table scan across all ReturnRequest records.

### 3.3 Refund Stored Procedure Execution Speed

- **Procedure:** `sp_process_refund(order_id, return_id)`
- **Median Execution Time:** **1.23 ms**
- **Average Execution Time:** **1.35 ms**

### 3.4 Disaster Recovery & Backup Verification

- **Backup Command:** `mysqldump --single-transaction --routines --triggers ecommerce_db > backup.sql`
- **Pre-Restore Order Rows:** **111,025**
- **Post-Restore Order Rows:** **111,025**
- **Checksum Verification Result:** **PASSED** (100% row & constraint integrity match)

---

## 4. Architectural Impact: Before vs After Comparison

| Assessment Metric | Before Implementation (Legacy Spreadsheet) | After Implementation (MySQL 8 DBMS) |
| :--- | :--- | :--- |
| **Status Visibility** | Isolated spreadsheets & manual logs; status updates untracked. | Single unified queryable record across 7 lifecycle states. |
| **Audit Trail** | Absent; inability to identify who modified order/return records. | Immutable audit trail (`AuditLog`) automatically written by triggers. |
| **Invalid State Transitions** | Manual status overwrite allowed out-of-order state skips. | Database trigger `trg_check_return_state_transition` blocks invalid hops (FIX 01). |
| **Refund Accuracy** | Duplication-prone; multiple refunds issued for single return. | Centralized procedure `sp_process_refund` enforces duplicate checks & transaction rollback (FIX 02 & 03). |

---

## 5. Visual Screenshots & Artifact Index

All generated presentation figures reside in `docs/screenshots/` (Streamlit app):
1. `st_customer_portal.png`: Customer portal — catalogue, order form, status tracker, return request.
2. `st_ops_dashboard.png`: Operations queue — approve/reject, receive, inspection.
3. `st_lifecycle.png`: Guided 7-state lifecycle demo stepper.
4. `st_audit_log.png`: Immutable Audit Log viewer (Admin role).
5. `st_analytics.png`: Analytics dashboard with metrics, charts, top reasons.
6. `st_blocked_return.png`: Trigger rejection message for late return outside return window.
7. `test_run_output.png`: Pytest automated suite run output (10/10 Passed).
8. `benchmark_chart.png`: Query latency benchmark chart (1K, 10K, 100K).
