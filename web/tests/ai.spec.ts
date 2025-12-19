import { test, expect } from '@playwright/test'
import { execFileSync } from 'child_process'
import fs from 'fs'
import path from 'path'

function loadDotEnv() {
  const envText = fs.readFileSync(path.join(__dirname, '../../.env'), 'utf8')
  const envLines = envText.split(/\r?\n/)
  const envMap: Record<string, string> = {}
  for (const line of envLines) {
    const match = line.match(/^([A-Z0-9_]+)=(.*)$/)
    if (!match) continue
    envMap[match[1]] = match[2]
  }
  return envMap
}

function mysqlQuery(sql: string): string {
  const envMap = loadDotEnv()
  const dbName = envMap.DB_NAME
  const dbUser = envMap.DB_USER
  const dbPass = envMap.DB_PASS
  expect(dbName).toBeTruthy()
  expect(dbUser).toBeTruthy()
  expect(dbPass).toBeTruthy()

  return execFileSync(
    'docker',
    ['exec', '-e', `MYSQL_PWD=${dbPass}`, 'mind2-mysql-1', 'mysql', '-u', dbUser, '-D', dbName, '-N', '-B', '-e', sql],
    { encoding: 'utf8' },
  ).trim()
}

test.use({
  viewport: {
    height: 1440,
    width: 3440,
  },
})

async function loginAsAdmin(page: any) {
  await page.goto('/login')
  await page.locator('input[type="password"]').fill('adminadmin')
  await page.getByRole('button', { name: 'Logga in' }).click()
  await page.waitForURL((url: URL) => !url.pathname.endsWith('/login'))
  await page.waitForFunction(() => !!localStorage.getItem('mind.jwt'))
}

test.describe('@migrations', () => {
  test.use({
    viewport: { width: 1900, height: 1200 },
    recordVideo: {
      dir: 'web/test-results/media/video',
      size: { width: 1900, height: 1200 },
    },
  })

  test('migrations do not replay or overwrite prompts @migrations', async ({ page }, testInfo) => {
    await loginAsAdmin(page)
    const token = await page.evaluate(() => localStorage.getItem('mind.jwt'))
    expect(token).toBeTruthy()
    const authHeaders = { Authorization: `Bearer ${token}` }

    await page.goto('/ai')
    await testInfo.attach('ai-page', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })

    const promptsResponse = await page.request.get('/ai/api/ai-config/prompts', { headers: authHeaders })
    expect(promptsResponse.ok()).toBeTruthy()
    const promptsPayload = (await promptsResponse.json()) as { prompts: any[] }
    const prompt = promptsPayload.prompts.find((p) => p.prompt_key === 'data_extraction')
    expect(prompt).toBeTruthy()

    const original = String(prompt.prompt_content ?? '')
    const mutated = `${original}\n\n# PW_TEST_MIGRATIONS_PROMPT_PERSIST\n`

    try {
      const updateResponse = await page.request.put(`/ai/api/ai-config/prompts/${prompt.id}`, {
        headers: authHeaders,
        data: {
          title: prompt.title,
          description: prompt.description,
          prompt_content: mutated,
          selected_model_id: prompt.selected_model_id ?? null,
        },
      })
      expect(updateResponse.ok()).toBeTruthy()

      const firstRun = await page.request.post('/ai/api/system/apply-migrations', { headers: authHeaders })
      expect(firstRun.ok()).toBeTruthy()
      const firstJson = await firstRun.json()

      const secondRun = await page.request.post('/ai/api/system/apply-migrations', { headers: authHeaders })
      expect(secondRun.ok()).toBeTruthy()
      const secondJson = await secondRun.json()

      expect(Array.isArray(secondJson.applied)).toBeTruthy()
      expect(secondJson.applied).toEqual([])

      const promptsResponseAfter = await page.request.get('/ai/api/ai-config/prompts', { headers: authHeaders })
      expect(promptsResponseAfter.ok()).toBeTruthy()
      const promptsAfter = (await promptsResponseAfter.json()) as { prompts: any[] }
      const after = promptsAfter.prompts.find((p) => p.prompt_key === 'data_extraction')
      expect(after).toBeTruthy()
      expect(String(after.prompt_content ?? '')).toBe(mutated)

      await testInfo.attach('apply-migrations-first.json', {
        body: Buffer.from(JSON.stringify(firstJson, null, 2), 'utf8'),
        contentType: 'application/json',
      })
      await testInfo.attach('apply-migrations-second.json', {
        body: Buffer.from(JSON.stringify(secondJson, null, 2), 'utf8'),
        contentType: 'application/json',
      })
    } finally {
      await page.request.put(`/ai/api/ai-config/prompts/${prompt.id}`, {
        headers: authHeaders,
        data: {
          title: prompt.title,
          description: prompt.description,
          prompt_content: original,
          selected_model_id: prompt.selected_model_id ?? null,
        },
      })
    }
  })
})

