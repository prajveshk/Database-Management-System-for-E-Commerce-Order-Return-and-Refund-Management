-- Query Catalog for Operational and Analytical Views
-- DBMS: MySQL 8

USE ecommerce_db;

-- ============================================================================
-- Query (a): Order History with Returns via JOIN (Operational)
-- Details: Retrieves full order details, items, payment status, and return requests.
-- ============================================================================
SELECT 
    o.order_id,
    o.customer_id,
    c.name AS customer_name,
    o.order_date,
    o.total_amount,
    o.order_status,
    p.payment_status,
    p.provider_reference,
    rr.return_id,
    rr.return_status,
    rr.reason AS return_reason,
    rf.amount AS refunded_amount
FROM Orders o
JOIN Customer c ON o.customer_id = c.customer_id
LEFT JOIN Payment p ON o.order_id = p.order_id
LEFT JOIN ReturnRequest rr ON o.order_id = rr.order_id
LEFT JOIN Refund rf ON rr.return_id = rf.return_id
ORDER BY o.order_date DESC;


-- ============================================================================
-- Query (b): Pending Returns Awaiting Inspection (Operational)
-- Details: Finds all return requests currently in 'Approved' or 'Received' status.
-- ============================================================================
SELECT 
    rr.return_id,
    rr.order_id,
    c.name AS customer_name,
    c.email AS customer_email,
    rr.reason,
    rr.return_status,
    rr.requested_at,
    COUNT(ri.return_item_id) AS total_returned_items
FROM ReturnRequest rr
JOIN Customer c ON rr.customer_id = c.customer_id
JOIN ReturnItem ri ON rr.return_id = ri.return_id
WHERE rr.return_status IN ('Approved', 'Received')
GROUP BY rr.return_id, rr.order_id, c.name, c.email, rr.reason, rr.return_status, rr.requested_at
ORDER BY rr.requested_at ASC;


-- ============================================================================
-- Query (c): Refund Status by Order (Operational)
-- Details: Summarizes payment and refund amounts per order.
-- ============================================================================
SELECT 
    o.order_id,
    c.name AS customer_name,
    o.total_amount AS order_total,
    p.provider_reference,
    p.payment_status,
    rr.return_id,
    rr.return_status,
    COALESCE(rf.amount, 0.00) AS amount_refunded,
    rf.refund_status,
    rf.processed_at
FROM Orders o
JOIN Customer c ON o.customer_id = c.customer_id
LEFT JOIN Payment p ON o.order_id = p.order_id
LEFT JOIN ReturnRequest rr ON o.order_id = rr.order_id
LEFT JOIN Refund rf ON rr.return_id = rf.return_id
ORDER BY o.order_id DESC;


-- ============================================================================
-- Query (d): Return Rate per Product (Analytical)
-- Details: Calculates total items sold vs returned, percentage return rate per product.
-- ============================================================================
SELECT 
    p.product_id,
    p.name AS product_name,
    COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
    COALESCE(SUM(ri.quantity), 0) AS total_units_returned,
    ROUND(
        IF(COALESCE(SUM(oi.quantity), 0) = 0, 0.0,
            (COALESCE(SUM(ri.quantity), 0) / SUM(oi.quantity)) * 100.0
        ), 2
    ) AS return_rate_percentage
FROM Product p
LEFT JOIN OrderItem oi ON p.product_id = oi.product_id
LEFT JOIN ReturnItem ri ON oi.order_item_id = ri.order_item_id
GROUP BY p.product_id, p.name
ORDER BY return_rate_percentage DESC;


-- ============================================================================
-- Query (e): Monthly Refund Totals (Analytical)
-- Details: Aggregates total processed refund amounts and counts grouped by YYYY-MM.
-- ============================================================================
SELECT 
    DATE_FORMAT(rf.processed_at, '%Y-%m') AS month_year,
    COUNT(rf.refund_id) AS total_refund_count,
    SUM(rf.amount) AS total_refund_amount
FROM Refund rf
WHERE rf.refund_status = 'Processed'
GROUP BY DATE_FORMAT(rf.processed_at, '%Y-%m')
ORDER BY month_year DESC;


-- ============================================================================
-- Query (f): Top Return Reasons (Analytical)
-- Details: Ranks return reasons by frequency and total associated refund impact.
-- ============================================================================
SELECT 
    rr.reason AS return_reason,
    COUNT(rr.return_id) AS total_requests,
    COALESCE(SUM(rf.amount), 0.00) AS total_refunded_value
FROM ReturnRequest rr
LEFT JOIN Refund rf ON rr.return_id = rf.return_id
GROUP BY rr.reason
ORDER BY total_requests DESC;
