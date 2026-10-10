-- E-Commerce Database Management System Schema (3NF)
-- DBMS: MySQL 8 (InnoDB, ACID compliant)

CREATE DATABASE IF NOT EXISTS ecommerce_db;
USE ecommerce_db;

-- Drop tables in reverse order of dependencies for clean setup
DROP TABLE IF EXISTS AuditLog;
DROP TABLE IF EXISTS Refund;
DROP TABLE IF EXISTS Inspection;
DROP TABLE IF EXISTS ReturnItem;
DROP TABLE IF EXISTS ReturnRequest;
DROP TABLE IF EXISTS Payment;
DROP TABLE IF EXISTS OrderItem;
DROP TABLE IF EXISTS Orders;
DROP TABLE IF EXISTS Inventory;
DROP TABLE IF EXISTS Product;
DROP TABLE IF EXISTS AppUser;
DROP TABLE IF EXISTS Role;
DROP TABLE IF EXISTS Customer;

-- 1. Role Table
-- Defines system roles for RBAC (Customer, Support, Warehouse, Admin)
CREATE TABLE Role (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- 2. Customer Table
-- Stores customer profiles separate from authentication credentials
CREATE TABLE Customer (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 3. AppUser Table
-- Secure authentication credentials with hashed passwords and role assignment
CREATE TABLE AppUser (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT NOT NULL,
    customer_id INT NULL,
    FOREIGN KEY (role_id) REFERENCES Role(role_id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 4. Product Table (3NF: Master data only)
-- Contains current price and return window in days.
CREATE TABLE Product (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    current_price DECIMAL(10,2) NOT NULL CHECK (current_price >= 0),
    return_window_days INT NOT NULL DEFAULT 30 CHECK (return_window_days >= 0)
) ENGINE=InnoDB;

-- 5. Inventory Table
-- Tracks item stock status (AVAILABLE, RESERVED, SOLD, RETURNED, DAMAGED)
CREATE TABLE Inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    serial_or_sku VARCHAR(100) UNIQUE,
    status ENUM('AVAILABLE', 'RESERVED', 'SOLD', 'RETURNED', 'DAMAGED') NOT NULL DEFAULT 'AVAILABLE',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 6. Orders Table
-- Header record for customer purchases with status domain tracking
CREATE TABLE Orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0),
    order_status ENUM('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled') NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 7. OrderItem Table (3NF: No redundant product name or current price)
-- Preserves unit_price_at_purchase for historical financial integrity
CREATE TABLE OrderItem (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price_at_purchase DECIMAL(10,2) NOT NULL CHECK (unit_price_at_purchase >= 0),
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE RESTRICT,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 8. Payment Table
-- Payment gateway transactions with UNIQUE provider_reference (no raw credit card data stored)
CREATE TABLE Payment (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    provider_reference VARCHAR(100) NOT NULL UNIQUE,
    amount DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    payment_status ENUM('Pending', 'Completed', 'Failed', 'Refunded') NOT NULL DEFAULT 'Completed',
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 9. ReturnRequest Table
-- Formal return requests created by customers with strict status domain transition checks
CREATE TABLE ReturnRequest (
    return_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    customer_id INT NOT NULL,
    reason VARCHAR(120) NOT NULL,
    return_status ENUM('Requested','Approved','Received','Inspected','Rejected','Refunded') NOT NULL DEFAULT 'Requested',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    inspected_at TIMESTAMP NULL,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 10. ReturnItem Table
-- Supports partial returns per order item with positive quantity constraints
CREATE TABLE ReturnItem (
    return_item_id INT AUTO_INCREMENT PRIMARY KEY,
    return_id INT NOT NULL,
    order_item_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    FOREIGN KEY (return_id) REFERENCES ReturnRequest(return_id) ON DELETE RESTRICT,
    FOREIGN KEY (order_item_id) REFERENCES OrderItem(order_item_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 11. Inspection Table (1:1 with ReturnRequest via UNIQUE constraint)
-- Records warehouse inspection details, condition (GOOD, DAMAGED, DEFECTIVE), and inspector info
CREATE TABLE Inspection (
    inspection_id INT AUTO_INCREMENT PRIMARY KEY,
    return_id INT NOT NULL UNIQUE,
    inspector VARCHAR(100) NOT NULL,
    condition_status ENUM('GOOD', 'DAMAGED', 'DEFECTIVE') NOT NULL,
    notes VARCHAR(255),
    inspected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (return_id) REFERENCES ReturnRequest(return_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 12. Refund Table (1 Return : N Refunds supported)
-- Final financial credit record linked to payment gateway transaction
CREATE TABLE Refund (
    refund_id INT AUTO_INCREMENT PRIMARY KEY,
    return_id INT NOT NULL,
    payment_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    refund_status ENUM('Pending', 'Processed', 'Failed') NOT NULL DEFAULT 'Processed',
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (return_id) REFERENCES ReturnRequest(return_id) ON DELETE RESTRICT,
    FOREIGN KEY (payment_id) REFERENCES Payment(payment_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 13. AuditLog Table
-- Immutable system audit trail capturing state changes across critical lifecycle entities
CREATE TABLE AuditLog (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    actor VARCHAR(100) NOT NULL,
    note VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
