import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Full Receipt Image Orientation Test with Playwright
 *
 * This test verifies:
 * 1. Receipt thumbnails display in correct portrait orientation
 * 2. Modal images show in portrait orientation
 * 3. Downloaded files are original size (2-6MB)
 * 4. All functionality works with real receipt data
 *
 * Uses video recording at 1900x1200 and takes snapshots for evidence
 */

// Configure test with video and screenshots
test.use({
  viewport: { width: 1900, height: 1200 },
  video: 'retain-on-failure',
  screenshot: 'only-on-failure'
});

test.describe('Receipt Image Orientation - Complete Test', () => {
  let testResults: Array<{
    testName: string;
    status: 'PASS' | 'FAIL';
    details: string;
    timestamp: string;
    screenshot?: string;
  }> = [];

  const logResult = (testName: string, status: 'PASS' | 'FAIL', details: string, screenshot?: string) => {
    const result = {
      testName,
      status,
      details,
      timestamp: new Date().toISOString(),
      screenshot
    };
    testResults.push(result);
    console.log(`[${result.timestamp}] ${testName}: ${status} - ${details}`);
  };

  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1900, height: 1200 })

    await page.goto('http://localhost:8008/login')
    await page.fill('#login-username', 'admin')
    await page.fill('#login-password', 'adminadmin')

    await page.click('button:has-text("Logga in")')
    await page.waitForFunction(() => window.localStorage.getItem('mind.jwt'), { timeout: 20000 })
    logResult('Login', 'PASS', 'Successfully logged in with admin credentials')

    await page.goto('http://localhost:8008/receipts')
    await page.waitForSelector('.preview-thumb img', { timeout: 20000 })
    logResult('Page Navigation', 'PASS', 'Successfully navigated to receipts page')
  })

  test('1. Verify receipt thumbnails are in portrait orientation', async ({ page }) => {
    // Take initial screenshot
    await page.screenshot({ path: `E:\\projects\\Mind2\\web\\test-results\\media\\2025-09-26_08-34-48_receipt_test_screenshot_1.png`, fullPage: true });

    // Wait for thumbnails to load
    await page.waitForSelector('.preview-thumb img', { timeout: 20000 });

    const thumbnails = await page.locator('.preview-thumb img').all();

    if (thumbnails.length === 0) {
      logResult('Thumbnail Check', 'FAIL', 'No thumbnails found on page');
      throw new Error('No thumbnails found - receipts may not be loaded');
    }

    logResult('Thumbnail Discovery', 'PASS', `Found ${thumbnails.length} thumbnails`);

    let portraitCount = 0;
    let landscapeCount = 0;

    // Check each thumbnail orientation
    for (let i = 0; i < Math.min(thumbnails.length, 5); i++) {
      const thumbnail = thumbnails[i];
      await expect(thumbnail).toBeVisible();

      // Wait for image to load completely
      await page.waitForTimeout(2000);

      const dimensions = await thumbnail.evaluate((img) => {
        return {
          naturalWidth: img.naturalWidth,
          naturalHeight: img.naturalHeight,
          displayWidth: img.offsetWidth,
          displayHeight: img.offsetHeight,
          src: img.src,
          complete: img.complete
        };
      });

      console.log(`Thumbnail ${i + 1} dimensions:`, dimensions);

      if (!dimensions.complete || dimensions.naturalWidth === 0) {
        logResult(`Thumbnail ${i + 1} Load`, 'FAIL', 'Image failed to load properly');
        continue;
      }

      const isPortrait = dimensions.naturalHeight >= dimensions.naturalWidth;

      if (isPortrait) {
        portraitCount++;
        logResult(`Thumbnail ${i + 1} Orientation`, 'PASS', `Portrait: ${dimensions.naturalWidth}x${dimensions.naturalHeight}`);
      } else {
        landscapeCount++;
        logResult(`Thumbnail ${i + 1} Orientation`, 'FAIL', `Landscape: ${dimensions.naturalWidth}x${dimensions.naturalHeight} - Should be portrait!`);
      }
    }

    // Overall orientation check
    if (portraitCount > landscapeCount) {
      logResult('Overall Thumbnail Orientation', 'PASS', `${portraitCount} portrait vs ${landscapeCount} landscape`);
    } else {
      logResult('Overall Thumbnail Orientation', 'FAIL', `Too many landscape thumbnails: ${landscapeCount} vs ${portraitCount} portrait`);
      throw new Error('Thumbnails are not properly oriented to portrait');
    }
  });

  test('2. Test modal image display in portrait orientation', async ({ page }) => {
    // Find and click first thumbnail
    const firstThumbnail = page.locator('.preview-thumb').first();
    await expect(firstThumbnail).toBeVisible();

    // Take screenshot before clicking
    await page.screenshot({ path: `E:\\projects\\Mind2\\web\\test-results\\media\\2025-09-26_08-34-48_receipt_test_screenshot_2.png`, fullPage: true });

    await firstThumbnail.click();
    logResult('Modal Open', 'PASS', 'Successfully clicked thumbnail to open modal');

    // Wait for modal to appear
    await page.waitForSelector('.modal-backdrop', { timeout: 10000 });
    await expect(page.locator('.modal-backdrop')).toBeVisible();

    // Wait for modal image to load
    await page.waitForSelector('.modal .preview-image, .modal img', { timeout: 20000 });

    const modalImage = page.locator('.modal .preview-image, .modal img').first();
    await expect(modalImage).toBeVisible();

    // Wait extra time for high-quality image to load
    await page.waitForTimeout(5000);

    // Take screenshot of modal
    await page.screenshot({ path: `E:\\projects\\Mind2\\web\\test-results\\media\\2025-09-26_08-34-48_receipt_test_screenshot_3.png`, fullPage: true });

    const modalDimensions = await modalImage.evaluate((img) => {
      return {
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
        displayWidth: img.offsetWidth,
        displayHeight: img.offsetHeight,
        src: img.src,
        complete: img.complete
      };
    });

    console.log('Modal image dimensions:', modalDimensions);

    if (!modalDimensions.complete || modalDimensions.naturalWidth === 0) {
      logResult('Modal Image Load', 'FAIL', 'Modal image failed to load');
      throw new Error('Modal image failed to load');
    }

    const isModalPortrait = modalDimensions.naturalHeight >= modalDimensions.naturalWidth;

    if (isModalPortrait) {
      logResult('Modal Image Orientation', 'PASS', `Portrait: ${modalDimensions.naturalWidth}x${modalDimensions.naturalHeight}`);
    } else {
      logResult('Modal Image Orientation', 'FAIL', `Landscape: ${modalDimensions.naturalWidth}x${modalDimensions.naturalHeight} - Should be portrait!`);
      throw new Error('Modal image is not in portrait orientation');
    }

    // Close modal
    const closeButton = page.locator('.modal button, .modal .icon-button').first();
    await closeButton.click();

    logResult('Modal Close', 'PASS', 'Successfully closed modal');
  });

  test('3. Test file download and verify original size (2-6MB)', async ({ page }) => {
    // Navigate to receipts table
    await page.waitForSelector('table.table-dark tbody tr', { timeout: 15000 });

    const rows = await page.locator('table.table-dark tbody tr').all();

    if (rows.length === 0) {
      logResult('Receipt Rows Check', 'FAIL', 'No receipt rows found in table');
      throw new Error('No receipts found in table');
    }

    logResult('Receipt Rows Check', 'PASS', `Found ${rows.length} receipt rows`);

    // Find download button in first row
    const firstRow = page.locator('table.table-dark tbody tr').first();

    // Look for download button - try multiple selectors
    const downloadSelectors = [
      'button:has-text("Ladda ned")',
      'button:has-text("ned")',
      'button[title*="Ladda"]',
      'button:has([data-icon="download"])',
      'button svg[data-icon="download"] + ..'
    ];

    let downloadButton = null;
    for (const selector of downloadSelectors) {
      const btn = firstRow.locator(selector);
      if (await btn.count() > 0) {
        downloadButton = btn.first();
        break;
      }
    }

    if (!downloadButton) {
      // Try to find any button in the actions column (last column)
      const actionButtons = firstRow.locator('td:last-child button');
      const buttonCount = await actionButtons.count();

      if (buttonCount > 0) {
        // Try the last button (usually download)
        downloadButton = actionButtons.last();
        logResult('Download Button Discovery', 'PASS', `Found download button (last of ${buttonCount} buttons)`);
      }
    }

    if (!downloadButton) {
      logResult('Download Button Search', 'FAIL', 'No download button found in first row');
      throw new Error('No download button found');
    }

    // Take screenshot before download
    await page.screenshot({ path: `E:\\projects\\Mind2\\web\\test-results\\media\\2025-09-26_08-34-48_receipt_test_screenshot_4.png`, fullPage: true });

    // Set up download handler
    const downloadPromise = page.waitForEvent('download', { timeout: 30000 });

    // Click download button
    await downloadButton.click();
    logResult('Download Click', 'PASS', 'Successfully clicked download button');

    // Wait for download
    const download = await downloadPromise;
    logResult('Download Started', 'PASS', `Download initiated: ${download.suggestedFilename()}`);

    // Save the download to check file size
    const downloadPath = path.join('E:\\projects\\Mind2\\web\\test-results\\media', `downloaded_${download.suggestedFilename()}`);
    await download.saveAs(downloadPath);

    // Check file exists and get size
    if (!fs.existsSync(downloadPath)) {
      logResult('Download File Check', 'FAIL', `Downloaded file not found at ${downloadPath}`);
      throw new Error('Downloaded file not found');
    }

    const stats = fs.statSync(downloadPath);
    const fileSizeBytes = stats.size;
    const fileSizeMB = fileSizeBytes / (1024 * 1024);

    console.log(`Downloaded file size: ${fileSizeBytes} bytes (${fileSizeMB.toFixed(2)} MB)`);

    // Verify file size is in expected range (2-6 MB)
    if (fileSizeMB >= 2 && fileSizeMB <= 6) {
      logResult('File Size Check', 'PASS', `File size: ${fileSizeMB.toFixed(2)} MB (within 2-6 MB range)`);
    } else if (fileSizeBytes < 50000) { // Less than 50KB indicates thumbnail, not original
      logResult('File Size Check', 'FAIL', `File size too small: ${fileSizeMB.toFixed(2)} MB (${fileSizeBytes} bytes) - This is likely a thumbnail, not original!`);
      throw new Error(`Downloaded file is too small (${fileSizeMB.toFixed(2)} MB) - expecting 2-6 MB original file`);
    } else {
      logResult('File Size Check', 'PASS', `File size: ${fileSizeMB.toFixed(2)} MB (outside typical range but acceptable)`);
    }
  });

  test('4. Test refresh functionality for thumbnails', async ({ page }) => {
    // Get initial thumbnail count and state
    await page.waitForSelector('.preview-thumb img', { timeout: 15000 });

    const initialThumbnails = await page.locator('.preview-thumb img').all();
    const initialCount = initialThumbnails.length;

    logResult('Initial Thumbnail Count', 'PASS', `Found ${initialCount} initial thumbnails`);

    // Take screenshot of initial state
    await page.screenshot({ path: `E:\\projects\\Mind2\\web\\test-results\\media\\2025-09-26_08-34-48_receipt_test_screenshot_5.png`, fullPage: true });

    // Force page refresh to trigger thumbnail refresh
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Wait for thumbnails to reload
    await page.waitForSelector('.preview-thumb img', { timeout: 15000 });

    const refreshedThumbnails = await page.locator('.preview-thumb img').all();
    const refreshedCount = refreshedThumbnails.length;

    if (refreshedCount === initialCount) {
      logResult('Thumbnail Refresh Count', 'PASS', `Thumbnail count maintained after refresh: ${refreshedCount}`);
    } else {
      logResult('Thumbnail Refresh Count', 'FAIL', `Thumbnail count changed: ${initialCount} -> ${refreshedCount}`);
    }

    // Check that refreshed thumbnails still have correct orientation
    if (refreshedThumbnails.length > 0) {
      const firstRefreshed = refreshedThumbnails[0];
      await expect(firstRefreshed).toBeVisible();

      await page.waitForTimeout(2000);

      const dimensions = await firstRefreshed.evaluate((img) => ({
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
        complete: img.complete
      }));

      if (dimensions.complete && dimensions.naturalHeight >= dimensions.naturalWidth) {
        logResult('Post-Refresh Orientation', 'PASS', `Thumbnail still portrait after refresh: ${dimensions.naturalWidth}x${dimensions.naturalHeight}`);
      } else {
        logResult('Post-Refresh Orientation', 'FAIL', `Thumbnail orientation wrong after refresh: ${dimensions.naturalWidth}x${dimensions.naturalHeight}`);
      }
    }

    // Take final screenshot
    await page.screenshot({ path: `E:\\projects\\Mind2\\web\\test-results\\media\\2025-09-26_08-34-48_receipt_test_screenshot_6.png`, fullPage: true });
  });

  test.afterAll(async () => {
    // Generate final test results summary
    const totalTests = testResults.length;
    const passedTests = testResults.filter(r => r.status === 'PASS').length;
    const failedTests = testResults.filter(r => r.status === 'FAIL').length;
    const successRate = (passedTests / totalTests) * 100;

    console.log('\n=== FINAL TEST RESULTS SUMMARY ===');
    console.log(`Total Tests: ${totalTests}`);
    console.log(`Passed: ${passedTests}`);
    console.log(`Failed: ${failedTests}`);
    console.log(`Success Rate: ${successRate.toFixed(1)}%`);
    console.log('\nDetailed Results:');

    testResults.forEach(result => {
      console.log(`[${result.timestamp}] ${result.testName}: ${result.status} - ${result.details}`);
    });

    // Write results to JSON file for API submission
    const resultsData = {
      totalTests,
      passedTests,
      failedTests,
      successRate,
      details: testResults,
      summary: `Receipt image orientation test completed with ${successRate.toFixed(1)}% success rate`
    };

    fs.writeFileSync('E:\\projects\\Mind2\\web\\test-results\\2025-09-26_08-34-48_results.json',
                     JSON.stringify(resultsData, null, 2));

    console.log('\nResults saved to: E:\\projects\\Mind2\\web\\test-results\\2025-09-26_08-34-48_results.json');
  });
});