test.describe('@accounting-input-gate', () => {
  test.use({
    viewport: { width: 1900, height: 1200 },
    recordVideo: {
      dir: 'web/test-results/media/video',
      size: { width: 1900, height: 1200 },
    },
  })

  test('AI4 normalization fills missing SEK totals from original totals @accounting-input-gate', async ({ page }, testInfo) => {
    test.setTimeout(2 * 60_000)
    await loginAsAdmin(page)

    const token = await page.evaluate(() => localStorage.getItem('mind.jwt'))
    expect(token).toBeTruthy()
    const authHeaders = { Authorization: `Bearer ${token}` }

    // This file_id is expected to exist in the local dev database and to have
    // gross_amount_original + net_amount_original set (currency=SEK), while *_sek may be NULL.
    // The test resets *_sek + exchange_rate to a broken state and asserts the pipeline
    // deterministically normalizes it during AI4.
    const fileId = mysqlQuery(
      "SELECT id FROM unified_files WHERE currency='SEK' AND gross_amount_original IS NOT NULL AND net_amount_original IS NOT NULL ORDER BY updated_at DESC LIMIT 1;",
    )
    expect(fileId).toBeTruthy()

    const resetResponse = await page.request.patch(`/ai/api/receipts/${fileId}`, {
      data: {
        currency: 'SEK',
        gross_amount_sek: null,
        net_amount_sek: null,
        exchange_rate: 0,
      },
    })
    expect(resetResponse.ok()).toBeTruthy()

    const before = await page.request.get(`/ai/api/receipts/${fileId}`)
    expect(before.ok()).toBeTruthy()
    const beforeJson = await before.json()
    expect(beforeJson?.gross_amount_sek ?? null).toBeNull()
    expect(beforeJson?.net_amount_sek ?? null).toBeNull()
    expect(beforeJson?.exchange_rate ?? null).toBeNull()

    const runAi4 = await page.request.post('/ai/api/ai/process/batch', {
      headers: authHeaders,
      data: {
        file_ids: [fileId],
        processing_steps: ['AI4'],
      },
    })
    expect(runAi4.ok()).toBeTruthy()
    const runAi4Json = await runAi4.json().catch(() => null)
    expect(Array.isArray(runAi4Json?.results) || Array.isArray(runAi4Json?.items)).toBeTruthy()

    await expect
      .poll(
        async () => {
          const response = await page.request.get(`/ai/api/receipts/${fileId}`)
          if (!response.ok()) return null
          const payload = await response.json()
          if (!payload) return null
          return {
            gross: payload.gross_amount_sek ?? null,
            net: payload.net_amount_sek ?? null,
            exchange_rate: payload.exchange_rate ?? null,
          }
        },
        { timeout: 30_000 },
      )
      .toEqual({
        gross: expect.any(Number),
        net: expect.any(Number),
        exchange_rate: 1,
      })

    await page.goto('/process')
    await page.waitForLoadState('networkidle')

    await testInfo.attach('process-snapshot', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })
  })
})

