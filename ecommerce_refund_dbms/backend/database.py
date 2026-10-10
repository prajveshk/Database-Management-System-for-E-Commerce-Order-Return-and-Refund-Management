import mysql.connector
from mysql.connector import pooling
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3307)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'ecommerce_db'),
    'autocommit': True,
    'pool_name': 'ecommerce_pool',
    'pool_size': 10
}

pool = None

def get_db_pool():
    global pool
    if pool is None:
        pool = pooling.MySQLConnectionPool(**DB_CONFIG)
    return pool

def get_db_connection():
    return get_db_pool().get_connection()
