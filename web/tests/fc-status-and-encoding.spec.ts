import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test.describe('Kortmatchning - Status och Encoding', () => {
  test.beforeEach(async ({ page }) => {
    // Logga in
    await page.goto('http://localhost:5169/login');
    await page.getByRole('textbox', { name: 'Användarnamn' }).fill('admin');
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    await page.getByRole('button', { name: 'Logga in' }).click();

    // Vänta på att vi är inloggade genom att vänta på att "Översikt" texten visas
    await page.getByRole('button', { name: 'Översikt' }).waitFor({ state: 'visible', timeout: 15000 });

    // Navigera till Kortmatchning
    await page.getByRole('button', { name: 'Kortmatchning' }).click();
    await page.waitForLoadState('networkidle', { timeout: 15000 });

    // Vänta lite extra för att säkerställa att data har laddats
    await page.waitForTimeout(1000);
  });

  test('Kontrollera statusuppdatering vid återupptagning', async ({ page }) => {
    // Leta efter första kontoutdraget
    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible();

    // Hämta nuvarande status
    const statusCell = firstRow.locator('td').nth(4); // STATUS kolumnen
    const initialStatus = await statusCell.textContent();
    console.log('Initial status:', initialStatus);

    // Klicka på "Återuppta fakturaimport" knappen
    const resumeButton = firstRow.getByRole('button', { name: /Återuppta fakturaimport/i });
    await expect(resumeButton).toBeVisible();
    await resumeButton.click();

    // Vänta en kort stund för att låta backend svara
    await page.waitForTimeout(500);

    // Kontrollera att status har ändrats MOMENTANT (inte samma som innan)
    // Status ska uppdateras direkt efter att knappen tryckts
    const updatedStatus = await statusCell.textContent();
    console.log('Uppdaterad status efter återuppta:', updatedStatus);

    // Status ska antingen vara "Under bearbetning" eller någon annan aktiv status
    // Det viktiga är att den har ändrats från initial status (om den var klar/misslyckad)
    if (initialStatus?.includes('Match Done') || initialStatus?.includes('Fel')) {
      expect(updatedStatus).not.toBe(initialStatus);
      // Och den ska nu visa en bearbetningsstatus
      expect(updatedStatus).toMatch(/(Under bearbetning|PDF|OCR|AI5)/);
    }
  });

  test('Kontrollera encoding i loggvisning', async ({ page }) => {
    // Leta efter första kontoutdraget
    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible();

    // Klicka på "Visa logg" knappen
    const logButton = firstRow.getByRole('button', { name: /Visa logg/i });
    await expect(logButton).toBeVisible();
    await logButton.click();

    // Vänta på att loggmodalen visas
    const logModal = page.getByRole('dialog', { name: /Importlogg/i });
    await expect(logModal).toBeVisible({ timeout: 10000 });

    // Kontrollera att modaltiteln har korrekt encoding
    const modalTitle = logModal.getByRole('heading', { name: /Importlogg/i });
    await expect(modalTitle).toBeVisible();

    // Vänta på att loggen har laddats klart (inte visar "Hämtar logg...")
    await page.waitForFunction(() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return false;
      const text = modal.textContent || '';
      return !text.includes('Hämtar logg...') && text.length > 100;
    }, { timeout: 10000 });

    // Hämta hela loggtexten
    const logContent = await logModal.textContent();
    console.log('Logginnehåll längd:', logContent?.length);

    // Kontrollera att det INTE finns några encoding-problem
    // Specifikt leta efter mojibake-tecken
    expect(logContent).not.toContain('�'); // Replacement character
    expect(logContent).not.toContain('Ã¤'); // ä i latin1 läst som utf-8
    expect(logContent).not.toContain('Ã¶'); // ö i latin1 läst som utf-8
    expect(logContent).not.toContain('Ã¥'); // å i latin1 läst som utf-8
    expect(logContent).not.toContain('Ã–'); // Ö i latin1 läst som utf-8
    expect(logContent).not.toContain('Ã„'); // Ä i latin1 läst som utf-8
    expect(logContent).not.toContain('Ã…'); // Å i latin1 läst som utf-8

    // Kontrollera specifika svenska ord som ska finnas korrekt
    if (logContent?.includes('Workflowkörning')) {
      // Om ordet finns, ska det vara korrekt stavat
      expect(logContent).toContain('Workflowkörning');
      expect(logContent).not.toContain('Workflowk�rning');
      expect(logContent).not.toContain('Workflowkörning'); // dubbel-encoding
    }

    if (logContent?.includes('Källa')) {
      expect(logContent).toContain('Källa');
      expect(logContent).not.toContain('K�lla');
      expect(logContent).not.toContain('Källa'); // dubbel-encoding
    }

    if (logContent?.includes('Återuppta')) {
      expect(logContent).toContain('Återuppta');
      expect(logContent).not.toContain('�teruppta');
    }

    if (logContent?.includes('körning')) {
      expect(logContent).toContain('körning');
      expect(logContent).not.toContain('k�rning');
    }

    // Ta en screenshot för manuell verifikation
    await page.screenshot({
      path: 'web/test-results/media/snapshots/fc-log-encoding-verification.png',
      fullPage: false
    });

    // Stäng modalen - använd den exakta knappen inne i modalen
    await logModal.getByRole('button', { name: 'Stäng', exact: true }).click();
    await expect(logModal).not.toBeVisible();
  });

  test('Kontrollera status i listan matchar loggstatus', async ({ page }) => {
    // Leta efter första kontoutdraget
    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible();

    // Hämta status från tabellen
    const statusCell = firstRow.locator('td').nth(4); // STATUS kolumnen
    const tableStatus = await statusCell.textContent();
    console.log('Tabellstatus:', tableStatus);

    // Öppna loggen
    const logButton = firstRow.getByRole('button', { name: /Visa logg/i });
    await logButton.click();

    // Vänta på att loggmodalen visas
    const logModal = page.getByRole('dialog', { name: /Importlogg/i });
    await expect(logModal).toBeVisible({ timeout: 10000 });

    // Vänta på att loggen har laddats klart
    await page.waitForFunction(() => {
      const modal = document.querySelector('[role="dialog"]');
      if (!modal) return false;
      const text = modal.textContent || '';
      return !text.includes('Hämtar logg...') && text.length > 100;
    }, { timeout: 10000 });

    // Hämta loggtexten
    const logContent = await logModal.textContent();

    // Kontrollera att loggstatus motsvarar tabellstatus
    // Om tabellen visar "Under bearbetning" ska loggen visa något liknande
    if (tableStatus?.includes('Under bearbetning')) {
      expect(logContent).toMatch(/(running|startad|pågår|pending|queued)/i);
    } else if (tableStatus?.includes('Match Done') || tableStatus?.includes('Matchad')) {
      expect(logContent).toMatch(/(succeeded|completed|klar|avslutad)/i);
    } else if (tableStatus?.includes('Fel')) {
      expect(logContent).toMatch(/(failed|error|fel|misslyckad)/i);
    }

    // Stäng modalen - använd den exakta knappen inne i modalen
    await logModal.getByRole('button', { name: 'Stäng', exact: true }).click();
  });
});
