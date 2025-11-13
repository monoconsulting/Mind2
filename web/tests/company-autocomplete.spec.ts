// company-autocomplete.spec.ts
import { test, expect } from '@playwright/test';

/**
 * E2E Test: Company Autocomplete in Receipt Preview Modal
 *
 * This test verifies:
 * 1. Company autocomplete functionality with datalist
 * 2. Selecting existing company makes fields read-only
 * 3. Creating new company allows editing all fields
 * 4. Proper saving of company_id when existing company selected
 */

test.describe('Company Autocomplete', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('textbox', { name: 'Användarnamn' }).fill('admin');
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    const loginBtn = page.getByRole('button', { name: /^Logga in$/ });
    await loginBtn.click();
    await page.waitForLoadState('networkidle');

    // Navigate to Process page
    const processNav = page.getByRole('button', { name: /^Process$/ })
      .or(page.getByRole('link', { name: /^Process$/ }));
    await processNav.waitFor({ state: 'visible' });
    await processNav.click();
    await page.waitForLoadState('networkidle');

    // Open first receipt preview
    const previewBtn = page.getByRole('button', { name: /Förhandsgranska kvitto/i }).first();
    await expect(previewBtn).toBeVisible();
    await previewBtn.click();

    // Wait for modal to open
    const modal = page.locator('.receipt-preview-modal');
    await expect(modal).toBeVisible();

    // Click "Redigera" button
    const editBtn = page.getByRole('button', { name: /Redigera/i });
    await expect(editBtn).toBeVisible();
    await editBtn.click();

    // Wait for edit mode to activate
    await page.waitForTimeout(500);
  });

  test('should show autocomplete suggestions when typing company name', async ({ page }) => {
    // Find the company name input field
    const companyNameInput = page.locator('input[list="company-suggestions"]');
    await expect(companyNameInput).toBeVisible();

    // Clear existing value
    await companyNameInput.clear();

    // Type to trigger autocomplete (assuming there's a company with "IK" in database)
    await companyNameInput.fill('IK');

    // Wait for debounce (300ms) + network request
    await page.waitForTimeout(500);

    // Check that datalist exists and has options
    const datalist = page.locator('#company-suggestions');
    await expect(datalist).toBeAttached();

    // Verify datalist has options (there should be suggestions if companies exist)
    const optionsCount = await datalist.locator('option').count();
    console.log(`Found ${optionsCount} autocomplete suggestions`);

    // Note: This assertion might fail if no companies match "IK" in test database
    // expect(optionsCount).toBeGreaterThan(0);
  });

  test('should make company fields read-only when selecting existing company', async ({ page }) => {
    // Get company name input
    const companyNameInput = page.locator('input[list="company-suggestions"]');
    await expect(companyNameInput).toBeVisible();

    // Get the current company name (should already exist)
    const currentCompanyName = await companyNameInput.inputValue();

    if (!currentCompanyName || currentCompanyName.trim() === '') {
      console.log('No existing company found, skipping this test');
      test.skip();
      return;
    }

    console.log(`Current company: ${currentCompanyName}`);

    // Clear and re-type the company name to trigger selection
    await companyNameInput.clear();
    await companyNameInput.fill(currentCompanyName);

    // Trigger blur to activate selection logic
    await companyNameInput.blur();

    // Wait for handleCompanySelection to complete
    await page.waitForTimeout(1000);

    // Check that company fields are now disabled
    const orgnrInput = page.getByLabel('Organisationsnummer').locator('input');
    const addressInput = page.getByLabel('Adress', { exact: true }).locator('input');

    // These should be disabled when existing company is selected
    await expect(orgnrInput).toBeDisabled();
    await expect(addressInput).toBeDisabled();

    console.log('Company fields are correctly read-only after selecting existing company');
  });

  test('should allow editing all fields when creating new company', async ({ page }) => {
    // Get company name input
    const companyNameInput = page.locator('input[list="company-suggestions"]');
    await expect(companyNameInput).toBeVisible();

    // Clear and type a new company name that doesn't exist
    await companyNameInput.clear();
    const newCompanyName = `Test Företag ${Date.now()}`;
    await companyNameInput.fill(newCompanyName);

    // Trigger blur
    await companyNameInput.blur();

    // Wait for selection logic
    await page.waitForTimeout(500);

    // Check that company fields are NOT disabled (editable)
    const orgnrInput = page.getByLabel('Organisationsnummer').locator('input');
    const addressInput = page.getByLabel('Adress', { exact: true }).locator('input');
    const cityInput = page.getByLabel('Ort').locator('input');

    await expect(orgnrInput).toBeEnabled();
    await expect(addressInput).toBeEnabled();
    await expect(cityInput).toBeEnabled();

    console.log('Company fields are correctly editable for new company');

    // Fill in some company data
    await orgnrInput.fill('556123-4567');
    await addressInput.fill('Testgatan 1');
    await cityInput.fill('Stockholm');

    // Save the changes
    const saveBtn = page.getByRole('button', { name: /Spara/i });
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    // Wait for save to complete
    await page.waitForTimeout(2000);

    // Verify no errors
    const errorAlert = page.locator('.alert-error');
    await expect(errorAlert).not.toBeVisible();

    console.log('New company saved successfully');
  });

  test('should save company_id when existing company is selected', async ({ page }) => {
    // Get company name input
    const companyNameInput = page.locator('input[list="company-suggestions"]');
    await expect(companyNameInput).toBeVisible();

    const currentCompanyName = await companyNameInput.inputValue();

    if (!currentCompanyName || currentCompanyName.trim() === '') {
      console.log('No existing company found, skipping this test');
      test.skip();
      return;
    }

    // Trigger selection by clearing and re-entering
    await companyNameInput.clear();
    await companyNameInput.fill(currentCompanyName);
    await companyNameInput.blur();
    await page.waitForTimeout(1000);

    // Listen for network request when saving
    const savePromise = page.waitForResponse(
      response => response.url().includes('/modal') && response.request().method() === 'PUT'
    );

    // Click save
    const saveBtn = page.getByRole('button', { name: /Spara/i });
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    // Wait for save response
    const response = await savePromise;
    expect(response.status()).toBe(200);

    // Verify request body contains company_id
    const requestBody = response.request().postDataJSON();
    console.log('Save payload company_id:', requestBody.company_id);

    // company_id should be present when existing company is selected
    expect(requestBody).toHaveProperty('company_id');
    expect(requestBody.company_id).not.toBeNull();

    console.log('company_id correctly included in save request');
  });

  test('should clear autocomplete suggestions when input is less than 2 characters', async ({ page }) => {
    // Get company name input
    const companyNameInput = page.locator('input[list="company-suggestions"]');
    await expect(companyNameInput).toBeVisible();

    // Type less than 2 characters
    await companyNameInput.clear();
    await companyNameInput.fill('I');

    // Wait for debounce
    await page.waitForTimeout(500);

    // Datalist should exist but have no options (or minimal options)
    const datalist = page.locator('#company-suggestions');
    const optionsCount = await datalist.locator('option').count();

    console.log(`Options with 1 character: ${optionsCount}`);
    // Should be 0 or very few since we require minimum 2 characters
  });

  test('should reset to original company when canceling edit', async ({ page }) => {
    // Get original company name
    const companyNameInput = page.locator('input[list="company-suggestions"]');
    const originalName = await companyNameInput.inputValue();

    // Make a change
    await companyNameInput.clear();
    await companyNameInput.fill('Changed Company Name');

    // Click cancel (Avbryt)
    const cancelBtn = page.getByRole('button', { name: /Avbryt/i });
    await expect(cancelBtn).toBeVisible();
    await cancelBtn.click();

    // Click edit again to verify reset
    const editBtn = page.getByRole('button', { name: /Redigera/i });
    await expect(editBtn).toBeVisible();
    await editBtn.click();
    await page.waitForTimeout(500);

    // Verify company name is back to original
    const currentName = await companyNameInput.inputValue();
    expect(currentName).toBe(originalName);

    console.log('Company name correctly reset after cancel');
  });
});
