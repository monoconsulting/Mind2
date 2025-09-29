"""
Corrected Playwright test to login and take dashboard screenshot
Uses the correct input selectors: id="u" and id="p"
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

            print("Checking if already logged in...")
            # Check if we're on login page or already logged in
            if page.locator('input#u').count() > 0:
                print("Login form found, logging in with admin/adminadmin...")

                # Clear and fill username (it might have default value)
                page.fill('input#u', "admin")

                # Fill password
                page.fill('input#p', "adminadmin")

                # Click login button
                page.click('button[type="submit"]')

                print("Waiting for dashboard to load after login...")
                page.wait_for_load_state("networkidle")
                time.sleep(4)  # Let dashboard fully load
            else:
                print("Already logged in, dashboard should be visible")

            # Create screenshots directory
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)

            # Take screenshot of logged-in dashboard
            screenshot_path = screenshots_dir / "logged_in_dashboard_corrected.png"
            page.screenshot(path=str(screenshot_path), full_page=False)

            print(f"Dashboard screenshot saved: {screenshot_path.absolute()}")
            print("Compare with target: old/oldmind/web/test-reports/admin-login-after-submit.png")

            # Check what's currently visible
            if page.locator('.sidebar').count() > 0:
                print("SUCCESS: Sidebar found - dashboard is visible!")
            else:
                print("WARNING: Sidebar not found - might still be on login page")

            # Keep browser open for inspection
            print("\\nBrowser window is open for your inspection.")
            print("You can now see the current dashboard design.")
            print("Press Enter when done comparing...")
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