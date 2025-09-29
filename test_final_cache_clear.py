"""
Final test with complete cache clearing
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_with_cache_clear():
    """Test with complete cache clearing"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        # Create completely new context with no cache
        context = browser.new_context(
            viewport={"width": 1376, "height": 842},
            # Disable all caching
            no_viewport=False,
            ignore_https_errors=True,
        )

        page = context.new_page()

        try:
            print("Clearing all caches and storage...")
            # Clear all storage
            page.evaluate("localStorage.clear(); sessionStorage.clear();")

            # Navigate with cache busting
            cache_buster = int(time.time())
            url = f"http://localhost:8008/?cb={cache_buster}"
            print(f"Navigating to: {url}")

            page.goto(url)
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # Check what we actually get
            page_content = page.content()
            print(f"Page contains SIMPLE DASHBOARD TEST: {'SIMPLE DASHBOARD TEST' in page_content}")
            print(f"Page contains stat-card: {'stat-card' in page_content}")
            print(f"Page contains Sign in: {'Sign in' in page_content}")

            # Check for stat cards
            stat_cards = page.locator('.stat-card')
            print(f"Number of stat cards found: {stat_cards.count()}")

            # Take screenshot
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)
            screenshot_path = screenshots_dir / "final_cache_cleared_test.png"
            page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"Screenshot saved: {screenshot_path.absolute()}")

            if stat_cards.count() > 0:
                print("SUCCESS: Stat cards are now visible!")
            else:
                print("STILL NOT WORKING: No stat cards found")

            print("Browser is open - you can inspect the page")
            print("Press Enter when done...")
            input()

        except Exception as e:
            print(f"Error: {e}")
            input("Press Enter to close...")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    test_with_cache_clear()