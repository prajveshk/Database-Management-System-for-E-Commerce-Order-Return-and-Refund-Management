import mysql.connector
import subprocess
import bcrypt
import random
import sys
from datetime import datetime, timedelta
from faker import Faker

def get_db_connection(database="ecommerce_db"):
    config = {
        'host': '127.0.0.1',
        'port': 3307,
        'user': 'root',
        'password': '',
        'autocommit': True
    }
    if database:
        config['database'] = database
    return mysql.connector.connect(**config)

fake = Faker()
Faker.seed(42)
random.seed(42)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def init_schema(conn=None):
    mysql_bin = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
    base_cmd = [mysql_bin, "-h", "127.0.0.1", "-P", "3307", "-u", "root"]
    
    # 1. Create Database if not exists
    subprocess.run(base_cmd + ["-e", "CREATE DATABASE IF NOT EXISTS ecommerce_db;"], check=True)
    
    # 2. Run schema, triggers, procedures, indexes
    sql_files = ['db/schema.sql', 'db/triggers.sql', 'db/procedures.sql', 'db/indexes.sql']
    for sf in sql_files:
        with open(sf, 'r', encoding='utf-8') as f:
            content = f.read()
        res = subprocess.run(base_cmd + ["ecommerce_db"], input=content, text=True, capture_output=True)
        if res.returncode != 0:
            print(f"Error executing {sf}:\n{res.stderr}")
            raise RuntimeError(f"Failed to execute {sf}")
        else:
            print(f"Successfully executed {sf}")
    print("Schema, triggers, procedures, and indexes created successfully.")

def seed_demo_data(conn):
    cursor = conn.cursor()
    pwd_hash = hash_password('password123')

    # 1. Seed Roles
    roles = [('Customer',), ('Support',), ('Warehouse',), ('Admin',)]
    cursor.executemany("INSERT INTO Role (role_name) VALUES (%s)", roles)
    
    # Map roles
    cursor.execute("SELECT role_id, role_name FROM Role")
    role_map = {name: r_id for r_id, name in cursor.fetchall()}

    # 2. Seed Demo Customers
    customers = [
        ('Alice Smith', 'alice@example.com', '555-0101'),
        ('Bob Jones', 'bob@example.com', '555-0102'),
        ('Charlie Brown', 'charlie@example.com', '555-0103'),
    ]
    cursor.executemany("INSERT INTO Customer (name, email, phone) VALUES (%s, %s, %s)", customers)
    
    # 3. Seed AppUsers for demo
    users = [
        ('customer_user', pwd_hash, role_map['Customer'], 1),
        ('bob_customer', pwd_hash, role_map['Customer'], 2),
        ('charlie_customer', pwd_hash, role_map['Customer'], 3),
        ('support_agent', pwd_hash, role_map['Support'], None),
        ('warehouse_op', pwd_hash, role_map['Warehouse'], None),
        ('admin_user', pwd_hash, role_map['Admin'], None),
    ]
    cursor.executemany(
        "INSERT INTO AppUser (username, password_hash, role_id, customer_id) VALUES (%s, %s, %s, %s)",
        users
    )

    # 4. Seed Products
    products = [
        ('Wireless Noise-Canceling Headphones', 199.99, 30),
        ('Ergonomic Mechanical Keyboard', 129.50, 14),
        ('Ultra HD 4K Monitor 27-inch', 349.00, 30),
        ('Smart Fitness Watch Series 5', 149.99, 7),
        ('USB-C Multi-Port Docking Station', 79.99, 30)
    ]
    cursor.executemany(
        "INSERT INTO Product (name, current_price, return_window_days) VALUES (%s, %s, %s)",
        products
    )

    # 5. Seed Inventory items
    for p_id in range(1, 6):
        for k in range(10):
            sku = f"SKU-PROD{p_id:02d}-{k:03d}"
            cursor.execute(
                "INSERT INTO Inventory (product_id, serial_or_sku, status) VALUES (%s, %s, 'AVAILABLE')",
                (p_id, sku)
            )

    now = datetime.now()
    
    # Order 1: Alice - Recent order, eligible for return
    o1_date = now - timedelta(days=2)
    cursor.execute(
        "INSERT INTO Orders (customer_id, order_date, total_amount, order_status) VALUES (1, %s, 199.99, 'Delivered')",
        (o1_date,)
    )
    cursor.execute(
        "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase) VALUES (1, 1, 1, 199.99)"
    )
    cursor.execute(
        "INSERT INTO Payment (order_id, provider_reference, amount, payment_status) VALUES (1, 'PAY-DEMO-001', 199.99, 'Completed')"
    )

    # Order 2: Bob - Recent order
    o2_date = now - timedelta(days=5)
    cursor.execute(
        "INSERT INTO Orders (customer_id, order_date, total_amount, order_status) VALUES (2, %s, 259.00, 'Delivered')",
        (o2_date,)
    )
    cursor.execute(
        "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase) VALUES (2, 2, 2, 129.50)"
    )
    cursor.execute(
        "INSERT INTO Payment (order_id, provider_reference, amount, payment_status) VALUES (2, 'PAY-DEMO-002', 259.00, 'Completed')"
    )

    # Order 3: Charlie - OUTSIDE RETURN WINDOW (45 days old, return window is 7 days)
    o3_date = now - timedelta(days=45)
    cursor.execute(
        "INSERT INTO Orders (customer_id, order_date, total_amount, order_status) VALUES (3, %s, 149.99, 'Delivered')",
        (o3_date,)
    )
    cursor.execute(
        "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase) VALUES (3, 4, 1, 149.99)"
    )
    cursor.execute(
        "INSERT INTO Payment (order_id, provider_reference, amount, payment_status) VALUES (3, 'PAY-DEMO-003', 149.99, 'Completed')"
    )

    # Order 4: Alice - Inspected Return ready for refund
    o4_date = now - timedelta(days=3)
    cursor.execute(
        "INSERT INTO Orders (customer_id, order_date, total_amount, order_status) VALUES (1, %s, 349.00, 'Delivered')",
        (o4_date,)
    )
    cursor.execute(
        "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase) VALUES (4, 3, 1, 349.00)"
    )
    cursor.execute(
        "INSERT INTO Payment (order_id, provider_reference, amount, payment_status) VALUES (4, 'PAY-DEMO-004', 349.00, 'Completed')"
    )
    cursor.execute(
        "INSERT INTO ReturnRequest (order_id, customer_id, reason, return_status, requested_at, inspected_at) VALUES (4, 1, 'Defective display panel', 'Inspected', %s, %s)",
        (now - timedelta(days=2), now - timedelta(days=1))
    )
    ret4_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO ReturnItem (return_id, order_item_id, quantity) VALUES (%s, 4, 1)",
        (ret4_id,)
    )
    cursor.execute(
        "INSERT INTO Inspection (return_id, inspector, condition_status, notes, inspected_at) VALUES (%s, 'warehouse_op', 'GOOD', 'Verified display fault, original box included.', %s)",
        (ret4_id, now - timedelta(days=1))
    )

    # Order 5: Bob - Approved Return awaiting warehouse inspection
    o5_date = now - timedelta(days=4)
    cursor.execute(
        "INSERT INTO Orders (customer_id, order_date, total_amount, order_status) VALUES (2, %s, 79.99, 'Delivered')",
        (o5_date,)
    )
    cursor.execute(
        "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase) VALUES (5, 5, 1, 79.99)"
    )
    cursor.execute(
        "INSERT INTO Payment (order_id, provider_reference, amount, payment_status) VALUES (5, 'PAY-DEMO-005', 79.99, 'Completed')"
    )
    cursor.execute(
        "INSERT INTO ReturnRequest (order_id, customer_id, reason, return_status, requested_at) VALUES (5, 2, 'Wrong size/incompatible ports', 'Approved', %s)",
        (now - timedelta(days=2),)
    )
    ret5_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO ReturnItem (return_id, order_item_id, quantity) VALUES (%s, 5, 1)",
        (ret5_id,)
    )

    cursor.close()
    print("Demo dataset seeded successfully.")

