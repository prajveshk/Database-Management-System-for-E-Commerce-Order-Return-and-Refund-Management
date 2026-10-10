"""Capture Streamlit app screenshots via Playwright into docs/screenshots/st_*.png."""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8501"
OUT = "docs/screenshots"


def login(page, username):
    page.goto(BASE)
    page.get_by_role("textbox", name="Username").fill(username)
    page.get_by_role("textbox", name="Password").fill("password123")
    page.get_by_role("button", name="Sign in").click()
    page.get_by_text("Signed in as").wait_for(timeout=15000)
    page.wait_for_timeout(1500)


def go(page, name):
    page.get_by_text(name, exact=True).first.click()
    page.wait_for_timeout(2000)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    login(page, "customer_user")
    page.screenshot(path=f"{OUT}/st_customer_portal.png")
    print("st_customer_portal.png")

    go(page, "Analytics")
    page.screenshot(path=f"{OUT}/st_analytics_customer.png")
    print("st_analytics_customer.png")

    login(page, "admin_user")
    go(page, "Operations")
    page.screenshot(path=f"{OUT}/st_ops_dashboard.png")
    print("st_ops_dashboard.png")

    go(page, "Analytics")
    page.screenshot(path=f"{OUT}/st_analytics.png")
    print("st_analytics.png")

    go(page, "Audit Log")
    page.screenshot(path=f"{OUT}/st_audit_log.png")
    print("st_audit_log.png")

    go(page, "Lifecycle Demo")
    page.screenshot(path=f"{OUT}/st_lifecycle.png")
    print("st_lifecycle.png")

    browser.close()
print("done")
