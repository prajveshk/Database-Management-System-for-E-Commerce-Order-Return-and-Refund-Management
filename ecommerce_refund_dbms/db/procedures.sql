-- E-Commerce Database Stored Procedures
-- DBMS: MySQL 8

USE ecommerce_db;

DELIMITER //

-- ============================================================================
-- PROCEDURE: sp_process_refund
-- Purpose: Executes atomic refund processing within a single ACID transaction.
-- Safeguards:
--   1. Validates return request is in 'Inspected' state.
--   2. Prevents duplicate refunds (FIX 02).
--   3. Calculates exact refundable amount from (unit_price_at_purchase * returned_qty).
--   4. Creates Refund record and transitions ReturnRequest state to 'Refunded'.
--   5. Restocks inventory to 'AVAILABLE' if inspection condition is 'GOOD'.
--   6. Records full audit trail entry.
--   7. Full rollback on any error via SQLEXCEPTION exit handler (FIX 03).
-- ============================================================================
DROP PROCEDURE IF EXISTS sp_process_refund //
CREATE PROCEDURE sp_process_refund(
    IN p_order_id INT,
    IN p_return_id INT,
    IN p_actor VARCHAR(100),
    OUT p_refund_id INT
)
proc_label: BEGIN
    DECLARE v_current_status VARCHAR(50);
    DECLARE v_payment_id INT;
    DECLARE v_refund_amount DECIMAL(10,2) DEFAULT 0.00;
    DECLARE v_condition VARCHAR(50);
    DECLARE v_existing_refund_count INT DEFAULT 0;

    -- Exit handler for full rollback on any failure (FIX 03)
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- Set session variable for trigger audit tracking
    SET @current_app_user = COALESCE(p_actor, 'sp_process_refund');

    START TRANSACTION;

    -- 1. Validate ReturnRequest existence and current status
    SELECT return_status INTO v_current_status
    FROM ReturnRequest
    WHERE return_id = p_return_id AND order_id = p_order_id
    FOR UPDATE;

    IF v_current_status IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Return request not found for the specified order.';
    END IF;

    -- FIX 02: Explicit duplicate refund prevention
    IF v_current_status = 'Refunded' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Duplicate refund error: Return request has already been refunded.';
    END IF;

    IF v_current_status <> 'Inspected' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Return request must be in Inspected state prior to refund processing.';
    END IF;

    -- Double-check Refund table for existing processed refund
    SELECT COUNT(*) INTO v_existing_refund_count
    FROM Refund
    WHERE return_id = p_return_id AND refund_status = 'Processed';

    IF v_existing_refund_count > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Duplicate refund error: A processed refund already exists for this return request.';
    END IF;

    -- 2. Calculate refundable amount from historical purchase price (3NF)
    SELECT COALESCE(SUM(ri.quantity * oi.unit_price_at_purchase), 0.00) INTO v_refund_amount
    FROM ReturnItem ri
    JOIN OrderItem oi ON ri.order_item_id = oi.order_item_id
    WHERE ri.return_id = p_return_id;

    IF v_refund_amount <= 0.00 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Calculated refund amount is zero or invalid.';
    END IF;

    -- 3. Retrieve payment reference
    SELECT payment_id INTO v_payment_id
    FROM Payment
    WHERE order_id = p_order_id
    LIMIT 1;

    IF v_payment_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Associated payment record not found for order.';
    END IF;

    -- 4. Insert Refund record
    INSERT INTO Refund (return_id, payment_id, amount, refund_status, processed_at)
    VALUES (p_return_id, v_payment_id, v_refund_amount, 'Processed', NOW());

    SET p_refund_id = LAST_INSERT_ID();

    -- 5. Update ReturnRequest status to 'Refunded'
    UPDATE ReturnRequest
    SET return_status = 'Refunded'
    WHERE return_id = p_return_id;

    -- 6. Check inspection condition and restock inventory if GOOD
    SELECT condition_status INTO v_condition
    FROM Inspection
    WHERE return_id = p_return_id
    LIMIT 1;

    IF v_condition = 'GOOD' THEN
        UPDATE Inventory inv
        JOIN OrderItem oi ON inv.product_id = oi.product_id
        JOIN ReturnItem ri ON oi.order_item_id = ri.order_item_id
        SET inv.status = 'AVAILABLE'
        WHERE ri.return_id = p_return_id
          AND inv.status IN ('SOLD', 'RESERVED', 'RETURNED');
    END IF;

    -- 7. Audit log record
    INSERT INTO AuditLog (entity_type, entity_id, old_status, new_status, actor, note, changed_at)
    VALUES (
        'Refund',
        p_refund_id,
        'Inspected',
        'Refunded',
        COALESCE(p_actor, 'sp_process_refund'),
        CONCAT('Successfully processed refund of $', v_refund_amount, ' for order #', p_order_id),
        NOW()
    );

    COMMIT;
END //

DELIMITER ;
