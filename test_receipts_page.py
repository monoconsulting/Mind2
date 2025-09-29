"""
Test the Receipts page specifically to verify it's working
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_receipts_page():
    """Test that the Receipts page loads and displays correctly"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        context = browser.new_context(viewport={"width": 1900, "height": 1200})
        page = context.new_page()

        try:
            print("Testing Receipts page specifically...")

            # Go to the app
            page.goto("http://localhost:8008/")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Login if needed
            if page.locator('input[type="text"], input[placeholder*="admin"]').count() > 0:
                print("Logging in...")
                page.fill('input[type="text"], input[placeholder*="admin"]', 'admin')
                page.fill('input[type="password"]', 'adminadmin')
                page.click('button:has-text("Login"), button[type="submit"]')
                page.wait_for_load_state("networkidle")
                time.sleep(2)

            # Navigate to Receipts page
            print("Navigating to Receipts page...")
            page.click('text="Receipts"')
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # Check if the Receipts page loaded
            page_content = page.content()

            # Look for Receipts page indicators
            receipts_title = page.locator('h1:has-text("Kvitton")').count() > 0
            receipts_table = page.locator('table').count() > 0
            search_form = page.locator('input[placeholder*="Sök"]').count() > 0
            ftp_button = page.locator('text="Hämta från FTP"').count() > 0

            print(f"Receipts title found: {'✓' if receipts_title else '✗'}")
            print(f"Receipts table found: {'✓' if receipts_table else '✗'}")
            print(f"Search form found: {'✓' if search_form else '✗'}")
            print(f"FTP button found: {'✓' if ftp_button else '✗'}")

            # Check for any error messages
            error_indicators = page.locator('text="❌"').count()
            if error_indicators > 0:
                print(f"Found {error_indicators} error indicators on page")

            # Take screenshot
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)
            page.screenshot(path=str(screenshots_dir / "receipts_page_test.png"))
            print("Screenshot saved: receipts_page_test.png")

            # Test search functionality
            if search_form:
                print("Testing search functionality...")
                search_input = page.locator('input[placeholder*="Sök"]').first
                search_input.fill("test")
                page.click('button:has-text("Sök")')
                time.sleep(1)
                search_status = page.locator('text*="Söker efter"').count() > 0
                print(f"Search status message: {'✓' if search_status else '✗'}")

            print(f"\n=== RECEIPTS PAGE SUMMARY ===")
            if receipts_title and (receipts_table or search_form):
                print("SUCCESS: Receipts page is loading correctly!")
                print("- Page title and header visible")
                print("- Core functionality present")
                if error_indicators == 0:
                    print("- No error messages detected")
                else:
                    print(f"- {error_indicators} error messages found (may be expected if no data)")
            else:
                print("ISSUE: Receipts page not loading properly")
                print("Check the screenshot for details")

            print("Press Enter when done inspecting...")
            input()

        except Exception as e:
            print(f"Error during test: {e}")
            input("Press Enter to close...")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    test_receipts_page()