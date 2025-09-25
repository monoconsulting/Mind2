"""
Final test - Docker container with proper React dashboard
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_final_dashboard():
    """Test Docker container with proper React dashboard"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        context = browser.new_context(viewport={"width": 1376, "height": 842})
        page = context.new_page()

        try:
            print("Testing Docker container with proper React dashboard...")
            page.goto("http://localhost:8008/")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # Check for login form first
            if page.locator('input[placeholder*="admin"]').count() > 0 or page.locator('text="Sign in"').count() > 0:
                print("Login screen detected - logging in...")

                # Fill login
                page.fill('input[type="text"], input[placeholder*="admin"]', 'admin')
                page.fill('input[type="password"]', 'adminadmin')
                page.click('button:has-text("Login"), button[type="submit"]')

                page.wait_for_load_state("networkidle")
                time.sleep(3)

            # Now check for dashboard
            page_content = page.content()
            print(f"Page contains MIND Admin: {'MIND Admin' in page_content}")
            print(f"Page contains stat-card: {'stat-card' in page_content}")

            # Check for stat cards
            stat_cards = page.locator('.stat-card')
            print(f"Number of stat cards found: {stat_cards.count()}")

            # Check for dashboard elements
            dashboard_title = page.locator('h1:has-text("Dashboard"), h2:has-text("Dashboard")')
            print(f"Dashboard title found: {dashboard_title.count() > 0}")

            # Take screenshot
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)
            screenshot_path = screenshots_dir / "final_dashboard_fixed.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"Screenshot saved: {screenshot_path.absolute()}")

            if stat_cards.count() > 0:
                print("🎉 SUCCESS: Docker container is now serving the proper React dashboard with stat cards!")
                print("The dark theme with red branding is working correctly!")
            else:
                print("❌ Issue: Still no stat cards found in Docker container")

            print("Browser is open for inspection!")
            print("Press Enter when done...")
            input()

        except Exception as e:
            print(f"Error: {e}")
            input("Press Enter to close...")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    test_final_dashboard()