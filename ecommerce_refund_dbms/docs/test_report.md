# Automated Test Report

**Project:** Design and Implementation of a Database Management System for E-Commerce Order, Return and Refund Management  
**Date:** 2026-10-11  
**Test Framework:** Pytest (tests/test_streamlit_ops.py, TC-01–TC-10)  
**Target DBMS:** MySQL 8.0.46 (InnoDB)  
**Application Under Test:** Streamlit app data layer (`streamlit_app/db_ops.py`)

---

## Test Results Summary Table

| Category | Test Case Name | Status | Measured Notes / Verification Details |
| :--- | :--- | :---: | :--- |
| **Constraint** | `test_tc01_invalid_quantity_blocked` | **PASSED** | Checked `CHECK (quantity > 0)`. Inserting quantity=0 was blocked by MySQL engine. |
| **Constraint** | `test_tc02_negative_amount_blocked` | **PASSED** | Checked `CHECK (total_amount >= 0)`. Negative amount (-50.00) rejected by engine. |
| **Constraint** | `test_tc03_duplicate_provider_reference_blocked` | **PASSED** | Checked `UNIQUE` constraint on Payment. Duplicate provider reference rejected. |
| **Constraint** | `test_tc04_bad_status_enum_blocked` | **PASSED** | Checked `ENUM` status domain. Invalid status ('SuperStatus') rejected. |
| **Constraint** | `test_tc05_fk_restrict_blocked` | **PASSED** | Checked `ON DELETE RESTRICT`. Attempting to delete customer with orders blocked by FK constraint. |
| **Guard** | `test_tc06_refund_requires_inspected_state` | **PASSED** | Verified `sp_process_refund` (via db_ops) rejects returns not in 'Inspected' state. |
| **Lifecycle** | `test_tc07_full_lifecycle_via_db_ops` | **PASSED** | Verified db_ops full flow: Order -> Requested -> Approved -> Received -> Inspected -> Refunded, with audit entries. |
| **Rollback** | `test_tc08_rollback_on_procedure_error` | **PASSED** | Failed refund on invalid IDs left zero orphan `Refund` rows (atomic rollback). |
| **Guards** | `test_tc09_duplicate_refund_blocked` | **PASSED** | Late return (order 3) blocked by window trigger; second refund on same return rejected as duplicate. |
| **Auth** | `test_tc10_auth_and_rbac` | **PASSED** | bcrypt login resolves all 4 RBAC roles (Customer, Support, Warehouse, Admin); wrong password rejected. |

Run: `python -m pytest tests/test_streamlit_ops.py -v` (requires MySQL on 127.0.0.1:3307 with seeded `ecommerce_db`).

---

**Total Executed:** 10  
**Passed:** 10  
**Failed:** 0  
**Pass Rate:** 100%  
