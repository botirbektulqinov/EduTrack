import { expect, test } from '@playwright/test';

import { loginViaUi, logoutViaUi } from './helpers/auth';
import { e2eUsers } from './helpers/testUsers';

test('real auth flow supports invalid login, teacher login, student login, and logout', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible();

  await page.getByLabel('Email').fill(e2eUsers.student.email);
  await page.getByLabel('Password').fill('definitely-wrong');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByText(/wrong email or password|invalid credentials/i)).toBeVisible();

  await loginViaUi(page, e2eUsers.teacher.email, e2eUsers.password);
  await expect(page).toHaveURL(/\/teacher\/dashboard$/);
  await expect(page.getByRole('heading', { name: 'Analytics Dashboard' })).toBeVisible();
  await logoutViaUi(page);

  await loginViaUi(page, e2eUsers.student.email, e2eUsers.password);
  await expect(page).toHaveURL(/\/student\/dashboard$/);
  await expect(page.getByRole('heading', { name: 'My Dashboard' })).toBeVisible();
  await logoutViaUi(page);
});
