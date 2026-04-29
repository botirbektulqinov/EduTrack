import { expect, test } from '@playwright/test';

import { loginViaUi } from './helpers/auth';
import { e2eUsers, seededNames } from './helpers/testUsers';

test('real student can start, answer, and submit the seeded assessment', async ({ page }) => {
  await loginViaUi(page, e2eUsers.student.email, e2eUsers.password);

  await expect(page.getByRole('heading', { name: 'My Dashboard' })).toBeVisible();
  await expect(page.getByText(seededNames.activeAssessment)).toBeVisible();
  await page
    .locator('div')
    .filter({ hasText: seededNames.activeAssessment })
    .getByRole('button', { name: /start|continue/i })
    .first()
    .click();

  await expect(page.getByRole('heading', { name: seededNames.activeAssessment })).toBeVisible();
  await page.getByRole('button', { name: 'Begin Assessment' }).click();

  await expect(page.getByText('E2E: Which answer is correct?')).toBeVisible();
  await page.getByText('Correct seeded option', { exact: true }).click();
  await page.getByRole('button', { name: 'Next' }).click();

  await expect(page.getByText('E2E: What is 6 * 7?')).toBeVisible();
  await page.getByPlaceholder('Enter a number').fill('42');
  await page.getByRole('button', { name: 'Next' }).click();

  await expect(page.getByText('E2E: Briefly explain what a regression test protects.')).toBeVisible();
  await page.getByPlaceholder('Type your answer…').fill('It protects important behavior from regressions.');

  await page.getByRole('button', { name: /^Submit$/ }).click();
  await expect(page.getByRole('heading', { name: 'Submit Assessment' })).toBeVisible();
  await page.getByRole('dialog').getByRole('button', { name: /^Submit$/ }).click();

  await expect(page.getByRole('heading', { name: 'Assessment Submitted' })).toBeVisible();
});
