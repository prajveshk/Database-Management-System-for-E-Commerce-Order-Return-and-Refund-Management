# Streamlit Application

Interactive role-based UI for the E-Commerce Order, Return and Refund DBMS.
It connects **directly to MySQL 8** with parameterized SQL
(`streamlit_app/db_ops.py`). All business rules (return window, quantity
limits, state machine, audit trail, atomic refunds) are enforced inside
the database by triggers and `sp_process_refund`.

The Streamlit app is the project's sole application layer. All business rules (return window, quantity
limits, state machine, audit trail, atomic refunds) are enforced inside
the database by triggers and `sp_process_refund`.

## Run

From the project root (`ecommerce_refund_dbms/`):

```bash
# 1. MySQL 8 on 127.0.0.1:3307 with seeded ecommerce_db (see ../REPORT_FINAL)
# 2. Launch the app
streamlit run streamlit_app/app.py --server.port 8501
```

Open `http://127.0.0.1:8501`.

## Demo logins (password for all: `password123`)

| Username | Role | Pages |
| :--- | :--- | :--- |
| `customer_user` | Customer | Customer Portal, Analytics, Lifecycle Demo (view) |
| `support_agent` | Support | Operations (approve/reject), Refunds, Analytics, Lifecycle Demo |
| `warehouse_op` | Warehouse | Operations (receive/inspect), Analytics |
| `admin_user` | Admin | All pages incl. Audit Log + guided end-to-end demo |

## Pages → tables

| Page | Tables used |
| :--- | :--- |
| Customer Portal | Product, Orders, OrderItem, Payment, ReturnRequest, ReturnItem |
| Operations | ReturnRequest, ReturnItem, Inspection, Inventory |
| Refunds | ReturnRequest, Refund, Payment (via `sp_process_refund`) |
| Analytics | All sales/return tables (JOIN + GROUP BY reports a–f) |
| Audit Log | AuditLog |
| Lifecycle Demo | Full chain incl. Inspection + Refund + AuditLog |
