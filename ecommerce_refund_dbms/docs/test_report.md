# Automated Test Report

**Project:** Design and Implementation of a Database Management System for E-Commerce Order, Return and Refund Management  
**Date:** 2026-10-10  
**Test Framework:** Pytest 9.1.1  
**Target DBMS:** MySQL 8.0.46 (InnoDB)  

---

## Test Results Summary Table

| Category | Test Case Name | Status | Measured Notes / Verification Details |
| :--- | :--- | :---: | :--- |
| **Constraint** | `test_constraint_invalid_quantity` | **PASSED** | Checked `CHECK (quantity > 0)`. Inserting quantity=0 was blocked by MySQL engine. |
| **Constraint** | `test_constraint_negative_amount` | **PASSED** | Checked `CHECK (total_amount >= 0)`. Negative amount (-50.00) rejected by engine. |
| **Constraint** | `test_constraint_duplicate_provider_reference` | **PASSED** | Checked `UNIQUE` constraint on Payment. Duplicate provider reference rejected. |
| **Constraint** | `test_constraint_bad_status_enum` | **PASSED** | Checked `ENUM` status domain. Invalid status ('SuperStatus') rejected. |
| **Constraint** | `test_constraint_fk_restrict` | **PASSED** | Checked `ON DELETE RESTRICT`. Attempting to delete customer with orders blocked by FK constraint. |
| **Unit** | `test_unit_sp_process_refund_validation` | **PASSED** | Verified `sp_process_refund` rejects returns not in 'Inspected' state. |
| **Integration** | `test_integration_full_lifecycle` | **PASSED** | Verified API-to-DB full flow: Order -> Return -> Approve -> Receive -> Inspect -> Refund. |
| **Failure/Rollback** | `test_failure_rollback_on_procedure_error` | **PASSED** | Verified SQLEXCEPTION exit handler rolls back all changes on invalid return ID (FIX 03). |
| **Concurrency** | `test_concurrency_duplicate_refund_attempts` | **PASSED** | Parallel competing threads attempting duplicate refund; exactly 1 succeeded and 1 failed with duplicate refund error (FIX 02). |
| **Streamlit Auth** | `test_streamlit_auth_and_rbac` (TC-10) | **PASSED** | `streamlit_app/db_ops.authenticate` resolves all 4 RBAC roles; wrong password rejected. |
| **Streamlit Lifecycle** | `test_streamlit_full_lifecycle_via_db_ops` (TC-11) | **PASSED** | db_ops chain Order -> Requested -> Approved -> Received -> Inspected -> Refunded with audit entries. |
| **Streamlit Guards** | `test_streamlit_guards_late_return_and_duplicate_refund` (TC-12) | **PASSED** | Late return (order 3) blocked by window trigger; second refund blocked as duplicate. |
| **Streamlit Sanity** | `test_streamlit_catalog_and_analytics_queries` (TC-13) | **PASSED** | Catalogue and return-rate report return rows. |

Run: `python -m pytest tests/test_suite.py tests/test_streamlit_ops.py -v` (requires MySQL on 3307 + FastAPI on 8000 for the API tests).

---

**Total Executed:** 13  
**Passed:** 13  
**Failed:** 0  
**Pass Rate:** 100%  