def seed_bulk_data(conn, count=1000):
    print(f"Seeding bulk dataset with {count} orders...")
    cursor = conn.cursor()
    now = datetime.now()
    
    # Generate Products (up to 50 total)
    prod_ids = []
    cursor.execute("SELECT product_id FROM Product")
    existing_p = [r[0] for r in cursor.fetchall()]
    prod_ids.extend(existing_p)
    
    while len(prod_ids) < 50:
        p_name = fake.catch_phrase() + " " + fake.word().capitalize()
        p_price = round(random.uniform(10.0, 500.0), 2)
        p_window = random.choice([7, 14, 30, 60])
        cursor.execute(
            "INSERT INTO Product (name, current_price, return_window_days) VALUES (%s, %s, %s)",
            (p_name, p_price, p_window)
        )
        prod_ids.append(cursor.lastrowid)

    # Generate Customers
    cursor.execute("SELECT customer_id FROM Customer")
    existing_c = [r[0] for r in cursor.fetchall()]
    cust_ids = list(existing_c)
    
    num_cust = max(100, count // 10)
    for _ in range(num_cust - len(cust_ids)):
        c_name = fake.name()
        c_email = fake.unique.email()
        c_phone = fake.phone_number()[:20]
        cursor.execute(
            "INSERT INTO Customer (name, email, phone) VALUES (%s, %s, %s)",
            (c_name, c_email, c_phone)
        )
        cust_ids.append(cursor.lastrowid)

    # Prepare bulk insertions
    orders_data = []
    items_data = []
    payments_data = []
    returns_data = []
    return_items_data = []
    inspections_data = []
    refunds_data = []

    # Get max IDs
    cursor.execute("SELECT COALESCE(MAX(order_id), 0) FROM Orders")
    start_order_id = cursor.fetchone()[0] + 1

    cursor.execute("SELECT COALESCE(MAX(order_item_id), 0) FROM OrderItem")
    start_item_id = cursor.fetchone()[0] + 1

    cursor.execute("SELECT COALESCE(MAX(return_id), 0) FROM ReturnRequest")
    start_return_id = cursor.fetchone()[0] + 1

    curr_order_id = start_order_id
    curr_item_id = start_item_id
    curr_return_id = start_return_id

    reasons = [
        "Defective item", "Wrong size", "Item not as described",
        "Changed mind", "Arrived late", "Package damaged"
    ]

    for i in range(count):
        o_id = curr_order_id
        curr_order_id += 1
        
        c_id = random.choice(cust_ids)
        # Random date within last 60 days
        days_ago = random.uniform(0.1, 60.0)
        o_date = now - timedelta(days=days_ago)
        
        # 1-3 items per order
        num_items = random.randint(1, 3)
        order_total = 0.0
        
        for _ in range(num_items):
            item_id = curr_item_id
            curr_item_id += 1
            
            p_id = random.choice(prod_ids)
            qty = random.randint(1, 2)
            unit_price = round(random.uniform(15.0, 300.0), 2)
            order_total += (qty * unit_price)
            
            items_data.append((item_id, o_id, p_id, qty, unit_price))
            
        order_total = round(order_total, 2)
        orders_data.append((o_id, c_id, o_date, order_total, 'Delivered'))
        
        # Payment
        pay_ref = f"BULK-PAY-{o_id}-{random.randint(10000, 99999)}"
        payments_data.append((o_id, pay_ref, order_total, 'Completed'))
        
        # ~15% return rate - ensure within 2 days of order date to respect return window trigger
        if random.random() < 0.15 and days_ago <= 5.0:
            ret_id = curr_return_id
            curr_return_id += 1
            
            reason = random.choice(reasons)
            req_date = o_date + timedelta(hours=random.uniform(1.0, 12.0))
            
            # Decide status lifecycle state
            st = random.choice(['Requested', 'Approved', 'Received', 'Inspected', 'Refunded'])
            
            returns_data.append((ret_id, o_id, c_id, reason, st, req_date))
            
            # Return item for first item in order
            first_item = items_data[-num_items]
            return_items_data.append((ret_id, first_item[0], 1))
            
            if st in ['Inspected', 'Refunded']:
                cond = random.choice(['GOOD', 'DAMAGED', 'DEFECTIVE'])
                insp_date = req_date + timedelta(days=1)
                inspections_data.append((ret_id, 'bulk_inspector', cond, 'Bulk automated inspection', insp_date))
                
                if st == 'Refunded':
                    ref_amount = round(1 * first_item[4], 2)
                    # We link payment via order_id later or in query
                    refunds_data.append((ret_id, o_id, ref_amount, 'Processed', insp_date + timedelta(hours=2)))

    # Execute batch inserts
    cursor.executemany(
        "INSERT INTO Orders (order_id, customer_id, order_date, total_amount, order_status) VALUES (%s, %s, %s, %s, %s)",
        orders_data
    )
    cursor.executemany(
        "INSERT INTO OrderItem (order_item_id, order_id, product_id, quantity, unit_price_at_purchase) VALUES (%s, %s, %s, %s, %s)",
        items_data
    )
    cursor.executemany(
        "INSERT INTO Payment (order_id, provider_reference, amount, payment_status) VALUES (%s, %s, %s, %s)",
        payments_data
    )
    if returns_data:
        cursor.executemany(
            "INSERT INTO ReturnRequest (return_id, order_id, customer_id, reason, return_status, requested_at) VALUES (%s, %s, %s, %s, %s, %s)",
            returns_data
        )
        cursor.executemany(
            "INSERT INTO ReturnItem (return_id, order_item_id, quantity) VALUES (%s, %s, %s)",
            return_items_data
        )
    if inspections_data:
        cursor.executemany(
            "INSERT INTO Inspection (return_id, inspector, condition_status, notes, inspected_at) VALUES (%s, %s, %s, %s, %s)",
            inspections_data
        )
    if refunds_data:
        # Match refund to payment_id
        refund_rows = []
        for ret_id, o_id, amount, status, p_date in refunds_data:
            cursor.execute("SELECT payment_id FROM Payment WHERE order_id = %s LIMIT 1", (o_id,))
            pay_row = cursor.fetchone()
            if pay_row:
                refund_rows.append((ret_id, pay_row[0], amount, status, p_date))
        if refund_rows:
            cursor.executemany(
                "INSERT INTO Refund (return_id, payment_id, amount, refund_status, processed_at) VALUES (%s, %s, %s, %s, %s)",
                refund_rows
            )

    cursor.close()
    print(f"Bulk data seed of {count} orders completed.")

def main():
    target_count = 0
    if len(sys.argv) > 1:
        target_count = int(sys.argv[1])
        
    if target_count == 0:
        init_schema()
        conn = get_db_connection(database="ecommerce_db")
        seed_demo_data(conn)
        conn.close()
    else:
        conn = get_db_connection(database="ecommerce_db")
        seed_bulk_data(conn, target_count)
        conn.close()

if __name__ == '__main__':
    main()
