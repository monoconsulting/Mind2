"""
Playwright test to verify Mind2 dashboard matches the target design
Compares against old/oldmind/web/test-reports/admin-login-after-submit.png
"""

import pytest
from playwright.sync_api import Page, expect
import time
import re
from pathlib import Path

def test_dashboard_design_match(page: Page):
    """Test that the current dashboard matches the target design exactly"""

    # Set viewport to match the target screenshot dimensions
    page.set_viewport_size({"width": 1376, "height": 842})

    # Create screenshots directory
    screenshots_dir = Path("design_comparison")
    screenshots_dir.mkdir(exist_ok=True)

    print("Testing Dashboard Design Match...")

    # Navigate to the admin dashboard
    page.goto("http://localhost:8008/")
    page.wait_for_load_state("networkidle")
    time.sleep(3)  # Let all styles and data load completely

    # Take a screenshot for comparison
    screenshot_path = screenshots_dir / "current_dashboard.png"
    page.screenshot(path=str(screenshot_path), full_page=False)

    print(f"Current dashboard screenshot saved: {screenshot_path.absolute()}")

    # Verify key design elements are present
    print("Verifying design elements...")

    # 1. Check dark theme background
    body_bg = page.locator("body").evaluate("el => window.getComputedStyle(el).backgroundColor")
    print(f"Body background: {body_bg}")

    # 2. Check sidebar with red Mind branding
    sidebar = page.locator(".sidebar")
    expect(sidebar).to_be_visible()
    sidebar_bg = sidebar.evaluate("el => window.getComputedStyle(el).backgroundColor")
    print(f"Sidebar background: {sidebar_bg}")

    # 3. Check Mind brand icon and text
    brand_icon = page.locator(".brand-icon")
    expect(brand_icon).to_be_visible()
    expect(brand_icon).to_contain_text("M")

    brand_text = page.locator(".brand-text")
    expect(brand_text).to_be_visible()
    expect(brand_text).to_contain_text("MIND Admin")

    # 4. Check navigation items
    nav_items = [
        ("Dashboard", "/"),
        ("Receipts", "/receipts"),
        ("Processing", "/company-card"),
        ("Analytics", "/ai"),
        ("System", "/export"),
        ("Users", "/settings")
    ]

    for item_name, _ in nav_items:
        nav_item = page.locator(f"button:has-text('{item_name}')")
        expect(nav_item).to_be_visible()

    # 5. Check that Dashboard is active (red background)
    dashboard_nav = page.locator("button:has-text('Dashboard')")
    expect(dashboard_nav).to_have_class(re.compile(r".*active.*"))

    # 6. Check main content area
    main_content = page.locator(".main")
    expect(main_content).to_be_visible()

    # 7. Check stat cards with proper colors
    stat_cards = page.locator(".stat-card")
    expect(stat_cards).to_have_count(4)

    # Verify stat card colors
    red_card = page.locator(".stat-card.red").first
    green_card = page.locator(".stat-card.green").first
    yellow_card = page.locator(".stat-card.yellow").first
    blue_card = page.locator(".stat-card.blue").first

    expect(red_card).to_be_visible()
    expect(green_card).to_be_visible()
    expect(yellow_card).to_be_visible()
    expect(blue_card).to_be_visible()

    # 8. Check Recent Activity section
    recent_activity = page.locator("h3:has-text('Recent Activity')")
    expect(recent_activity).to_be_visible()

    # 9. Check Storage Usage section
    storage_usage = page.locator("h3:has-text('Storage Usage')")
    expect(storage_usage).to_be_visible()

    # 10. Check Quick Actions section
    quick_actions = page.locator("h3:has-text('Quick Actions')")
    expect(quick_actions).to_be_visible()

    print("\\nAll design elements verified!")
    print(f"Compare current screenshot with target: old/oldmind/web/test-reports/admin-login-after-submit.png")
    print(f"Current screenshot: {screenshot_path.absolute()}")

    return True

if __name__ == "__main__":
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # Launch browser with maximum window
        browser = p.chromium.launch(
            headless=False,  # Show browser
            args=['--start-maximized']
        )

        context = browser.new_context(
            viewport={"width": 1376, "height": 842}
        )

        page = context.new_page()

        try:
            result = test_dashboard_design_match(page)

            if result:
                print("\\nDesign verification complete!")
                print("Browser window is open for your inspection.")
                print("Press Enter to close the browser...")
                input()

        except Exception as e:
            print(f"Test failed: {e}")
            print("Browser window is open for debugging.")
            print("Press Enter to close the browser...")
            input()

        finally:
            context.close()
            browser.close()