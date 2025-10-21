import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Complete Web Scraper for Gävle Föreningsregister
 *
 * This test:
 * 1. Scrapes all associations from https://fri.gavle.se/forening/ with pagination
 * 2. Fixes homepage URLs to be complete URLs
 * 3. Visits each association's detail page and scrapes all information
 *
 * Output: JSON file with complete associations data including detailed info
 */

interface Association {
  name: string;
  url: string;
  pageNumber: number;
  extractedAt: string;
  type?: string;
  activity?: string;
  homepage?: string;
  details?: AssociationDetails;
}

interface AssociationDetails {
  contactInfo?: {
    address?: string;
    zipCode?: string;
    city?: string;
    phone?: string;
    email?: string;
    website?: string;
  };
  organizationInfo?: {
    organizationNumber?: string;
    registrationDate?: string;
    boardMembers?: string[];
    signatories?: string[];
  };
  activities?: string[];
  documents?: {
    name: string;
    year?: string;
    uploaded?: string;
  }[];
  allText?: string;
  rawFields?: Record<string, string>;
}

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test('scrape complete association data with details', async ({ page }) => {
  // Increase timeout for very long-running scrape (30 minutes)
  test.setTimeout(1800000);

  const allAssociations: Association[] = [];
  const baseUrl = 'https://fri.gavle.se/forening/';

  console.log('='.repeat(60));
  console.log('GÄVLE FÖRENINGSREGISTER - COMPLETE SCRAPER');
  console.log('='.repeat(60));
  console.log('\nPhase 1: Scraping association list...\n');

  // Navigate to the associations register
  await page.goto(baseUrl);
  await page.waitForLoadState('networkidle');

  let currentPage = 1;
  let hasMorePages = true;

  // PHASE 1: Scrape the list
  while (hasMorePages) {
    console.log(`Scraping page ${currentPage}...`);
    await page.waitForTimeout(1000);

    // Extract all association links from current page
    const associations = await page.evaluate((pageNum) => {
      const results: { name: string; url: string; pageNumber: number; extractedAt: string; type?: string; activity?: string; homepage?: string }[] = [];

      const table = document.querySelector('table');
      if (!table) return results;

      const rows = Array.from(table.querySelectorAll('tbody tr'));

      rows.forEach((row) => {
        const cells = row.querySelectorAll('td');
        if (cells.length === 0) return;

        const nameCell = cells[0];
        const link = nameCell.querySelector('a');

        if (link) {
          const name = link.textContent?.trim() || '';
          const href = (link as HTMLAnchorElement).href;

          const type = cells[1]?.textContent?.trim() || '';
          const activity = cells[2]?.textContent?.trim() || '';

          // Get homepage URL (not just text)
          const homepageLink = cells[3]?.querySelector('a');
          const homepage = homepageLink ? (homepageLink as HTMLAnchorElement).href : '';

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

    console.log(`  Found ${associations.length} associations`);
    allAssociations.push(...associations);

    // Try to find the "Next" button
    const nextButton = page.getByRole('link', { name: 'Next' });
    const isNextVisible = await nextButton.isVisible().catch(() => false);

    if (isNextVisible) {
      await nextButton.click();
      await page.waitForLoadState('networkidle');
      currentPage++;
    } else {
      hasMorePages = false;
    }

    if (currentPage > 100) {
      console.log('  Reached safety limit of 100 pages.');
      hasMorePages = false;
    }
  }

  // Remove duplicates
  const uniqueAssociations = Array.from(
    new Map(allAssociations.map(item => [item.url, item])).values()
  );

  console.log(`\n✓ Phase 1 complete!`);
  console.log(`  Total associations: ${uniqueAssociations.length}`);
  console.log(`  Pages scraped: ${currentPage}`);

  // PHASE 2: Scrape details from each association page
  console.log('\n' + '='.repeat(60));
  console.log('Phase 2: Scraping detailed information...');
  console.log('='.repeat(60));
  console.log(`\nVisiting ${uniqueAssociations.length} association pages...\n`);

  for (const [index, assoc] of uniqueAssociations.entries()) {
    const progress = `[${index + 1}/${uniqueAssociations.length}]`;
    console.log(`${progress} ${assoc.name}`);

    try {
      await page.goto(assoc.url, {
        waitUntil: 'networkidle',
        timeout: 15000
      });

      // Extract detailed information
      const details = await page.evaluate(() => {
        const data: AssociationDetails = {
          contactInfo: {},
          organizationInfo: {},
          activities: [],
          documents: [],
          rawFields: {}
        };

        // Extract all table rows with information
        const tables = document.querySelectorAll('table');

        tables.forEach(table => {
          const rows = table.querySelectorAll('tr');

          rows.forEach(row => {
            const cells = row.querySelectorAll('td, th');
            if (cells.length >= 2) {
              const label = cells[0]?.textContent?.trim() || '';
              const value = cells[1]?.textContent?.trim() || '';

              if (label && value) {
                // Store in raw fields
                data.rawFields![label] = value;

                // Parse specific fields
                const lowerLabel = label.toLowerCase();

                if (lowerLabel.includes('adress') || lowerLabel.includes('address')) {
                  data.contactInfo!.address = value;
                } else if (lowerLabel.includes('postnummer') || lowerLabel.includes('zip')) {
                  data.contactInfo!.zipCode = value;
                } else if (lowerLabel.includes('postort') || lowerLabel.includes('city')) {
                  data.contactInfo!.city = value;
                } else if (lowerLabel.includes('telefon') || lowerLabel.includes('phone')) {
                  data.contactInfo!.phone = value;
                } else if (lowerLabel.includes('e-post') || lowerLabel.includes('email') || lowerLabel.includes('mail')) {
                  data.contactInfo!.email = value;
                } else if (lowerLabel.includes('hemsida') || lowerLabel.includes('webbplats') || lowerLabel.includes('website')) {
                  data.contactInfo!.website = value;
                } else if (lowerLabel.includes('organisationsnummer') || lowerLabel.includes('org.nr')) {
                  data.organizationInfo!.organizationNumber = value;
                } else if (lowerLabel.includes('registrerad') || lowerLabel.includes('registered')) {
                  data.organizationInfo!.registrationDate = value;
                }
              }
            }
          });
        });

        // Extract board members (styrelse)
        const boardSection = Array.from(document.querySelectorAll('h2, h3, h4'))
          .find(h => h.textContent?.toLowerCase().includes('styrelse'));

        if (boardSection) {
          const boardList: string[] = [];
          let nextElement = boardSection.nextElementSibling;

          while (nextElement && !nextElement.matches('h2, h3, h4')) {
            if (nextElement.matches('ul, ol')) {
              const items = nextElement.querySelectorAll('li');
              items.forEach(item => {
                const text = item.textContent?.trim();
                if (text) boardList.push(text);
              });
            } else if (nextElement.matches('table')) {
              const rows = nextElement.querySelectorAll('tr');
              rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length > 0) {
                  const text = Array.from(cells).map(c => c.textContent?.trim()).join(' - ');
                  if (text) boardList.push(text);
                }
              });
            }
            nextElement = nextElement.nextElementSibling;
          }

          if (boardList.length > 0) {
            data.organizationInfo!.boardMembers = boardList;
          }
        }

        // Extract documents
        const docLinks = document.querySelectorAll('a[href*=".pdf"], a[href*="/documents/"], a[href*="/dokument/"]');
        docLinks.forEach(link => {
          const name = link.textContent?.trim() || '';
          const href = (link as HTMLAnchorElement).href;

          if (name) {
            data.documents!.push({
              name,
              year: name.match(/\d{4}/)?.[0],
              uploaded: href
            });
          }
        });

        // Get all text content for full-text search capability
        data.allText = document.body.innerText;

        return data;
      });

      // Attach details to association
      assoc.details = details;

      // Be polite to the server - wait between requests
      await page.waitForTimeout(300);

    } catch (error) {
      console.log(`  ✗ Failed: ${error}`);
      assoc.details = {
        rawFields: { error: String(error) }
      };
    }

    // Progress indicator every 50 associations
    if ((index + 1) % 50 === 0) {
      console.log(`  ... ${index + 1}/${uniqueAssociations.length} completed`);
    }
  }

  console.log(`\n✓ Phase 2 complete!`);
  console.log(`  All ${uniqueAssociations.length} associations scraped with details`);

  // Save complete data
  const outputDir = path.join(process.cwd(), 'web', 'test-results', 'scraped-data');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const outputFile = path.join(outputDir, `gavle-foreningar-complete-${timestamp}.json`);

  const output = {
    metadata: {
      source: baseUrl,
      scrapedAt: new Date().toISOString(),
      totalPages: currentPage,
      totalAssociations: uniqueAssociations.length,
      includesDetailedInfo: true,
      scrapeType: 'complete'
    },
    associations: uniqueAssociations
  };

  fs.writeFileSync(outputFile, JSON.stringify(output, null, 2), 'utf-8');

  console.log('\n' + '='.repeat(60));
  console.log('SCRAPING COMPLETE!');
  console.log('='.repeat(60));
  console.log(`\n✓ Complete data saved to:`);
  console.log(`  ${outputFile}`);
  console.log(`\n✓ Statistics:`);
  console.log(`  - Associations: ${uniqueAssociations.length}`);
  console.log(`  - Pages scraped: ${currentPage}`);
  console.log(`  - Detailed info: YES`);
  console.log(`  - Homepage URLs: Fixed to full URLs`);

  // Show sample with details
  console.log('\n✓ Sample association with details:');
  const sample = uniqueAssociations[0];
  console.log(`  Name: ${sample.name}`);
  console.log(`  Type: ${sample.type || 'N/A'}`);
  console.log(`  Homepage: ${sample.homepage || 'N/A'}`);
  if (sample.details?.contactInfo?.email) {
    console.log(`  Email: ${sample.details.contactInfo.email}`);
  }
  if (sample.details?.contactInfo?.phone) {
    console.log(`  Phone: ${sample.details.contactInfo.phone}`);
  }
  if (sample.details?.organizationInfo?.organizationNumber) {
    console.log(`  Org.nr: ${sample.details.organizationInfo.organizationNumber}`);
  }

  // Assertions
  expect(uniqueAssociations.length).toBeGreaterThan(0);
  expect(currentPage).toBeGreaterThan(0);
});
