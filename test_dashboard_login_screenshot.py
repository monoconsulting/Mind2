"""
Playwright test to login and take dashboard screenshot for design comparison
Uses admin/adminadmin credentials as requested
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_dashboard_with_login():
    """Login to dashboard and take screenshot for comparison"""

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=False,  # Show browser window
            args=['--start-maximized']
        )

        context = browser.new_context(
            viewport={"width": 1376, "height": 842}
        )

        page = context.new_page()

        try:
            print("Navigating to admin dashboard...")
            page.goto("http://localhost:8008/")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            print("Filling login form with admin/adminadmin...")
            # Fill username
            page.fill('input[placeholder*="Username"], input[name="username"], input[type="text"]', "admin")

            # Fill password
            page.fill('input[placeholder*="Password"], input[name="password"], input[type="password"]', "adminadmin")

            # Click login button
            page.click('button:has-text("Login")')

            print("Waiting for dashboard to load...")
            page.wait_for_load_state("networkidle")
            time.sleep(3)  # Let dashboard fully load

            # Create screenshots directory
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)

            # Take screenshot of logged-in dashboard
            screenshot_path = screenshots_dir / "logged_in_dashboard.png"
            page.screenshot(path=str(screenshot_path), full_page=False)

            print(f"Dashboard screenshot saved: {screenshot_path.absolute()}")
            print("Compare with target: old/oldmind/web/test-reports/admin-login-after-submit.png")

            # Keep browser open for inspection
            print("Browser window is open for your inspection.")
            print("Press Enter when done...")
            input()

        except Exception as e:
            print(f"Error: {e}")
            print("Browser window is open for debugging.")
            print("Press Enter to close...")
            input()

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    test_dashboard_with_login()