import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Web Scraper for Gävle Föreningsregister
 *
 * This test scrapes all associations from https://fri.gavle.se/forening/
 * including pagination through all pages and extracts complete data.
 *
 * Output: JSON file with all associations data
 */

interface Association {
  name: string;
  url: string;
  pageNumber: number;
  extractedAt: string;
  type?: string;
  activity?: string;
  homepage?: string;
}

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test('scrape all associations from Gävle föreningsregister', async ({ page }) => {
  // Increase timeout for long-running scrape (10 minutes)
  test.setTimeout(600000);

  const allAssociations: Association[] = [];
  const baseUrl = 'https://fri.gavle.se/forening/';

  console.log('Starting scrape of Gävle Föreningsregister...');

  // Navigate to the associations register
  await page.goto(baseUrl);

  // Wait for page to load
  await page.waitForLoadState('networkidle');

  let currentPage = 1;
  let hasMorePages = true;

  while (hasMorePages) {
    console.log(`\nScraping page ${currentPage}...`);

    // Wait for content to be visible
    await page.waitForTimeout(1000);

    // Extract all association links from current page
    const associations = await page.evaluate((pageNum) => {
      const results: { name: string; url: string; pageNumber: number; extractedAt: string; type?: string; activity?: string; homepage?: string }[] = [];

      // Find the table with associations
      const table = document.querySelector('table');
      if (!table) return results;

      // Get all rows except the header
      const rows = Array.from(table.querySelectorAll('tbody tr'));

      rows.forEach((row) => {
        const cells = row.querySelectorAll('td');
        if (cells.length === 0) return;

        // First cell contains the association name link
        const nameCell = cells[0];
        const link = nameCell.querySelector('a');

        if (link) {
          const name = link.textContent?.trim() || '';
          const href = (link as HTMLAnchorElement).href;

          // Extract additional data from other columns
          const type = cells[1]?.textContent?.trim() || '';
          const activity = cells[2]?.textContent?.trim() || '';
          const homepage = cells[3]?.querySelector('a')?.textContent?.trim() || '';

          if (name) {
            results.push({
              name,
              url: href,
              pageNumber: pageNum,
              extractedAt: new Date().toISOString(),
              type: type !== '(Saknas)' && type !== '' ? type : undefined,
              activity: activity !== '(Saknas)' && activity !== '' ? activity : undefined,
              homepage: homepage !== '' ? homepage : undefined
            });
          }
        }
      });

      return results;
    }, currentPage);

    console.log(`  Found ${associations.length} associations on page ${currentPage}`);
    allAssociations.push(...associations);

    // Try to find the "Next" button - based on error-context, it has text "Next"
    const nextButton = page.getByRole('link', { name: 'Next' });
    const isNextVisible = await nextButton.isVisible().catch(() => false);

    if (isNextVisible) {
      console.log(`  Navigating to page ${currentPage + 1}...`);
      await nextButton.click();
      await page.waitForLoadState('networkidle');
      currentPage++;
    } else {
      console.log('  No more pages found.');
      hasMorePages = false;
    }

    // Safety limit to prevent infinite loops
    if (currentPage > 100) {
      console.log('  Reached safety limit of 100 pages. Stopping.');
      hasMorePages = false;
    }
  }

  // Remove duplicates based on URL
  const uniqueAssociations = Array.from(
    new Map(allAssociations.map(item => [item.url, item])).values()
  );

  console.log(`\n✓ Scraping complete!`);
  console.log(`  Total associations found: ${allAssociations.length}`);
  console.log(`  Unique associations: ${uniqueAssociations.length}`);
  console.log(`  Pages scraped: ${currentPage}`);

  // Save to JSON file
  const outputDir = path.join(process.cwd(), 'web', 'test-results', 'scraped-data');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const outputFile = path.join(outputDir, `gavle-foreningar-${timestamp}.json`);

  const output = {
    metadata: {
      source: baseUrl,
      scrapedAt: new Date().toISOString(),
      totalPages: currentPage,
      totalAssociations: allAssociations.length,
      uniqueAssociations: uniqueAssociations.length
    },
    associations: uniqueAssociations
  };

  fs.writeFileSync(outputFile, JSON.stringify(output, null, 2), 'utf-8');
  console.log(`\n✓ Data saved to: ${outputFile}`);

  // Assertions to verify the scrape was successful
  expect(uniqueAssociations.length).toBeGreaterThan(0);
  expect(currentPage).toBeGreaterThan(0);

  // Sample the first few associations for verification
  console.log('\nSample of scraped associations:');
  uniqueAssociations.slice(0, 5).forEach((assoc, idx) => {
    console.log(`  ${idx + 1}. ${assoc.name}`);
    console.log(`     URL: ${assoc.url}`);
    console.log(`     Page: ${assoc.pageNumber}`);
  });
});

/**
 * Optional: Test to scrape detailed information from individual association pages
 * This would visit each association's detail page and extract additional data
 */
test.skip('scrape detailed association information', async ({ page }) => {
  // Read the previously scraped associations
  const scrapedDataDir = path.join(process.cwd(), 'web', 'test-results', 'scraped-data');
  const files = fs.readdirSync(scrapedDataDir).filter(f => f.startsWith('gavle-foreningar-'));

  if (files.length === 0) {
    console.log('No scraped data found. Run the main scraper first.');
    return;
  }

  // Get the most recent file
  const latestFile = files.sort().reverse()[0];
  const data = JSON.parse(fs.readFileSync(path.join(scrapedDataDir, latestFile), 'utf-8'));

  console.log(`Loading ${data.associations.length} associations from ${latestFile}...`);

  const detailedData: any[] = [];

  // Limit to first 10 for testing, remove limit for full scrape
  const associationsToScrape = data.associations.slice(0, 10);

  for (const [index, assoc] of associationsToScrape.entries()) {
    console.log(`\nScraping details for ${index + 1}/${associationsToScrape.length}: ${assoc.name}`);

    try {
      await page.goto(assoc.url, { waitUntil: 'networkidle', timeout: 10000 });

      // Extract detailed information from the page
      const details = await page.evaluate(() => {
        const data: any = {};

        // Example: Extract all text content from the page
        // Adjust these selectors based on actual page structure
        data.fullText = document.body.innerText;

        // Try to find common fields
        const rows = document.querySelectorAll('tr, .field, .info-row');
        rows.forEach(row => {
          const label = row.querySelector('th, .label, strong')?.textContent?.trim();
          const value = row.querySelector('td, .value, span')?.textContent?.trim();
          if (label && value) {
            data[label] = value;
          }
        });

        return data;
      });

      detailedData.push({
        ...assoc,
        details
      });

      // Be polite to the server
      await page.waitForTimeout(500);

    } catch (error) {
      console.log(`  ✗ Failed to scrape ${assoc.name}: ${error}`);
      detailedData.push({
        ...assoc,
        error: String(error)
      });
    }
  }

  // Save detailed data
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const outputFile = path.join(scrapedDataDir, `gavle-foreningar-detailed-${timestamp}.json`);

  fs.writeFileSync(outputFile, JSON.stringify(detailedData, null, 2), 'utf-8');
  console.log(`\n✓ Detailed data saved to: ${outputFile}`);
});
