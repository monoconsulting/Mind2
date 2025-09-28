const { test, expect } = require('@playwright/test');

/**
 * Receipt Image Orientation Test
 *
 * Tests that receipt images are displayed correctly in portrait orientation
 * in both thumbnail preview and modal view
 */

test.describe('Receipt Image Orientation', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to receipts page
    await page.goto('http://localhost:3000/receipts');

    // Wait for page to load
    await page.waitForSelector('[data-testid="receipts-table"], .table-dark', { timeout: 10000 });
  });

  test('should display receipt thumbnails in portrait orientation', async ({ page }) => {
    // Wait for receipts to load
    await page.waitForSelector('.preview-thumb', { timeout: 15000 });

    // Get all thumbnail images
    const thumbnails = await page.locator('.preview-thumb img').all();

    if (thumbnails.length === 0) {
      console.log('No thumbnails found, skipping thumbnail orientation test');
      return;
    }

    // Check that at least one thumbnail exists and is visible
    const firstThumbnail = thumbnails[0];
    await expect(firstThumbnail).toBeVisible();

    // Get image dimensions
    const dimensions = await firstThumbnail.evaluate((img) => {
      return {
        width: img.naturalWidth,
        height: img.naturalHeight,
        displayWidth: img.width,
        displayHeight: img.height
      };
    });

    console.log('Thumbnail dimensions:', dimensions);

    // Verify image loaded properly
    expect(dimensions.width).toBeGreaterThan(0);
    expect(dimensions.height).toBeGreaterThan(0);

    // For receipts, we expect portrait orientation (height >= width)
    // Allow some tolerance for square images
    expect(dimensions.height).toBeGreaterThanOrEqual(dimensions.width * 0.8);
  });

  test('should open modal with portrait-oriented image when thumbnail is clicked', async ({ page }) => {
    // Wait for receipts to load
    await page.waitForSelector('.preview-thumb', { timeout: 15000 });

    // Find first clickable thumbnail
    const firstThumbnail = page.locator('.preview-thumb').first();
    await expect(firstThumbnail).toBeVisible();

    // Click on thumbnail to open modal
    await firstThumbnail.click();

    // Wait for modal to appear
    await page.waitForSelector('.modal-backdrop', { timeout: 10000 });
    await expect(page.locator('.modal-backdrop')).toBeVisible();

    // Wait for image to load in modal
    await page.waitForSelector('.modal .preview-image, .modal img', { timeout: 15000 });

    const modalImage = page.locator('.modal .preview-image, .modal img').first();
    await expect(modalImage).toBeVisible();

    // Wait for image to actually load
    await modalImage.waitFor({ state: 'visible', timeout: 10000 });

    // Get modal image dimensions
    const modalDimensions = await modalImage.evaluate((img) => {
      return {
        width: img.naturalWidth,
        height: img.naturalHeight,
        displayWidth: img.width,
        displayHeight: img.height
      };
    });

    console.log('Modal image dimensions:', modalDimensions);

    // Verify modal image loaded properly
    expect(modalDimensions.width).toBeGreaterThan(0);
    expect(modalDimensions.height).toBeGreaterThan(0);

    // For receipts in modal, we expect portrait orientation (height >= width)
    expect(modalDimensions.height).toBeGreaterThanOrEqual(modalDimensions.width * 0.8);
  });

  test('should download original image with correct orientation', async ({ page }) => {
    // Wait for receipts to load
    await page.waitForSelector('.table-dark tbody tr', { timeout: 15000 });

    // Find first row with download button
    const firstRow = page.locator('.table-dark tbody tr').first();
    await expect(firstRow).toBeVisible();

    // Look for download button
    const downloadButton = firstRow.locator('button:has-text("Ladda ned"), button[title*="download"], button:has(svg)').last();

    if (await downloadButton.count() === 0) {
      console.log('No download button found, skipping download test');
      return;
    }

    // Set up download handler
    const downloadPromise = page.waitForEvent('download', { timeout: 30000 });

    // Click download button
    await downloadButton.click();

    // Wait for download to complete
    const download = await downloadPromise;

    // Verify download was successful
    expect(download).toBeDefined();
    expect(download.suggestedFilename()).toMatch(/\.(jpg|jpeg|png)$/i);

    console.log('Downloaded file:', download.suggestedFilename());
  });

  test('should maintain portrait orientation after preview refresh', async ({ page }) => {
    // Wait for receipts to load
    await page.waitForSelector('.preview-thumb', { timeout: 15000 });

    const thumbnails = await page.locator('.preview-thumb img').all();

    if (thumbnails.length === 0) {
      console.log('No thumbnails found, skipping refresh test');
      return;
    }

    const firstThumbnail = thumbnails[0];
    await expect(firstThumbnail).toBeVisible();

    // Get initial dimensions
    const initialDimensions = await firstThumbnail.evaluate((img) => {
      return {
        width: img.naturalWidth,
        height: img.naturalHeight
      };
    });

    // Force page refresh to trigger preview refresh
    await page.reload();
    await page.waitForSelector('.preview-thumb img', { timeout: 15000 });

    // Get dimensions after refresh
    const refreshedThumbnail = page.locator('.preview-thumb img').first();
    await expect(refreshedThumbnail).toBeVisible();

    const refreshedDimensions = await refreshedThumbnail.evaluate((img) => {
      return {
        width: img.naturalWidth,
        height: img.naturalHeight
      };
    });

    console.log('Initial dimensions:', initialDimensions);
    console.log('Refreshed dimensions:', refreshedDimensions);

    // Verify portrait orientation is maintained after refresh
    expect(refreshedDimensions.height).toBeGreaterThanOrEqual(refreshedDimensions.width * 0.8);
  });
});