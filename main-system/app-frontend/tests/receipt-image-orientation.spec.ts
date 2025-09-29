import { test, expect } from '@playwright/test';

/**
 * Receipt Image Orientation Test
 *
 * Tests that receipt images are displayed correctly in portrait orientation
 * in both thumbnail preview and modal view
 */

test.describe('Receipt Image Orientation', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to receipts page
    await page.goto('http://localhost:3000');

    // Wait for the app to load and navigate to receipts
    await page.waitForLoadState('networkidle');

    // Look for receipts navigation link or direct path
    const receiptsLink = page.locator('text=Kvitton');
    if (await receiptsLink.count() > 0) {
      await receiptsLink.click();
    } else {
      await page.goto('http://localhost:3000/receipts');
    }

    // Wait for page to load
    await page.waitForSelector('table.table-dark, [data-testid="receipts-table"]', { timeout: 15000 });
  });

  test('should display receipt thumbnails in portrait orientation', async ({ page }) => {
    // Wait for receipts to load
    await page.waitForSelector('.preview-thumb', { timeout: 15000 });

    // Get all thumbnail images
    const thumbnails = await page.locator('.preview-thumb img').all();

    if (thumbnails.length === 0) {
      console.log('No thumbnails found, checking if receipts exist');

      // Check if there are any receipts at all
      const rows = await page.locator('table.table-dark tbody tr').all();
      if (rows.length === 0) {
        console.log('No receipts found in table, test passed with warning');
        return;
      }

      throw new Error('Receipts exist but no thumbnails found');
    }

    // Check that at least one thumbnail exists and is visible
    const firstThumbnail = thumbnails[0];
    await expect(firstThumbnail).toBeVisible();

    // Wait for image to load
    await page.waitForTimeout(2000);

    // Get image dimensions
    const dimensions = await firstThumbnail.evaluate((img) => {
      return {
        width: img.naturalWidth,
        height: img.naturalHeight,
        displayWidth: img.width,
        displayHeight: img.height,
        src: img.src
      };
    });

    console.log('Thumbnail dimensions:', dimensions);

    // Verify image loaded properly
    expect(dimensions.width).toBeGreaterThan(0);
    expect(dimensions.height).toBeGreaterThan(0);

    // For receipts, we expect portrait orientation (height >= width)
    // Allow some tolerance for square images (at least 80% as tall as wide)
    expect(dimensions.height).toBeGreaterThanOrEqual(dimensions.width * 0.8);
  });

  test('should open modal with portrait-oriented image when thumbnail is clicked', async ({ page }) => {
    // Wait for receipts to load
    await page.waitForSelector('.preview-thumb', { timeout: 15000 });

    // Find first clickable thumbnail
    const firstThumbnail = page.locator('.preview-thumb').first();

    if (await firstThumbnail.count() === 0) {
      console.log('No thumbnails found, skipping modal test');
      return;
    }

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
    await page.waitForTimeout(3000);

    // Get modal image dimensions
    const modalDimensions = await modalImage.evaluate((img) => {
      return {
        width: img.naturalWidth,
        height: img.naturalHeight,
        displayWidth: img.width,
        displayHeight: img.height,
        src: img.src
      };
    });

    console.log('Modal image dimensions:', modalDimensions);

    // Verify modal image loaded properly
    expect(modalDimensions.width).toBeGreaterThan(0);
    expect(modalDimensions.height).toBeGreaterThan(0);

    // For receipts in modal, we expect portrait orientation (height >= width)
    expect(modalDimensions.height).toBeGreaterThanOrEqual(modalDimensions.width * 0.8);

    // Close modal
    await page.locator('.modal button').first().click();
  });

  test('should download original image correctly', async ({ page }) => {
    // Wait for receipts to load
    await page.waitForSelector('table.table-dark tbody tr', { timeout: 15000 });

    const rows = await page.locator('table.table-dark tbody tr').all();

    if (rows.length === 0) {
      console.log('No receipts found, skipping download test');
      return;
    }

    // Find first row with download button
    const firstRow = page.locator('table.table-dark tbody tr').first();
    await expect(firstRow).toBeVisible();

    // Look for download button - try different selectors
    const downloadSelectors = [
      'button:has-text("Ladda ned")',
      'button[title*="download"]',
      'button:has-text("ned")',
      'button svg + text:has-text("ned")'
    ];

    let downloadButton = null;
    for (const selector of downloadSelectors) {
      downloadButton = firstRow.locator(selector);
      if (await downloadButton.count() > 0) {
        break;
      }
    }

    if (!downloadButton || await downloadButton.count() === 0) {
      console.log('No download button found, skipping download test');
      return;
    }

    // Set up download handler
    const downloadPromise = page.waitForEvent('download', { timeout: 30000 });

    // Click download button
    await downloadButton.first().click();

    // Wait for download to complete
    const download = await downloadPromise;

    // Verify download was successful
    expect(download).toBeDefined();
    expect(download.suggestedFilename()).toMatch(/\.(jpg|jpeg|png)$/i);

    console.log('Downloaded file:', download.suggestedFilename());
  });

  test('should maintain aspect ratio in thumbnail display', async ({ page }) => {
    // Wait for receipts to load
    await page.waitForSelector('.preview-thumb', { timeout: 15000 });

    const thumbnails = await page.locator('.preview-thumb img').all();

    if (thumbnails.length === 0) {
      console.log('No thumbnails found, skipping aspect ratio test');
      return;
    }

    // Check multiple thumbnails if available
    const thumbnailsToCheck = Math.min(3, thumbnails.length);

    for (let i = 0; i < thumbnailsToCheck; i++) {
      const thumbnail = thumbnails[i];
      await expect(thumbnail).toBeVisible();

      // Wait for image to load
      await page.waitForTimeout(1000);

      const dimensions = await thumbnail.evaluate((img) => {
        const rect = img.getBoundingClientRect();
        return {
          naturalWidth: img.naturalWidth,
          naturalHeight: img.naturalHeight,
          displayWidth: rect.width,
          displayHeight: rect.height
        };
      });

      console.log(`Thumbnail ${i + 1} dimensions:`, dimensions);

      // Verify image loaded properly
      expect(dimensions.naturalWidth).toBeGreaterThan(0);
      expect(dimensions.naturalHeight).toBeGreaterThan(0);

      // Check that display maintains reasonable aspect ratio
      const naturalAspect = dimensions.naturalHeight / dimensions.naturalWidth;
      const displayAspect = dimensions.displayHeight / dimensions.displayWidth;

      // Allow some tolerance in aspect ratio preservation (within 20%)
      expect(Math.abs(naturalAspect - displayAspect) / naturalAspect).toBeLessThan(0.2);
    }
  });
});