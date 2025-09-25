"""
Test React dashboard on Vite dev server
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_vite_dashboard():
    """Test dashboard on Vite dev server"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        context = browser.new_context(viewport={"width": 1376, "height": 842})
        page = context.new_page()

        try:
            print("Testing React dashboard on Vite dev server...")
            page.goto("http://localhost:5174/")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # Check what we get
            page_content = page.content()
            print(f"Page contains SIMPLE DASHBOARD TEST: {'SIMPLE DASHBOARD TEST' in page_content}")
            print(f"Page contains stat-card: {'stat-card' in page_content}")

            # Check for stat cards
            stat_cards = page.locator('.stat-card')
            print(f"Number of stat cards found: {stat_cards.count()}")

            # Check for specific elements
            recent_activity = page.locator('h3:has-text("Recent Activity")')
            print(f"Recent Activity found: {recent_activity.count() > 0}")

            # Take screenshot
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)
            screenshot_path = screenshots_dir / "vite_dev_dashboard.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"Screenshot saved: {screenshot_path.absolute()}")

            if stat_cards.count() > 0:
                print("SUCCESS: Dashboard with stat cards is working on dev server!")
                # Compare with target image
                print("This should match the target design from old Mind project!")
            else:
                print("Issue: Still no stat cards found even on dev server")

            print("Browser is open - you can see the dashboard!")
            print("Press Enter when done inspecting...")
            input()

        except Exception as e:
            print(f"Error: {e}")
            input("Press Enter to close...")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    test_vite_dashboard()