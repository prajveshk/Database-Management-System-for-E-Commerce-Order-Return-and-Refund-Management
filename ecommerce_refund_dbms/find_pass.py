import subprocess
import sys

passwords = [
    'root', 'admin', 'password', '1234', '123456', '12345678', 'mysql',
    'P@ssword1', 'root123', 'prajvesh', 'Prajvesh', 'Prajvesh@123',
    'root@123', 'Root@123', 'MySQL80', 'mysql123', 'Pass123',
    '12345', 'admin123', 'Password123!', 'Root123!'
]

mysql_bin = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"

for p in passwords:
    try:
        res = subprocess.run([mysql_bin, "-u", "root", f"-p{p}", "-e", "SELECT VERSION();"],
                             capture_output=True, text=True, timeout=5)
        if "VERSION" in res.stdout:
            print(f"SUCCESS_PASSWORD:{p}")
            sys.exit(0)
        else:
            print(f"Failed: {p} -> {res.stderr.strip()[:60]}")
    except Exception as e:
        print(f"Err {p}: {e}")

print("NOT_FOUND")
