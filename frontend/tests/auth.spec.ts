import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should login successfully with mock API', async ({ page }) => {
    // 1. Mock the login API request
    await page.route('**/login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-jwt-token-12345',
          token_type: 'bearer'
        }),
      });
    });

    // 2. Navigate to the login page
    await page.goto('/');
    
    // 3. Fill in the form
    await page.fill('input[placeholder="name@example.com"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'password123');
    
    // 4. Click login
    await page.click('button[type="submit"]');

    // 5. Verify successful redirect to Dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('h3', { hasText: 'Secure AI Audit Assistant' })).toBeVisible();
  });
});
