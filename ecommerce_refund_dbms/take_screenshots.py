import time
import os
import subprocess
from playwright.sync_api import sync_playwright

def capture_all_screenshots():
    os.makedirs("docs/screenshots", exist_ok=True)
    
    # 1. Capture terminal output screenshot for test_run_output.png
    res = subprocess.run(["python", "-m", "pytest", "tests/test_suite.py", "-v"], capture_output=True, text=True)
    test_output = res.stdout
    print("pytest run output captured:\n", test_output)
    
    # Create test_run_output.png using Matplotlib text rendering for high quality terminal look
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('off')
    ax.set_facecolor('#1e1e1e')
    fig.patch.set_facecolor('#1e1e1e')
    ax.text(0.02, 0.95, f"Automated Pytest Execution Output:\n\n{test_output}", 
            fontsize=9, color='#00ff66', family='monospace', va='top')
    plt.savefig("docs/screenshots/test_run_output.png", bbox_inches='tight', dpi=150)
    plt.close()

    # 2. Capture Browser Screenshots via Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        
        # Navigate to web app
        page.goto("http://127.0.0.1:8000")
        page.wait_for_timeout(1000)

        # a) Demo Stepper & API Flow
        page.evaluate("showTab('demo-stepper')")
        page.wait_for_timeout(500)
        page.screenshot(path="docs/screenshots/api_flow.png")
        print("Captured api_flow.png")

        # b) Blocked Late Return Rejection
        # Click test blocked action button
        page.click("button:has-text('Test Blocked Late Return')")
        page.wait_for_timeout(500)
        page.screenshot(path="docs/screenshots/blocked_late_return.png")
        print("Captured blocked_late_return.png")

        # c) Customer Portal
        page.evaluate("showTab('customer-portal')")
        page.wait_for_timeout(500)
        page.screenshot(path="docs/screenshots/customer_portal.png")
        print("Captured customer_portal.png")

        # d) Ops Dashboard
        page.evaluate("showTab('ops-dashboard')")
        page.wait_for_timeout(500)
        page.screenshot(path="docs/screenshots/ops_dashboard.png")
        print("Captured ops_dashboard.png")

        # e) Analytics Dashboard
        page.evaluate("showTab('analytics-dashboard')")
        page.wait_for_timeout(1000)
        page.screenshot(path="docs/screenshots/analytics_dashboard.png")
        print("Captured analytics_dashboard.png")

        # f) Audit Log (Admin view)
        page.evaluate("showTab('audit-view')")
        page.wait_for_timeout(500)
        page.screenshot(path="docs/screenshots/audit_log.png")
        print("Captured audit_log.png")

        # g) Access Denied (HTTP 403 Forbidden Non-Admin view)
        page.click("button:has-text('Test Non-Admin 403 Access')")
        page.wait_for_timeout(500)
        page.screenshot(path="docs/screenshots/access_denied_403.png")
        print("Captured access_denied_403.png")

        browser.close()

    print("All 9 screenshots captured successfully!")

if __name__ == "__main__":
    capture_all_screenshots()
