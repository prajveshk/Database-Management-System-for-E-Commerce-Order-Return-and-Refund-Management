"""E-Commerce Order, Return & Refund Management - Streamlit application.

Role-based UI over the 3NF MySQL 8 database. All reads/writes go through
streamlit_app/db_ops.py with parameterized SQL; business rules live in the
database (triggers + sp_process_refund) and their messages are shown as-is.

Run from the project root:
    streamlit run streamlit_app/app.py --server.port 8501

Demo logins (password for all: password123):
    customer_user (Customer) | support_agent (Support)
    warehouse_op (Warehouse) | admin_user (Admin)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from streamlit_app.db_ops import (  # noqa: E402
    AppError,
    audit_log,
    authenticate,
    inspect_return,
    list_products,
    my_orders,
    order_detail,
    pending_returns,
    place_order,
    process_refund,
    report_monthly_refunds,
    report_order_history,
    report_refund_status,
    report_return_rates,
    report_top_reasons,
    request_return,
    set_return_status,
    system_inventory,
)

st.set_page_config(
    page_title="E-Commerce Returns & Refunds DBMS",
    page_icon="📦",
    layout="wide",
)

CUSTOMER_PAGES = ["Customer Portal", "Analytics", "Lifecycle Demo"]
SUPPORT_PAGES = ["Operations", "Refunds", "Analytics", "Lifecycle Demo"]
WAREHOUSE_PAGES = ["Operations", "Analytics"]
ADMIN_PAGES = ["Customer Portal", "Operations", "Refunds", "Analytics", "Audit Log", "Lifecycle Demo"]
ROLE_PAGES = {
    "Customer": CUSTOMER_PAGES,
    "Support": SUPPORT_PAGES,
    "Warehouse": WAREHOUSE_PAGES,
    "Admin": ADMIN_PAGES,
}


def _err_box(err):
    st.error("Database / business rule: %s" % err)


# ---------------------------------------------------------------------------
# Login / sidebar
# ---------------------------------------------------------------------------
def sidebar():
    st.sidebar.title("📦 Returns & Refunds DBMS")
    st.sidebar.caption("Streamlit app over MySQL 8 (3NF, ACID)")
    if st.session_state.get("user") is None:
        st.sidebar.subheader("Login")
        username = st.sidebar.text_input("Username", key="login_user")
        password = st.sidebar.text_input("Password", type="password", key="login_pass")
        if st.sidebar.button("Sign in", use_container_width=True):
            try:
                st.session_state["user"] = authenticate(username.strip(), password)
                st.rerun()
            except AppError as err:
                st.sidebar.error(str(err))
        with st.sidebar.expander("Demo accounts (password123)"):
            st.markdown(
                "- `customer_user` - Customer\n"
                "- `support_agent` - Support\n"
                "- `warehouse_op` - Warehouse\n"
                "- `admin_user` - Admin"
            )
        return None
    user = st.session_state["user"]
    st.sidebar.success("Signed in as **%s** (%s)" % (user["username"], user["role"]))
    if st.sidebar.button("Sign out", use_container_width=True):
        st.session_state["user"] = None
        st.rerun()
    pages = ROLE_PAGES[user["role"]]
    choice = st.sidebar.radio("Navigate", pages, key="nav")
    try:
        inv = system_inventory()
        st.sidebar.caption(
            "DB: %d tables | %d triggers | %d procedure(s)"
            % (inv["tables_count"], inv["triggers_count"], inv["procedures_count"])
        )
    except AppError:
        pass
    return choice


# ---------------------------------------------------------------------------
# Customer portal
# ---------------------------------------------------------------------------
def page_customer(user):
    st.header("🛍️ Customer Portal")
    st.caption("Browse catalogue, place orders, track status and request item-level returns.")

    products = list_products()
    st.subheader("Product catalogue")
    st.dataframe(pd.DataFrame(products), use_container_width=True, hide_index=True)

    st.subheader("Place a new order")
    with st.form("place_order_form"):
        cols = st.columns(2)
        sel = cols[0].multiselect(
            "Products",
            options=[p["product_id"] for p in products],
            format_func=lambda pid: next(
                "%s - ₹%s (%d-day window)" % (p["name"], p["current_price"], p["return_window_days"])
                for p in products if p["product_id"] == pid
            ),
        )
        qty = cols[1].number_input("Quantity (each)", min_value=1, max_value=10, value=1)
        submitted = st.form_submit_button("Place order (status: Delivered)")
    if submitted:
        try:
            cid = user["customer_id"] or 1
            res = place_order(cid, [{"product_id": pid, "quantity": int(qty)} for pid in sel],
                              actor=user["username"])
            st.success("Order #%d placed: ₹%s (payment ref %s)"
                       % (res["order_id"], res["total_amount"], res["provider_reference"]))
        except AppError as err:
            _err_box(err)

    st.subheader("My orders & status tracker")
    cid = user["customer_id"] or 1
    orders = my_orders(cid)
    if not orders:
        st.info("No orders yet.")
        return
    st.dataframe(pd.DataFrame(orders), use_container_width=True, hide_index=True)
    order_ids = [o["order_id"] for o in orders]
    oid = st.selectbox("Select order for detail / return", order_ids)
    det = order_detail(oid)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Items**")
        st.dataframe(pd.DataFrame(det["items"]), use_container_width=True, hide_index=True)
    with c2:
        st.markdown("**Returns & refunds**")
        if det["returns"]:
            st.dataframe(pd.DataFrame(det["returns"]), use_container_width=True, hide_index=True)
        else:
            st.info("No return requests on this order.")

    st.markdown("**Request a return** (trigger blocks late / excess-quantity requests)")
    with st.form("return_form"):
        r1, r2 = st.columns(2)
        item_ids = r1.multiselect(
            "Order items to return",
            options=[i["order_item_id"] for i in det["items"]],
            format_func=lambda iid: next(
                "%s × %s @ ₹%s" % (i["product_name"], i["quantity"], i["unit_price_at_purchase"])
                for i in det["items"] if i["order_item_id"] == iid
            ),
        )
        rqty = r2.number_input("Return quantity (each)", min_value=1, max_value=10, value=1)
        reason = st.text_input("Reason", placeholder="e.g. Defective item")
        rsub = st.form_submit_button("Submit return request")
    if rsub:
        try:
            rid = request_return(oid, cid, reason,
                                 [{"order_item_id": iid, "quantity": int(rqty)} for iid in item_ids],
                                 actor=user["username"])
            st.success("Return request #%d submitted (status: Requested)" % rid)
        except AppError as err:
            _err_box(err)

    with st.expander("Try the late-return guard (Order 3: 45 days old, 7-day window)"):
        if st.button("Test blocked late return"):
            try:
                request_return(3, 3, "Changed mind",
                               [{"order_item_id": 3, "quantity": 1}], actor=user["username"])
                st.warning("Unexpected: late return was accepted")
            except AppError as err:
                st.error("Blocked by trigger trg_validate_return_window: %s" % err)


# ---------------------------------------------------------------------------
# Operations (support + warehouse)
# ---------------------------------------------------------------------------
def page_operations(user):
    st.header("🏭 Operations Dashboard")
    st.caption("Support: approve/reject · Warehouse: receive/inspect. Illegal jumps are blocked by the state-machine trigger.")
    queue = pending_returns()
    if not queue:
        st.info("No pending returns. Queue covers Requested / Approved / Received / Inspected.")
        return
    st.dataframe(pd.DataFrame(queue), use_container_width=True, hide_index=True)
    rid = st.selectbox("Select return", [q["return_id"] for q in queue])
    current = next(q["return_status"] for q in queue if q["return_id"] == rid)
    st.markdown("Current status: **%s**" % current)
    role = user["role"]

    c1, c2, c3 = st.columns(3)
    if role in ("Support", "Admin"):
        with c1:
            if st.button("✅ Approve", use_container_width=True):
                try:
                    set_return_status(rid, "Approved", actor=user["username"])
                    st.success("Return #%d approved" % rid)
                    st.rerun()
                except AppError as err:
                    _err_box(err)
        with c2:
            if st.button("❌ Reject", use_container_width=True):
                try:
                    set_return_status(rid, "Rejected", actor=user["username"])
                    st.success("Return #%d rejected (terminal)" % rid)
                    st.rerun()
                except AppError as err:
                    _err_box(err)
    if role in ("Warehouse", "Admin"):
        with c3:
            if st.button("📥 Mark received", use_container_width=True):
                try:
                    set_return_status(rid, "Received", actor=user["username"])
                    st.success("Return #%d marked received" % rid)
                    st.rerun()
                except AppError as err:
                    _err_box(err)

    if role in ("Warehouse", "Admin"):
        st.markdown("**Warehouse inspection** (moves Received → Inspected)")
        with st.form("inspect_form"):
            i1, i2 = st.columns(2)
            cond = i1.selectbox("Condition", ["GOOD", "DAMAGED", "DEFECTIVE"])
            notes = i2.text_input("Notes", placeholder="e.g. Verified fault, box included")
            isub = st.form_submit_button("Record inspection")
        if isub:
            try:
                inspect_return(rid, cond, notes, actor=user["username"])
                st.success("Return #%d inspected (%s)" % (rid, cond))
                st.rerun()
            except AppError as err:
                _err_box(err)


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------
def page_refunds(user):
    st.header("💸 Refund Processing")
    st.caption("Atomic refunds via stored procedure sp_process_refund (duplicate-safe, full rollback on error).")
    ready = [q for q in pending_returns() if q["return_status"] == "Inspected"]
    if not ready:
        st.info("No inspected returns awaiting refund.")
        return
    st.dataframe(pd.DataFrame(ready), use_container_width=True, hide_index=True)
    rid = st.selectbox("Select inspected return", [q["return_id"] for q in ready])
    if st.button("Process refund via sp_process_refund", type="primary"):
        try:
            order_id = next(q["order_id"] for q in ready if q["return_id"] == rid)
            fid = process_refund(order_id, rid, actor=user["username"])
            st.success("Refund #%d processed for return #%d (status: Refunded)" % (fid, rid))
            st.rerun()
        except AppError as err:
            _err_box(err)
    with st.expander("Concurrency guard"):
        st.caption("Two parallel refund attempts on the same return yield exactly one success "
                   "and one duplicate-refund error (verified by TC-09).")


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
def page_analytics():
    st.header("📊 Analytics Dashboard")
    rates = report_return_rates()
    monthly = report_monthly_refunds()
    reasons = report_top_reasons()

    total_refunded = sum(float(m["total_refund_amount"] or 0) for m in monthly)
    total_count = sum(int(m["total_refund_count"] or 0) for m in monthly)
    m1, m2, m3 = st.columns(3)
    m1.metric("Processed refunds", total_count)
    m2.metric("Total refunded", "₹%.2f" % total_refunded)
    worst = rates[0] if rates else None
    m3.metric("Highest return rate", "%s (%s%%)" % (worst["product_name"], worst["return_rate_percentage"])
              if worst else "—")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Return rate per product (%)**")
        if rates:
            st.bar_chart(pd.DataFrame(rates).set_index("product_name")["return_rate_percentage"])
        st.markdown("**Top return reasons**")
        st.dataframe(pd.DataFrame(reasons), use_container_width=True, hide_index=True)
    with c2:
        st.markdown("**Monthly refund totals**")
        if monthly:
            st.bar_chart(pd.DataFrame(monthly).set_index("month_year")["total_refund_amount"])
        else:
            st.info("No processed refunds yet.")

    st.markdown("**Order history with returns**")
    st.dataframe(pd.DataFrame(report_order_history()), use_container_width=True, hide_index=True)
    st.markdown("**Refund status by order**")
    st.dataframe(pd.DataFrame(report_refund_status()), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Audit log (admin)
# ---------------------------------------------------------------------------
def page_audit():
    st.header("🧾 Audit Log (Admin)")
    st.caption("Immutable trigger-written trail of every ReturnRequest / Refund status change.")
    st.dataframe(pd.DataFrame(audit_log(100)), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Guided lifecycle demo (7 states)
# ---------------------------------------------------------------------------
def page_lifecycle(user):
    st.header("🔁 Demo Lifecycle Stepper (7 states)")
    st.caption("Requested → Approved → Received → Inspected → Refunded, plus Rejected branch. "
               "Run as admin_user: Admin holds every operational right.")
    st.graphviz_chart(
        "digraph { rankdir=LR; Requested -> Approved -> Received -> Inspected -> Refunded; "
        "Requested -> Rejected; Approved -> Rejected; Received -> Rejected; Inspected -> Rejected; }"
    )
    if user["role"] != "Admin":
        st.warning("Sign in as admin_user to run the guided demo end-to-end.")
        return
    if st.button("▶ Run full lifecycle demo", type="primary"):
        try:
            with st.status("Running lifecycle demo…", expanded=True) as status:
                st.write("① Placing order (Wireless Headphones × 1)…")
                res = place_order(1, [{"product_id": 1, "quantity": 1}], actor=user["username"])
                oid = res["order_id"]
                st.write("Order #%d placed (Delivered), payment %s" % (oid, res["provider_reference"]))
                iid = order_detail(oid)["items"][0]["order_item_id"]
                st.write("② Requesting return…")
                rid = request_return(oid, 1, "Defective item (guided demo)",
                                     [{"order_item_id": iid, "quantity": 1}], actor=user["username"])
                st.write("Return #%d Requested" % rid)
                st.write("③ Approving…")
                set_return_status(rid, "Approved", actor=user["username"])
                st.write("④ Receiving…")
                set_return_status(rid, "Received", actor=user["username"])
                st.write("⑤ Inspecting (GOOD)…")
                inspect_return(rid, "GOOD", "Guided demo inspection", actor=user["username"])
                st.write("⑥ Refunding via sp_process_refund…")
                fid = process_refund(oid, rid, actor=user["username"])
                status.update(label="Demo complete: order #%d refunded (refund #%d)" % (oid, fid),
                              state="complete")
            st.success("End-to-end lifecycle verified: Delivered → Requested → Approved → "
                       "Received → Inspected → Refunded")
        except AppError as err:
            _err_box(err)


# ---------------------------------------------------------------------------
def main():
    if "user" not in st.session_state:
        st.session_state["user"] = None
    choice = sidebar()
    if st.session_state.get("user") is None:
        st.title("📦 E-Commerce Order, Return & Refund DBMS")
        st.markdown("Sign in from the sidebar to open your role workspace. "
                    "The app connects directly to MySQL 8 with parameterized SQL; "
                    "every status change is validated by database triggers and audited automatically.")
        return
    user = st.session_state["user"]
    if choice == "Customer Portal":
        page_customer(user)
    elif choice == "Operations":
        page_operations(user)
    elif choice == "Refunds":
        page_refunds(user)
    elif choice == "Analytics":
        page_analytics()
    elif choice == "Audit Log":
        page_audit()
    elif choice == "Lifecycle Demo":
        page_lifecycle(user)


if __name__ == "__main__":
    main()
