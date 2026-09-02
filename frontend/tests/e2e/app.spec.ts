import { test, expect } from '@playwright/test';

test('login page loads', async ({ page }) => {
  await page.goto('/login');
  await expect(page.locator('h1')).toContainText('LC-MS Method Predictor');
});

test('can switch between login and register', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByText('Sign In')).toBeVisible();
  await page.getByText("Don't have an account? Register").click();
  await expect(page.getByText('Register')).toBeVisible();
});
