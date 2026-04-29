import { expect, type Page } from '@playwright/test';

export async function loginViaUi(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.waitForURL(/\/(admin|teacher|student)\/dashboard$/, { timeout: 10_000 });
}

export async function logoutViaUi(page: Page) {
  await page.getByTitle('Logout').click();
  await expect(page).toHaveURL(/\/login$/);
}
