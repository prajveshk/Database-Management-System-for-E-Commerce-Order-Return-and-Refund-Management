-- Database Performance Indexes
-- DBMS: MySQL 8

USE ecommerce_db;

-- Customer lookups
CREATE INDEX idx_orders_customer_id ON Orders(customer_id);
CREATE INDEX idx_return_customer_id ON ReturnRequest(customer_id);

-- Order lookups
CREATE INDEX idx_orderitem_order_id ON OrderItem(order_id);
CREATE INDEX idx_payment_order_id ON Payment(order_id);
CREATE INDEX idx_return_order_id ON ReturnRequest(order_id);

-- Status filtering indexes
CREATE INDEX idx_return_status ON ReturnRequest(return_status);
CREATE INDEX idx_refund_status ON Refund(refund_status);

-- Product & Inventory performance indexes
CREATE INDEX idx_orderitem_product_id ON OrderItem(product_id);
CREATE INDEX idx_inventory_product_id ON Inventory(product_id);
