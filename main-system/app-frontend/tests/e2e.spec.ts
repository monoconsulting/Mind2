import { test, expect } from '@playwright/test';

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'adminadmin';

const receiptsResponse = {
  items: [
    {
      id: 'rct-001',
      purchase_date: '2025-09-20',
      merchant: 'Café Stockholm',
      line_item_count: 3,
      net_amount: 180.5,
      gross_amount: 225.63,
      status: 'completed',
      original_filename: 'receipt_001.jpg',
    },
    {
      id: 'rct-002',
      purchase_date: '2025-09-19',
      merchant: 'SJ Biljetter',
      line_item_count: 1,
      net_amount: 450,
      gross_amount: 562.5,
      status: 'processing',
      original_filename: 'receipt_002.pdf',
    },
  ],
};

const statementItems = [
  {
    id: 'stmt-101',
    status: 'matched',
    created_at: '2025-09-18T08:15:00Z',
    updated_at: '2025-09-18T09:00:00Z',
  },
  {
    id: 'stmt-102',
    status: 'pending',
    created_at: '2025-09-18T10:05:00Z',
    updated_at: '2025-09-18T10:10:00Z',
  },
];

const rulesResponse = [
  { id: 'rule-1', matcher: 'merchant innehåller "Taxi"', account: '5610', note: 'Resor inom stan' },
  { id: 'rule-2', matcher: 'belopp > 5000', account: '2641', note: 'Momsjustering' },
];

test('svenska menyer och design verifieras', async ({ page }) => {
  await page.route('**/ai/api/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const { pathname } = url;
    const method = request.method();

    if (method === 'POST' && pathname.endsWith('/auth/login')) {
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: 'test-token' }),
      });
    }

    if (method === 'GET' && pathname.endsWith('/receipts')) {
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(receiptsResponse),
      });
    }

    if (method === 'POST' && pathname.endsWith('/ingest/fetch-ftp')) {
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'FTP-hämtning klar - 2 filer hämtade' }),
      });
    }

    if (method === 'GET' && pathname.endsWith('/reconciliation/firstcard/statements')) {
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: statementItems }),
      });
    }

    if (method === 'POST' && pathname.endsWith('/reconciliation/firstcard/match')) {
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ matched: true }),
      });
    }

    if (method === 'GET' && pathname.endsWith('/rules')) {
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rulesResponse),
      });
    }

    if (method === 'POST' && pathname.endsWith('/rules')) {
      return route.fulfill({
        status: 201,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: 'rule-3' }),
      });
    }

    if (method === 'GET' && pathname.endsWith('/admin/ping')) {
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
        body: 'pong',
      });
    }

    return route.fulfill({ status: 200, body: '{}' });
  });

  const capture = async (name: string) => {
    const filePath = test.info().outputPath(`${name}.png`);
    await page.screenshot({ path: filePath, fullPage: true });
    await test.info().attach(name, { path: filePath, contentType: 'image/png' });
  };

  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Logga in' })).toBeVisible();
  await capture('login-sidan');

  await page.fill('#login-username', 'admin');
  await page.fill('#login-password', ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL('**/'),
    page.getByRole('button', { name: 'Logga in' }).click(),
  ]);

  await expect(page.locator('.page-title')).toHaveText('Översikt');
  await capture('oversikt');

  await page.getByRole('button', { name: 'Testa API-anslutning' }).click();
  await expect(page.getByText('API-anslutning fungerar', { exact: false })).toBeVisible();

  const sections = [
    {
      button: 'Kvitton',
      title: 'Kvitton',
      assertion: () => expect(page.getByRole('heading', { level: 1, name: 'Kvitton' })).toBeVisible(),
      screenshot: 'kvitton',
    },
    {
      button: 'Kortmatchning',
      title: 'Kortmatchning',
      assertion: () => expect(page.getByRole('heading', { name: 'Företagskort' })).toBeVisible(),
      screenshot: 'kortmatchning',
    },
    {
      button: 'Analys',
      title: 'Analys',
      assertion: () => expect(page.getByRole('heading', { name: 'AI-panel' })).toBeVisible(),
      screenshot: 'analys',
    },
    {
      button: 'Export',
      title: 'Export',
      assertion: () => expect(page.getByRole('heading', { name: 'Exportera SIE' })).toBeVisible(),
      screenshot: 'export',
    },
    {
      button: 'Användare',
      title: 'Användare',
      assertion: () => expect(page.getByRole('heading', { name: 'Regler för kontering' })).toBeVisible(),
      screenshot: 'anvandare',
    },
  ];

  for (const section of sections) {
    await page.getByRole('button', { name: section.button, exact: true }).click();
    await expect(page.locator('.page-title')).toHaveText(section.title);
    await section.assertion();
    await capture(section.screenshot);
  }
});


