-- Database Business Rules & Integrity Triggers
-- DBMS: MySQL 8

USE ecommerce_db;

DELIMITER //

-- ============================================================================
-- TRIGGER 1: Validation Trigger - BEFORE INSERT on ReturnRequest
-- Business Rule: Blocks return requests submitted outside the product return window.
-- ============================================================================
DROP TRIGGER IF EXISTS trg_validate_return_window //
CREATE TRIGGER trg_validate_return_window
BEFORE INSERT ON ReturnRequest
FOR EACH ROW
BEGIN
    DECLARE v_order_date TIMESTAMP;
    DECLARE v_max_window INT;
    DECLARE v_days_elapsed INT;

    -- Retrieve order date
    SELECT order_date INTO v_order_date
    FROM Orders
    WHERE order_id = NEW.order_id;

    -- Calculate minimum return window allowed among items in this order
    SELECT MIN(p.return_window_days) INTO v_max_window
    FROM OrderItem oi
    JOIN Product p ON oi.product_id = p.product_id
    WHERE oi.order_id = NEW.order_id;

    IF v_order_date IS NOT NULL AND v_max_window IS NOT NULL THEN
        SET v_days_elapsed = TIMESTAMPDIFF(DAY, v_order_date, NOW());
        IF v_days_elapsed > v_max_window THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Return window expired: Order date exceeds allowed product return window';
        END IF;
    END IF;
END //

-- ============================================================================
-- TRIGGER 2: Validation Trigger - BEFORE INSERT on ReturnItem
-- Business Rule: Prevents returning quantity > purchased quantity - already returned quantity.
-- ============================================================================
DROP TRIGGER IF EXISTS trg_validate_return_quantity //
CREATE TRIGGER trg_validate_return_quantity
BEFORE INSERT ON ReturnItem
FOR EACH ROW
BEGIN
    DECLARE v_purchased_qty INT DEFAULT 0;
    DECLARE v_already_returned_qty INT DEFAULT 0;
    DECLARE v_remaining_qty INT DEFAULT 0;

    -- Get total quantity purchased in the order item
    SELECT quantity INTO v_purchased_qty
    FROM OrderItem
    WHERE order_item_id = NEW.order_item_id;

    -- Get sum of previously returned quantities for this order item
    SELECT COALESCE(SUM(ri.quantity), 0) INTO v_already_returned_qty
    FROM ReturnItem ri
    JOIN ReturnRequest rr ON ri.return_id = rr.return_id
    WHERE ri.order_item_id = NEW.order_item_id
      AND rr.return_status NOT IN ('Rejected');

    SET v_remaining_qty = v_purchased_qty - v_already_returned_qty;

    IF NEW.quantity > v_remaining_qty THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Excess return quantity: Return quantity exceeds purchased quantity minus already returned items';
    END IF;
END //

-- ============================================================================
-- TRIGGER 3: Invalid State Transition Trigger - BEFORE UPDATE on ReturnRequest
-- Business Rule: Enforces strict state lifecycle:
-- Requested -> Approved / Rejected
-- Approved -> Received
-- Received -> Inspected
-- Inspected -> Refunded / Rejected
-- ============================================================================
DROP TRIGGER IF EXISTS trg_check_return_state_transition //
CREATE TRIGGER trg_check_return_state_transition
BEFORE UPDATE ON ReturnRequest
FOR EACH ROW
BEGIN
    IF OLD.return_status <> NEW.return_status THEN
        IF OLD.return_status = 'Requested' AND NEW.return_status NOT IN ('Approved', 'Rejected') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid state transition: Requested state can only move to Approved or Rejected';
        ELSEIF OLD.return_status = 'Approved' AND NEW.return_status NOT IN ('Received', 'Rejected') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid state transition: Approved state can only move to Received or Rejected';
        ELSEIF OLD.return_status = 'Received' AND NEW.return_status NOT IN ('Inspected', 'Rejected') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid state transition: Received state can only move to Inspected or Rejected';
        ELSEIF OLD.return_status = 'Inspected' AND NEW.return_status NOT IN ('Refunded', 'Rejected') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid state transition: Inspected state can only move to Refunded or Rejected';
        ELSEIF OLD.return_status IN ('Rejected', 'Refunded') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid state transition: Terminal state (Refunded/Rejected) cannot be modified';
        END IF;
    END IF;
END //

-- ============================================================================
-- TRIGGER 4: Audit Log Trigger - AFTER UPDATE on ReturnRequest
-- Business Rule: Records every status change on ReturnRequest to AuditLog
-- ============================================================================
DROP TRIGGER IF EXISTS trg_audit_return_status //
CREATE TRIGGER trg_audit_return_status
AFTER UPDATE ON ReturnRequest
FOR EACH ROW
BEGIN
    IF OLD.return_status <> NEW.return_status THEN
        INSERT INTO AuditLog (entity_type, entity_id, old_status, new_status, actor, note, changed_at)
        VALUES (
            'ReturnRequest',
            NEW.return_id,
            OLD.return_status,
            NEW.return_status,
            COALESCE(@current_app_user, 'SYSTEM_TRIGGER'),
            CONCAT('Return status updated for order #', NEW.order_id),
            NOW()
        );
    END IF;
END //

-- ============================================================================
-- TRIGGER 5: Audit Log Trigger - AFTER UPDATE on Refund
-- Business Rule: Records every status change on Refund to AuditLog
-- ============================================================================
DROP TRIGGER IF EXISTS trg_audit_refund_status //
CREATE TRIGGER trg_audit_refund_status
AFTER UPDATE ON Refund
FOR EACH ROW
BEGIN
    IF OLD.refund_status <> NEW.refund_status THEN
        INSERT INTO AuditLog (entity_type, entity_id, old_status, new_status, actor, note, changed_at)
        VALUES (
            'Refund',
            NEW.refund_id,
            OLD.refund_status,
            NEW.refund_status,
            COALESCE(@current_app_user, 'SYSTEM_TRIGGER'),
            CONCAT('Refund status changed for return #', NEW.return_id),
            NOW()
        );
    END IF;
END //

DELIMITER ;
