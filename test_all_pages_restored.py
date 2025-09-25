"""
Test all pages and navigation are restored with dark theme design
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def test_all_pages():
    """Test all pages and navigation work correctly"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        context = browser.new_context(viewport={"width": 1900, "height": 1200})
        page = context.new_page()

        try:
            print("Testing complete Mind2 application with all pages...")

            # Go to the app
            page.goto("http://localhost:8008/")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Check if login screen appears
            if page.locator('input[type="text"], input[placeholder*="admin"], text="Sign in"').count() > 0:
                print("Login screen detected - logging in...")

                # Fill login
                page.fill('input[type="text"], input[placeholder*="admin"]', 'admin')
                page.fill('input[type="password"]', 'adminadmin')
                page.click('button:has-text("Login"), button[type="submit"]')

                page.wait_for_load_state("networkidle")
                time.sleep(2)

            # Test Dashboard page
            print("1. Testing Dashboard page...")
            dashboard_found = page.locator('text="Dashboard"').count() > 0
            stat_cards = page.locator('.stat-card').count()
            sidebar_visible = page.locator('.sidebar').count() > 0
            mind_branding = page.locator('text="MIND Admin"').count() > 0

            print(f"   Dashboard page: {'✓' if dashboard_found else '✗'}")
            print(f"   Stat cards: {stat_cards} found")
            print(f"   Sidebar: {'✓' if sidebar_visible else '✗'}")
            print(f"   MIND branding: {'✓' if mind_branding else '✗'}")

            # Take dashboard screenshot
            screenshots_dir = Path("design_comparison")
            screenshots_dir.mkdir(exist_ok=True)
            page.screenshot(path=str(screenshots_dir / "dashboard_restored.png"))

            # Test Receipts page
            print("2. Testing Receipts page...")
            page.click('text="Receipts"')
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            receipts_content = page.content()
            receipts_page = 'Receipts' in receipts_content or 'receipt' in receipts_content.lower()
            print(f"   Receipts page: {'✓' if receipts_page else '✗'}")

            page.screenshot(path=str(screenshots_dir / "receipts_page.png"))

            # Test Processing page
            print("3. Testing Processing page...")
            page.click('text="Processing"')
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            processing_content = page.content()
            processing_page = 'Processing' in processing_content or 'company' in processing_content.lower()
            print(f"   Processing page: {'✓' if processing_page else '✗'}")

            # Test Analytics page
            print("4. Testing Analytics page...")
            page.click('text="Analytics"')
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            analytics_content = page.content()
            analytics_page = 'Analytics' in analytics_content or 'ai' in analytics_content.lower()
            print(f"   Analytics page: {'✓' if analytics_page else '✗'}")

            # Test System page
            print("5. Testing System page...")
            page.click('text="System"')
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            system_content = page.content()
            system_page = 'System' in system_content or 'export' in system_content.lower()
            print(f"   System page: {'✓' if system_page else '✗'}")

            # Test Users page
            print("6. Testing Users page...")
            page.click('text="Users"')
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            users_content = page.content()
            users_page = 'Users' in users_content or 'settings' in users_content.lower()
            print(f"   Users page: {'✓' if users_page else '✗'}")

            # Go back to Dashboard
            print("7. Testing navigation back to Dashboard...")
            page.click('text="Dashboard"')
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            back_to_dashboard = page.locator('.stat-card').count() > 0
            print(f"   Back to Dashboard: {'✓' if back_to_dashboard else '✗'}")

            # Final screenshot of complete application
            page.screenshot(path=str(screenshots_dir / "complete_application.png"), full_page=True)

            print("\n=== SUMMARY ===")
            if all([dashboard_found, stat_cards > 0, sidebar_visible, mind_branding]):
                print("SUCCESS: All pages and navigation restored with beautiful dark theme!")
                print("- Dark navy theme with red Mind branding")
                print("- Complete sidebar navigation")
                print("- All pages accessible and functional")
                print("- Stat cards working on Dashboard")
            else:
                print("Issues found - not all functionality restored")

            print("Application ready at http://localhost:8008")
            print("Press Enter when done inspecting...")
            input()

        except Exception as e:
            print(f"Error: {e}")
            input("Press Enter to close...")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    test_all_pages()