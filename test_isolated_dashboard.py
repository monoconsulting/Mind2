"""
Test isolated Dashboard component to see if it renders stat cards
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_isolated_dashboard():
    """Test Dashboard component in isolation"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        context = browser.new_context(viewport={"width": 1376, "height": 842})
        page = context.new_page()

        try:
            print("Testing isolated Dashboard component...")
            page.goto("http://localhost:8008/")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # Check if stat cards are now visible
            stat_cards = page.locator('.stat-card')
            print(f"Number of stat cards found: {stat_cards.count()}")

            # Check for Recent Activity
            recent_activity = page.locator('h3:has-text("Recent Activity")')
            print(f"Recent Activity found: {recent_activity.count() > 0}")

            # Check for Storage Usage
            storage_usage = page.locator('h3:has-text("Storage Usage")')
            print(f"Storage Usage found: {storage_usage.count() > 0}")

            # Take screenshot
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)
            screenshot_path = screenshots_dir / "isolated_dashboard_test.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"Screenshot saved: {screenshot_path.absolute()}")

            if stat_cards.count() > 0:
                print("SUCCESS: Dashboard component is rendering with stat cards!")
            else:
                print("ISSUE: Still no stat cards found")

            print("Press Enter when done...")
            input()

        except Exception as e:
            print(f"Error: {e}")
            input("Press Enter to close...")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    test_isolated_dashboard()