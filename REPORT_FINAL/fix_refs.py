import docx
from copy import deepcopy
OUT = r"C:\Users\Prajvesh\Documents\Database-Management-System-for-E-Commerce-Order-Return-and-Refund-Management\REPORT_FINAL\25WU0102114_Prajvesh_DBMS_PBL_Report.docx"
d = docx.Document(OUT)

# 1. Fix Objective 3 (drop FastAPI harness remnant)
for p in d.paragraphs:
    if p.text.startswith("Develop a role-based Streamlit application"):
        p.text = ("Develop a role-based Streamlit application with direct parameterized-SQL connectivity and session-state RBAC "
"for Customer, Support, Warehouse, and Admin, covering ordering, returns, inspection, refunds, analytics, and audit.")
        print("obj3 fixed")
        break

# 2. Show citation-bearing sentences to confirm numbering
for p in d.paragraphs:
    if p.text.startswith("E-commerce post-purchase"):
        import re
        print("ABSTRACT CITES:", re.findall(r"\[\d+\]", p.text))
    if "appropriate acknowledgement has been given" in p.text:
        import re
        print("UNDERTAKING CITES:", re.findall(r"\[\d+\][-\[]*\d*\]*", p.text), "| tail:", p.text[-120:])
    if p.text.startswith("The application is a role-based Streamlit multi-page"):
        import re
        print("CH3 CITES:", re.findall(r"\[\d+\]", p.text))
    if p.text.startswith("Key results: 10/10"):
        import re
        print("KEYRES CITES:", re.findall(r"\[\d+\]", p.text))

# 3. Re-add [6] and [7] entries after [5]
for p in d.paragraphs:
    if p.text.startswith("[5] Oracle"):
        e6 = deepcopy(p._element)
        e7 = deepcopy(p._element)
        p._element.addnext(e6)
        e6.addnext(e7)
        break
found = 0
for p in d.paragraphs:
    if p.text.startswith("[5] Oracle") and found == 0:
        found = 1
    elif found == 1:
        p.text = ("[6] Python Software Foundation, mysql-connector-python Developer Guide "
"(parameterized queries and transactions). Accessed: Oct. 8, 2026. [Online]. Available: https://dev.mysql.com/doc/connector-python/en/")
        found = 2
    elif found == 2:
        p.text = ("[7] Streamlit Inc., Streamlit Documentation \u2014 Build data apps in Python. "
"Accessed: Oct. 11, 2026. [Online]. Available: https://docs.streamlit.io/")
        found = 3
        break
print("entries added:", found == 3)
d.save(OUT)
