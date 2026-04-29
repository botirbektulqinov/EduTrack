import { expect, test } from '@playwright/test';

import { loginViaUi } from './helpers/auth';
import { e2eUsers, seededNames } from './helpers/testUsers';

test('real student analytics renders persisted seeded data', async ({ page }) => {
  await loginViaUi(page, e2eUsers.student.email, e2eUsers.password);
  await expect(page.getByRole('heading', { name: 'My Dashboard' })).toBeVisible();
  await expect(page.getByText('Assessments Taken')).toBeVisible();
  await expect(page.getByText('100.0%').first()).toBeVisible();
});

test('real teacher analytics renders persisted seeded data', async ({ page }) => {
  await loginViaUi(page, e2eUsers.teacher.email, e2eUsers.password);
  await expect(page.getByRole('heading', { name: 'Analytics Dashboard' })).toBeVisible();
  await expect(page.getByText(seededNames.analyticsAssessment)).toBeVisible();
  await expect(page.getByText('100.0%').first()).toBeVisible();
});
