"""
Debug test to check what's actually rendering in the dashboard
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def debug_dashboard():
    """Debug what's actually rendering"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        context = browser.new_context(viewport={"width": 1376, "height": 842})
        page = context.new_page()

        try:
            print("Navigating and logging in...")
            page.goto("http://localhost:8008/")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Login
            page.fill('input#u', "admin")
            page.fill('input#p', "adminadmin")
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # Debug what's actually on the page
            print("\n=== PAGE DEBUG INFO ===")

            # Check if we have React root
            react_root = page.locator('#root')
            print(f"React root exists: {react_root.count() > 0}")

            # Check current URL
            print(f"Current URL: {page.url}")

            # Check what's in the main content area
            main_content = page.locator('.main')
            if main_content.count() > 0:
                content_text = main_content.inner_text()
                print(f"Main content text: {content_text[:200]}...")

            # Check for stat cards
            stat_cards = page.locator('.stat-card')
            print(f"Number of stat cards found: {stat_cards.count()}")

            # Check for specific React components
            dashboard_title = page.locator('h1, h2, h3').filter(has_text="Dashboard")
            print(f"Dashboard title found: {dashboard_title.count() > 0}")

            # Check console errors
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            # Wait a bit more for any async loading
            time.sleep(2)

            if console_errors:
                print(f"\nConsole errors: {console_errors}")
            else:
                print("\nNo console errors found")

            # Check page source for React elements
            page_html = page.content()
            has_react_elements = "stat-card" in page_html
            print(f"React stat-card elements in HTML: {has_react_elements}")

            # Take screenshot
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)
            screenshot_path = screenshots_dir / "debug_dashboard.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"\nDebug screenshot saved: {screenshot_path.absolute()}")

            print("\nPress Enter to continue...")
            input()

        except Exception as e:
            print(f"Error during debug: {e}")
            input("Press Enter to close...")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    debug_dashboard()