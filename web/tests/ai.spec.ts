import { test, expect } from '@playwright/test'

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
