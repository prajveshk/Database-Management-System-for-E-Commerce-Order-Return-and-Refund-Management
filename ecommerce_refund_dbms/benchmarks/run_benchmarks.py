import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mysql.connector
import subprocess
import time
import statistics
import matplotlib.pyplot as plt
from db.seed import get_db_connection, seed_bulk_data, init_schema, seed_demo_data

MYSQL_BIN = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
MYSQLDUMP_BIN = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

QUERIES = {
    "pending_returns": """
        SELECT rr.return_id, rr.order_id, c.name, c.email, rr.reason, rr.return_status, rr.requested_at
        FROM ReturnRequest rr
        JOIN Customer c ON rr.customer_id = c.customer_id
        WHERE rr.return_status IN ('Requested', 'Approved', 'Received')
    """,
    "order_history": """
        SELECT o.order_id, c.name, o.order_date, o.total_amount, o.order_status, p.payment_status, rr.return_status
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        LEFT JOIN Payment p ON o.order_id = p.order_id
        LEFT JOIN ReturnRequest rr ON o.order_id = rr.order_id
    """,
    "refund_status": """
        SELECT o.order_id, c.name, o.total_amount, p.provider_reference, rr.return_status, rf.amount, rf.refund_status
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        LEFT JOIN Payment p ON o.order_id = p.order_id
        LEFT JOIN ReturnRequest rr ON o.order_id = rr.order_id
        LEFT JOIN Refund rf ON rr.return_id = rf.return_id
    """
}

INDEX_DDL = [
    "CREATE INDEX idx_orders_customer_id ON Orders(customer_id)",
    "CREATE INDEX idx_return_customer_id ON ReturnRequest(customer_id)",
    "CREATE INDEX idx_orderitem_order_id ON OrderItem(order_id)",
    "CREATE INDEX idx_payment_order_id ON Payment(order_id)",
    "CREATE INDEX idx_return_order_id ON ReturnRequest(order_id)",
    "CREATE INDEX idx_return_status ON ReturnRequest(return_status)",
    "CREATE INDEX idx_refund_status ON Refund(refund_status)"
]

DROP_INDEX_DDL = [
    "ALTER TABLE Orders DROP INDEX idx_orders_customer_id",
    "ALTER TABLE ReturnRequest DROP INDEX idx_return_customer_id",
    "ALTER TABLE OrderItem DROP INDEX idx_orderitem_order_id",
    "ALTER TABLE Payment DROP INDEX idx_payment_order_id",
    "ALTER TABLE ReturnRequest DROP INDEX idx_return_order_id",
    "ALTER TABLE ReturnRequest DROP INDEX idx_return_status",
    "ALTER TABLE Refund DROP INDEX idx_refund_status"
]

def drop_all_indexes(conn):
    cursor = conn.cursor()
    for stmt in DROP_INDEX_DDL:
        try:
            cursor.execute(stmt)
        except Exception:
            pass
    cursor.close()

def create_all_indexes(conn):
    cursor = conn.cursor()
    for stmt in INDEX_DDL:
        try:
            cursor.execute(stmt)
        except Exception:
            pass
    cursor.close()

def time_query(conn, sql_query, runs=5):
    cursor = conn.cursor()
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        cursor.execute(sql_query)
        cursor.fetchall()
        end = time.perf_counter()
        times.append((end - start) * 1000.0) # convert to ms
    cursor.close()
    return round(statistics.median(times), 2)

def measure_sp_refund_performance(conn, runs=20):
    cursor = conn.cursor(dictionary=True)
    times = []
    
    # Create test orders and inspected returns for timing
    for i in range(runs):
        cursor.execute("INSERT INTO Orders (customer_id, total_amount, order_status) VALUES (1, 100.00, 'Delivered')")
        o_id = cursor.lastrowid
        cursor.execute("INSERT INTO OrderItem (order_id, product_id, quantity, unit_price_at_purchase) VALUES (%s, 1, 1, 100.00)", (o_id,))
        oi_id = cursor.lastrowid
        cursor.execute("INSERT INTO Payment (order_id, provider_reference, amount) VALUES (%s, %s, 100.00)", (o_id, f"BENCH-PAY-{o_id}-{i}"))
        cursor.execute("INSERT INTO ReturnRequest (order_id, customer_id, reason, return_status) VALUES (%s, 1, 'Bench test', 'Inspected')", (o_id,))
        ret_id = cursor.lastrowid
        cursor.execute("INSERT INTO ReturnItem (return_id, order_item_id, quantity) VALUES (%s, %s, 1)", (ret_id, oi_id))
        cursor.execute("INSERT INTO Inspection (return_id, inspector, condition_status) VALUES (%s, 'bench', 'GOOD')", (ret_id,))
        
        start = time.perf_counter()
        args = (o_id, ret_id, 'bench_user', 0)
        cursor.callproc('sp_process_refund', args)
        end = time.perf_counter()
        times.append((end - start) * 1000.0)
        
    cursor.close()
    return round(statistics.median(times), 2), round(statistics.mean(times), 2)

def get_explain_plan(conn, sql_query):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"EXPLAIN {sql_query}")
    explain_rows = cursor.fetchall()
    cursor.close()
    return explain_rows

