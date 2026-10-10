# Design and Implementation of a Database Management System for E-Commerce Order, Return and Refund Management

A complete B.Tech AI & ML Database Systems Capstone Project (3-Stage Review Ready) implementing an ACID-compliant MySQL 8 3NF database schema, database-enforced integrity triggers, stored procedures with atomic transactions and rollback handlers, and a role-based Streamlit application with direct database connectivity.

---

## 1. Quick Start & Setup

### Prerequisites
- Python 3.11+ (`pip install streamlit mysql-connector-python bcrypt pandas`)
- MySQL Server 8.0 on 127.0.0.1:3307 with seeded `ecommerce_db`

### One-Command Setup (Local MySQL)
```bash
# 1. Initialize MySQL schema, triggers, procedures, indexes & demo seed data
python db/seed.py

# 2. Launch Streamlit App
streamlit run streamlit_app/app.py --server.port 8501
```
Open your browser at: `http://127.0.0.1:8501`

---

## 2. Demo Credentials

The system includes pre-seeded demo accounts for all 4 RBAC system roles (Password for all demo accounts: `password123`):

| Role | Username | Password | Access Rights & Purpose |
| :--- | :--- | :--- | :--- |
| **Customer** | `customer_user` | `password123` | Place orders, view my orders, request returns (Alice Smith). |
| **Support Agent** | `support_agent` | `password123` | View pending returns, approve/reject return requests, trigger refunds. |
| **Warehouse Op** | `warehouse_op` | `password123` | Receive returned packages, inspect item condition (GOOD/DAMAGED/DEFECTIVE). |
| **Admin** | `admin_user` | `password123` | Full system access + Audit Log viewer + guided lifecycle demo. |

---

## 3. Running Automated Tests & Benchmarks

### Execute Pytest Automated Test Suite
```bash
python -m pytest tests/test_streamlit_ops.py -v
```
*Runs 10 automated tests (TC-01–TC-10: CHECK/UNIQUE/ENUM/FK constraints, procedure state guard, full db_ops lifecycle, atomic rollback, late/duplicate guards, auth/RBAC).*

### Execute Performance & Disaster Recovery Benchmarks
```bash
python benchmarks/run_benchmarks.py
```
*Seeds datasets at 1K, 10K, 100K scale, times key queries with & without indexes, executes EXPLAIN analysis, benchmarks procedure speed, and runs mysqldump backup/restore verification.*

---

## 4. System Architecture

```
+-----------------------------------------------------------------------------------+
|                             APPLICATION LAYER                                     |
|   Streamlit App: Customer Portal | Operations | Refunds | Analytics | Audit | Demo  |
|   Session-state RBAC (bcrypt)          Mocked Payment Gateway                      |
+-----------------------------------------------------------------------------------+
                                          │
                                    Parameterized SQL
                                          ▼
+-----------------------------------------------------------------------------------+
|                                 DATA LAYER                                        |
|                           MySQL 8 InnoDB DBMS (3NF)                               |
|   • PK / FK Restrictions   • Triggers (Validation, State, Audit)                  |
|   • Stored Procedures      • B-Tree Performance Indexes                           |
|   • ACID Transactions      • Immutable Audit Log                                  |
+-----------------------------------------------------------------------------------+
```

---

## 5. Honest Project Limitations

1. **Simulated Payment Gateway:** Payment transactions use a deterministic mock module returning synthetic provider references without connecting to real bank card networks.
2. **Local Scale Scope:** Tested up to 100,000 order records on a single database instance rather than distributed multi-region scale.
3. **Single Database Instance:** Deployed on a single MySQL instance without master-slave read replication.

---

## 6. Future Scope

1. **ML-Based Return Risk Prediction:** Integrate machine learning models to predict customer return probability at order placement time.
2. **Automated Return Eligibility:** AI-assisted computer vision inspection of warehouse return images.
3. **Event-Driven Architecture:** Webhook integration for instant SMS/Email customer notification upon refund completion.
4. **Cloud Replication:** Master-replica setup on AWS RDS with automated failover.
