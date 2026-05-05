import { test, expect } from '@playwright/test';

test.describe('Dashboard RAG Query', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a page to set localStorage
    await page.goto('/');
    
    // Inject mock token directly into localStorage to bypass login
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock-jwt-token');
      localStorage.setItem('user_email', 'admin@example.com');
    });

    // Mock the documents API so the dashboard loads
    await page.route('**/documents', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });
    
    // Mock the graph API
    await page.route('**/admin/graph', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"nodes":[], "links":[]}' });
    });
  });

  test('should submit a RAG query and display response with citations', async ({ page }) => {
    // 1. Mock the RAG query API response
    await page.route('**/query', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          answer: "Based on the provided documents, the system architecture uses Azure Container Apps. [DOC:a8399933]",
          citations: [
            {
              doc_id: "a8399933-1111-2222-3333-444444444444",
              title: "System Architecture V2",
              filename: "architecture_v2.pdf",
              snippet: "The system architecture uses Azure Container Apps for serverless scaling."
            }
          ]
        }),
      });
    });

    // 2. Navigate to dashboard
    await page.goto('/dashboard');
    await expect(page.locator('h3', { hasText: 'Secure AI Audit Assistant' })).toBeVisible();

    // 3. Type query
    await page.fill('textarea[placeholder="Ask a question..."]', 'What is the system architecture?');
    
    // 4. Submit query
    await page.keyboard.press('Enter');

    // 5. Verify the AI Answer appeared
    await expect(page.locator('text=Based on the provided documents')).toBeVisible();

    // 6. Verify the Citation appeared
    await expect(page.locator('text=System Architecture V2')).toBeVisible();
  });
});