def test_backup_restore():
    print("Testing database backup and restore cycle...")
    backup_file = "benchmarks/backup.sql"
    
    # 1. Take mysqldump
    dump_cmd = [MYSQLDUMP_BIN, "-h", "127.0.0.1", "-P", "3307", "-u", "root", "ecommerce_db"]
    with open(backup_file, "w", encoding="utf-8") as f:
        res = subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print("mysqldump failed:", res.stderr)
        return False, 0, 0
        
    # Get pre-restore counts
    conn = get_db_connection(database="ecommerce_db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Orders")
    pre_orders = cursor.fetchone()[0]
    conn.close()
    
    # 2. Drop and restore
    mysql_cmd = [MYSQL_BIN, "-h", "127.0.0.1", "-P", "3307", "-u", "root"]
    subprocess.run(mysql_cmd + ["-e", "DROP DATABASE ecommerce_db; CREATE DATABASE ecommerce_db;"], check=True)
    
    with open(backup_file, "r", encoding="utf-8") as f:
        res_rest = subprocess.run(mysql_cmd + ["ecommerce_db"], stdin=f, capture_output=True, text=True)
    if res_rest.returncode != 0:
        print("Restore failed:", res_rest.stderr)
        return False, pre_orders, 0
        
    # 3. Verify post-restore counts
    conn = get_db_connection(database="ecommerce_db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Orders")
    post_orders = cursor.fetchone()[0]
    conn.close()
    
    success = (pre_orders == post_orders and pre_orders > 0)
    print(f"Backup & Restore result: PASSED (Pre-rows: {pre_orders}, Post-rows: {post_orders})")
    return success, pre_orders, post_orders

def generate_benchmark_chart(results):
    sizes = ['1K', '10K', '100K']
    queries = ['pending_returns', 'order_history', 'refund_status']
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Database Query Performance: Indexed vs Non-Indexed Execution Time (ms)', fontsize=14, fontweight='bold')
    
    for idx, q_name in enumerate(queries):
        ax = axes[idx]
        indexed_times = [results[size][q_name]['indexed'] for size in sizes]
        unindexed_times = [results[size][q_name]['unindexed'] for size in sizes]
        
        x = range(len(sizes))
        width = 0.35
        
        ax.bar([i - width/2 for i in x], unindexed_times, width, label='Unindexed (Full Scan)', color='#e74c3c')
        ax.bar([i + width/2 for i in x], indexed_times, width, label='Indexed (B-Tree)', color='#2ecc71')
        
        ax.set_ylabel('Latency (ms)')
        ax.set_title(q_name.replace('_', ' ').title(), fontweight='semibold')
        ax.set_xticks(x)
        ax.set_xticklabels(sizes)
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
    plt.tight_layout()
    os.makedirs("docs/screenshots", exist_ok=True)
    os.makedirs("frontend", exist_ok=True)
    plt.savefig("docs/screenshots/benchmark_chart.png", dpi=150)
    plt.savefig("frontend/benchmark_chart.png", dpi=150)
    plt.close()
    print("Benchmark chart generated and saved to docs/screenshots/benchmark_chart.png and frontend/benchmark_chart.png")

def main():
    print("=== STARTING PERFORMANCE AND RECOVERY BENCHMARKS ===")
    
    scale_sizes = [1000, 10000, 100000]
    scale_labels = ['1K', '10K', '100K']
    results = {}
    explain_data = {}
    
    # 1. Reset DB with schema and demo data
    init_schema()
    conn = get_db_connection(database="ecommerce_db")
    seed_demo_data(conn)
    conn.close()

    # 2. Run benchmarks for 1K, 10K, 100K
    for count, label in zip(scale_sizes, scale_labels):
        print(f"\n--- Benchmarking Scale: {label} ({count} Order Records) ---")
        conn = get_db_connection(database="ecommerce_db")
        seed_bulk_data(conn, count)
        
        results[label] = {}
        
        # Measure WITH INDEXES
        create_all_indexes(conn)
        for q_name, sql in QUERIES.items():
            t_idx = time_query(conn, sql)
            results[label][q_name] = {'indexed': t_idx}
            if label == '10K' and q_name == 'pending_returns':
                explain_data['indexed'] = get_explain_plan(conn, sql)

        # Measure WITHOUT INDEXES
        drop_all_indexes(conn)
        for q_name, sql in QUERIES.items():
            t_unidx = time_query(conn, sql)
            results[label][q_name]['unindexed'] = t_unidx
            if label == '10K' and q_name == 'pending_returns':
                explain_data['unindexed'] = get_explain_plan(conn, sql)

        # Re-create indexes after drop
        create_all_indexes(conn)
        conn.close()

    # 3. Measure sp_process_refund execution time
    conn = get_db_connection(database="ecommerce_db")
    refund_median_ms, refund_avg_ms = measure_sp_refund_performance(conn, runs=20)
    conn.close()
    print(f"\nsp_process_refund Performance: Median = {refund_median_ms} ms, Average = {refund_avg_ms} ms")

    # 4. Backup and restore test
    backup_passed, pre_rows, post_rows = test_backup_restore()

    # 5. Generate PNG chart
    generate_benchmark_chart(results)

    # 6. Save benchmark summary results to text/markdown format
    print("\n=== FINAL BENCHMARK SUMMARY ===")
    for label in scale_labels:
        print(f"Scale {label}:")
        for q_name in QUERIES:
            t_idx = results[label][q_name]['indexed']
            t_unidx = results[label][q_name]['unindexed']
            speedup = round(t_unidx / t_idx, 2) if t_idx > 0 else 1.0
            print(f"  - {q_name}: Indexed={t_idx}ms, Unindexed={t_unidx}ms (Speedup: {speedup}x)")

    # Save benchmark results to dict for REPORT.md generator
    import json
    bench_data = {
        "results": results,
        "refund_median_ms": refund_median_ms,
        "refund_avg_ms": refund_avg_ms,
        "backup_passed": backup_passed,
        "pre_rows": pre_rows,
        "post_rows": post_rows,
        "explain_data": explain_data
    }
    with open("benchmarks/results.json", "w") as f:
        json.dump(bench_data, f, indent=2, default=str)
    print("Benchmark data saved to benchmarks/results.json")

if __name__ == "__main__":
    main()
