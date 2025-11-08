import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test('test', async ({ page }) => {
  test.setTimeout(120000);

  await page.goto('http://localhost:5169/login');
  await page.getByRole('textbox', { name: 'Användarnamn' }).fill('admin');
  await page.getByRole('textbox', { name: 'Lösenord' }).click();
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.waitForTimeout(2000);
  await page.getByRole('button', { name: 'Översikt' }).click();
  await page.getByRole('button', { name: 'Process' }).click();
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.getByRole('button', { name: 'Kortmatchning' }).click();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);


    }

    await page.waitForTimeout(2000);

    // Check if modal appeared 
    const modalVisible = await page.locator('[class*="modal"], [role="dialog"]').isVisible().catch(() => false);
    console.log(`Preview modal visible: ${modalVisible}`);

    await page.screenshot({ path: 'web/test-results/media/snapshots/fc-after-preview-click.png' });

    if (modalVisible) {
      console.log('✓ Preview modal opened successfully!');
      // Close modal
      const closeBtn = page.getByRole('button', { name: 'Stäng' }).first();
      if (await closeBtn.isVisible()) { 
        await closeBtn.click();
        await page.waitForTimeout(500);
      }
    } else {
      console.error('✗ Preview modal did NOT open');
    }
  } else {
    console.error('✗ No "Förhandsgranska" buttons found!');
  }

  console.log('\n=== Test 2: Checking Log Date Grouping ===');

  // Click "Visa logg" button
  const logButton = page.getByRole('button', { name: /visa logg/i }).first();
  if (await logButton.isVisible()) {
    await logButton.click();
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'web/test-results/media/snapshots/fc-log-opened.png' });

    // Get log structure
    const logData = await page.evaluate(() => {
      const modal = document.querySelector('[class*="modal"]') || document.body;
      const text = modal.textContent || '';

      // Find date sections
      const dateMatches = text.match(/\d{4}-\d{2}-\d{2}/g) || [];
      const wf3Matches = text.match(/WF3_FIRSTCARD_INVOICE/g) || [];
      const ai6Matches = text.match(/AI6|CreditCardInvoiceParsing/g) || [];

      return {
        dates: [...new Set(dateMatches)],
        wf3Count: wf3Matches.length,
        ai6Count: ai6Matches.length,
        fullText: text.substring(0, 500) // First 500 chars for debugging
      };
    });

    console.log('Log data:', JSON.stringify(logData, null, 2));
    console.log(`Found ${logData.dates.length} unique dates`);
    console.log(`Found ${logData.wf3Count} WF3 entries`);
    console.log(`Found ${logData.ai6Count} AI6 entries`);

    // Close log
    const closeLogBtn = page.getByRole('button', { name: 'Stäng', exact: true }).first();
    if (await closeLogBtn.isVisible()) {
      await closeLogBtn.click();
    }
  } else {
    console.error('✗ "Visa logg" button not found');
  }

  console.log('\n=== Test Complete ===');
});