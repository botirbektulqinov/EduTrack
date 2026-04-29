import { expect, test } from '@playwright/test';

import { apiLogin, findTeacherAssessmentId } from './helpers/api';
import { loginViaUi } from './helpers/auth';
import { e2eUsers, seededNames } from './helpers/testUsers';

test('real teacher can view seeded dashboard, assessment, and results page', async ({ page }) => {
  await loginViaUi(page, e2eUsers.teacher.email, e2eUsers.password);

  await expect(page.getByRole('heading', { name: 'Analytics Dashboard' })).toBeVisible();
  await expect(page.getByText('Total Assessments')).toBeVisible();
  await expect(page.getByText('Total Attempts')).toBeVisible();

  await page.getByRole('link', { name: 'Assessments' }).click();
  await expect(page).toHaveURL(/\/teacher\/assessments$/);
  await expect(page.getByText(seededNames.activeAssessment)).toBeVisible();
  await expect(page.getByRole('cell', { name: seededNames.group }).first()).toBeVisible();

  await page.getByText(seededNames.activeAssessment).click();
  await expect(page.getByRole('heading', { name: seededNames.activeAssessment })).toBeVisible();
  await expect(page.getByText('Published')).toBeVisible();
  await expect(page.getByText('Access Link')).toBeVisible();

  await page.getByRole('button', { name: 'View Results' }).click();
  await expect(page.getByRole('heading', { name: 'Results' })).toBeVisible();
  await expect(page.getByText('Total Attempts')).toBeVisible();
});

test('real teacher is blocked from another teacher assessment detail', async ({ page, request }) => {
  const teacher2Tokens = await apiLogin(request, e2eUsers.teacher2.email);
  const otherAssessmentId = await findTeacherAssessmentId(
    request,
    teacher2Tokens.access_token,
    'E2E Other Teacher Assessment',
  );

  await loginViaUi(page, e2eUsers.teacher.email, e2eUsers.password);
  await page.goto(`/teacher/assessments/${otherAssessmentId}`);

  await expect(page.getByText(/failed|not found|assessment not found/i)).toBeVisible();
});
