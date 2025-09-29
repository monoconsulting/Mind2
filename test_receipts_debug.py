"""
Debug test to check what's actually on the page and find the Receipts navigation
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_receipts_debug():
    """Debug test to see what's actually on the page"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        context = browser.new_context(viewport={"width": 1900, "height": 1200})
        page = context.new_page()

        try:
            print("DEBUG: Testing what's actually on the page...")

            # Go to the app
            page.goto("http://localhost:8008/")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            print("DEBUG: Initial page loaded")

            # Take screenshot of initial state
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)
            page.screenshot(path=str(screenshots_dir / "debug_initial_page.png"))
            print("DEBUG: Initial screenshot saved")

            # Check if login screen appears
            login_inputs = page.locator('input[type="text"], input[placeholder*="admin"]').count()
            print(f"DEBUG: Found {login_inputs} login inputs")

            if login_inputs > 0:
                print("DEBUG: Login screen detected - logging in...")

                # Fill login
                page.fill('input[type="text"], input[placeholder*="admin"]', 'admin')
                page.fill('input[type="password"]', 'adminadmin')
                page.click('button:has-text("Login"), button[type="submit"]')

                page.wait_for_load_state("networkidle")
                time.sleep(3)

                page.screenshot(path=str(screenshots_dir / "debug_after_login.png"))
                print("DEBUG: After login screenshot saved")

            # Check what navigation items are available
            nav_items = page.locator('nav a, .sidebar a, [role="navigation"] a').all()
            print(f"DEBUG: Found {len(nav_items)} navigation items:")
            for i, item in enumerate(nav_items):
                try:
                    text = item.text_content()
                    href = item.get_attribute('href')
                    print(f"  {i+1}. '{text}' -> {href}")
                except:
                    print(f"  {i+1}. [Could not get text/href]")

            # Look for any text containing "receipt" or "kvitto"
            receipt_elements = page.locator('text*="receipt", text*="Receipt", text*="kvitto", text*="Kvitto"').all()
            print(f"DEBUG: Found {len(receipt_elements)} elements with receipt/kvitto text:")
            for i, elem in enumerate(receipt_elements):
                try:
                    text = elem.text_content()
                    print(f"  {i+1}. '{text}'")
                except:
                    print(f"  {i+1}. [Could not get text]")

            # Check page content
            page_text = page.content()
            has_receipts = "receipt" in page_text.lower() or "kvitto" in page_text.lower()
            print(f"DEBUG: Page contains receipts/kvitto text: {has_receipts}")

            # Try to find sidebar or navigation
            sidebar = page.locator('.sidebar, nav, [role="navigation"]').count()
            print(f"DEBUG: Found {sidebar} sidebar/nav elements")

            # Try clicking any element that might be receipts
            possible_receipts = page.locator('[href*="receipt"], [href*="/receipts"], text="Receipts", text="Kvitton"').count()
            print(f"DEBUG: Found {possible_receipts} possible receipts links")

            if possible_receipts > 0:
                print("DEBUG: Attempting to click receipts link...")
                try:
                    page.click('[href*="receipt"], [href*="/receipts"], text="Receipts", text="Kvitton"', timeout=5000)
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)

                    page.screenshot(path=str(screenshots_dir / "debug_receipts_page.png"))
                    print("DEBUG: Receipts page screenshot saved")

                    # Check if receipts page loaded
                    receipts_content = page.content()
                    has_receipts_title = "kvitton" in receipts_content.lower()
                    has_table = page.locator('table').count() > 0
                    print(f"DEBUG: Receipts page has title: {has_receipts_title}")
                    print(f"DEBUG: Receipts page has table: {has_table}")

                except Exception as e:
                    print(f"DEBUG: Could not click receipts: {e}")

            print("DEBUG: Final page screenshot")
            page.screenshot(path=str(screenshots_dir / "debug_final_page.png"))

            print("\nDEBUG: Test complete. Check the screenshots in design_comparison/")
            print("Press Enter when done inspecting...")
            input()

        except Exception as e:
            print(f"DEBUG: Error during test: {e}")
            page.screenshot(path=str(screenshots_dir / "debug_error.png"))
            input("Press Enter to close...")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    test_receipts_debug()