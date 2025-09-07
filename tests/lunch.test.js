const { test, expect } = require('@playwright/test');

test.setTimeout(120_000)

test('smoke test', async ({ page }) => {
  await page.goto('http://localhost:8000');
  const content = await page.textContent('.restaurant h2:first-of-type');
  expect(content).toContain('Bistro IN');
});