/*
 * NOTE (2025-12-19):
 * This was an auto-recorded Playwright script that is unrelated to the regression checks in this repo.
 * Keeping it enabled risks accidental execution in CI/local runs (it targets hard-coded UI selectors and
 * snapshots not tied to the conversion pipeline fixes). We keep it here commented out for traceability.
 */
// test('test', async ({ page }) => {
//   await page.goto('http://localhost:8008/login')
//   await page.getByRole('textbox', { name: 'L"senord' }).click()
//   await page.getByRole('textbox', { name: 'L"senord' }).fill('adminadmin')
//   await page.getByRole('button', { name: 'Logga in' }).click()
//   await page.getByRole('button', { name: 'AI' }).click()
//   await expect(page).toHaveScreenshot('AI001.png')
//   await page.getByRole('button', { name: 'LLM-konfiguration' }).click()
//   await expect(page).toHaveScreenshot('AI002.png')
//   await page.getByRole('button', { name: 'L„gg till leverant”r' }).click()
//   await expect(page).toHaveScreenshot('AI003.png')
//   await page.getByRole('textbox', { name: 'Min OpenAI-konfiguration...' }).click()
//   await expect(page).toHaveScreenshot('AI004.png')
//   await page.getByRole('textbox', { name: 'Min OpenAI-konfiguration...' }).fill('test')
//   await page.getByRole('textbox', { name: 'sk-' }).click()
//   await page.getByRole('textbox', { name: 'sk-' }).fill('skasdfjowiejfsldkjfoweifjslkdjf')
//   await page.getByRole('checkbox', { name: 'Aktiverad' }).check()
//   await page.getByRole('button', { name: 'Spara' }).click()
//   await expect(page).toHaveScreenshot('AI005.png')
// })
test.describe('@company-resolution-fallback', () => {
  test.use({
    viewport: { width: 1900, height: 1200 },
    recordVideo: {
      dir: 'web/test-results/media/video',
      size: { width: 1900, height: 1200 },
    },
  })

  test('missing vendor identity degrades to manual review (not a crash) @company-resolution-fallback', async ({ page }, testInfo) => {
    test.setTimeout(2 * 60_000)
    await loginAsAdmin(page)
    const token = await page.evaluate(() => localStorage.getItem('mind.jwt'))
    expect(token).toBeTruthy()
    const authHeaders = { Authorization: `Bearer ${token}` }

    // Known failure-case file_id from ai_processing_history where AI3 previously crashed on:
    // "Company resolution failed: both vat/orgnr and name are missing"
    const fileId = '10c33ec7-7a0c-4729-8e37-e68811c772b8'

    const runAi3 = await page.request.post('/ai/api/ai/process/batch', {
      headers: authHeaders,
      data: {
        file_ids: [fileId],
        processing_steps: ['AI3'],
        stop_on_error: true,
      },
    })
    expect(runAi3.ok()).toBeTruthy()
    const runAi3Json = await runAi3.json()

    const result = Array.isArray(runAi3Json?.results) ? runAi3Json.results[0] : null
    expect(result?.file_id).toBe(fileId)
    expect(Array.isArray(result?.steps_completed)).toBeTruthy()
    expect(result?.steps_completed || []).toContain('AI3')
    expect(result?.error ?? null).toBeNull()

    const receiptResponse = await page.request.get(`/ai/api/receipts/${fileId}`)
    expect(receiptResponse.ok()).toBeTruthy()
    const receipt = await receiptResponse.json()
    expect(receipt?.ai_status).toBe('manual_review')

    const otherDataRaw = receipt?.other_data ?? null
    expect(typeof otherDataRaw).toBe('string')
    const otherData = JSON.parse(otherDataRaw)
    expect(otherData?.needs_review_reason).toBe('missing_vendor_identity_in_ocr')

    await page.goto('/process')
    await page.waitForLoadState('networkidle')
    await testInfo.attach('process-snapshot', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })
  })
})
