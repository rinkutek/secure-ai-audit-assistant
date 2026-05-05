import { test, expect } from '@playwright/test';

test.describe('Live Backend E2E Flow', () => {
  test('should reject invalid live login securely', async ({ page }) => {
    await page.goto('/');
    
    // We are NOT mocking the API here. This hits the real live backend.
    await page.fill('input[placeholder="name@example.com"]', 'hacker@example.com');
    await page.fill('input[type="password"]', 'badpassword123');
    await page.click('button[type="submit"]');

    // The live backend should reject this
    await expect(page.locator('text=Invalid credentials')).toBeVisible({ timeout: 5000 });
  });

  test('admin should be able to reach dashboard live', async ({ page }) => {
    // Assuming the docker-compose environment seeds an admin@example.com user
    // If not, this test will fail and alert us that the seed is missing
    await page.goto('/');
    await page.fill('input[placeholder="name@example.com"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'AdminPass123!');
    await page.click('button[type="submit"]');

    // Verify successful redirect to Dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('h3', { hasText: 'Secure AI Audit Assistant' })).toBeVisible();
  });
});
