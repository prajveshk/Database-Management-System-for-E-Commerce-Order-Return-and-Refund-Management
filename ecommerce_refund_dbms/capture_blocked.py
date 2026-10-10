"""Capture the Streamlit late-return guard evidence (st_blocked_return.png)."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto("http://127.0.0.1:8501")
    page.get_by_role("textbox", name="Username").fill("customer_user")
    page.get_by_role("textbox", name="Password").fill("password123")
    page.get_by_role("button", name="Sign in").click()
    page.get_by_text("Signed in as").wait_for(timeout=15000)
    page.wait_for_timeout(1500)
    page.get_by_text("Try the late-return guard").click()
    page.wait_for_timeout(800)
    page.get_by_role("button", name="Test blocked late return").click()
    page.wait_for_timeout(1500)
    page.screenshot(path="docs/screenshots/st_blocked_return.png")
    print("st_blocked_return.png")
    browser.close()
print("done")
