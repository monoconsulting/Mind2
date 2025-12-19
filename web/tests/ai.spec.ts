import { test, expect } from '@playwright/test'
import { execFileSync } from 'child_process'
import fs from 'fs'
import path from 'path'

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

test.describe('@ai-history', () => {
  test.use({
    viewport: { width: 1900, height: 1200 },
    recordVideo: {
      dir: 'web/test-results/media/video',
      size: { width: 1900, height: 1200 },
    },
  })

  test('log_text must not contain prompt_text (DB-level) @ai-logtext-sanitize', async ({ page }, testInfo) => {
    test.setTimeout(6 * 60_000)

    const envText = fs.readFileSync(path.join(__dirname, '../../.env'), 'utf8')
    const envLines = envText.split(/\r?\n/)
    const envMap: Record<string, string> = {}
    for (const line of envLines) {
      const match = line.match(/^([A-Z0-9_]+)=(.*)$/)
      if (!match) continue
      envMap[match[1]] = match[2]
    }
    const dbName = envMap.DB_NAME
    const dbUser = envMap.DB_USER
    const dbPass = envMap.DB_PASS
    expect(dbName).toBeTruthy()
    expect(dbUser).toBeTruthy()
    expect(dbPass).toBeTruthy()

    const mysqlQuery = (sql: string) =>
      execFileSync(
        'docker',
        ['exec', '-e', `MYSQL_PWD=${dbPass}`, 'mind2-mysql-1', 'mysql', '-u', dbUser, '-D', dbName, '-N', '-B', '-e', sql],
        { encoding: 'utf8' },
      ).trim()

    const leakingFileId = mysqlQuery(
      "SELECT file_id FROM ai_processing_history WHERE prompt_text IS NOT NULL AND log_text IS NOT NULL AND log_text LIKE CONCAT('%', prompt_text, '%') ORDER BY created_at DESC LIMIT 1;",
    )
    expect(leakingFileId).toBeTruthy()

    const beforeMaxIdRaw = mysqlQuery(
      `SELECT COALESCE(MAX(id), 0) FROM ai_processing_history WHERE file_id='${leakingFileId}' AND job_type='ai1' AND status='success';`,
    )
    const beforeMaxId = Number(beforeMaxIdRaw)
    expect(Number.isFinite(beforeMaxId)).toBeTruthy()

    await loginAsAdmin(page)
    const token = await page.evaluate(() => localStorage.getItem('mind.jwt'))
    expect(token).toBeTruthy()
    const authHeaders = { Authorization: `Bearer ${token}` }

    const restartResponse = await page.request.post(`/ai/api/receipts/${leakingFileId}/restart-ai`, { headers: authHeaders })
    expect(restartResponse.ok()).toBeTruthy()

    const deadline = Date.now() + 4 * 60_000
    let latestRow: string | null = null
    while (Date.now() < deadline) {
      const afterMaxIdRaw = mysqlQuery(
        `SELECT COALESCE(MAX(id), 0) FROM ai_processing_history WHERE file_id='${leakingFileId}' AND job_type='ai1' AND status='success';`,
      )
      const afterMaxId = Number(afterMaxIdRaw)
      if (Number.isFinite(afterMaxId) && afterMaxId > beforeMaxId) {
        latestRow = mysqlQuery(
          `SELECT id, COALESCE(prompt_text,''), COALESCE(log_text,'') FROM ai_processing_history WHERE id=${afterMaxId} LIMIT 1;`,
        )
        break
      }
      await page.waitForTimeout(3000)
    }

    expect(latestRow).toBeTruthy()
    const parts = String(latestRow).split('\t')
    expect(parts.length).toBeGreaterThanOrEqual(3)
    const promptText = parts[1] ?? ''
    const logText = parts.slice(2).join('\t')
    expect(promptText.length).toBeGreaterThan(0)
    expect(logText.length).toBeGreaterThan(0)
    expect(logText).not.toContain(promptText)

    await testInfo.attach('ai-processing-history-latest-ai1.tsv', {
      body: Buffer.from(String(latestRow), 'utf8'),
      contentType: 'text/plain',
    })
    await testInfo.attach('ai-page', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })
  })
})

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

test('test', async ({ page }) => {
  await page.goto('http://localhost:8008/login')
  await page.getByRole('textbox', { name: 'L”senord' }).click()
  await page.getByRole('textbox', { name: 'L”senord' }).fill('adminadmin')
  await page.getByRole('button', { name: 'Logga in' }).click()
  await page.getByRole('button', { name: 'AI' }).click()
  await expect(page).toHaveScreenshot('AI001.png')
  await page.getByRole('button', { name: 'LLM-konfiguration' }).click()
  await expect(page).toHaveScreenshot('AI002.png')
  await page.getByRole('button', { name: 'L„gg till leverant”r' }).click()
  await expect(page).toHaveScreenshot('AI003.png')
  await page.getByRole('textbox', { name: 'Min OpenAI-konfiguration...' }).click()
  await expect(page).toHaveScreenshot('AI004.png')
  await page.getByRole('textbox', { name: 'Min OpenAI-konfiguration...' }).fill('test')
  await page.getByRole('textbox', { name: 'sk-' }).click()
  await page.getByRole('textbox', { name: 'sk-' }).fill('skasdfjowiejfsldkjfoweifjslkdjf')
  await page.getByRole('checkbox', { name: 'Aktiverad' }).check()
  await page.getByRole('button', { name: 'Spara' }).click()
  await expect(page).toHaveScreenshot('AI005.png')
})
