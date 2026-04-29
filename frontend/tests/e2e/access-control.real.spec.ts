import { expect, test } from '@playwright/test';

import { loginViaUi, logoutViaUi } from './helpers/auth';
import { e2eUsers } from './helpers/testUsers';

test('real protected routes redirect unauthenticated and wrong-role users', async ({ page }) => {
  await page.goto('/teacher/dashboard');
  await expect(page).toHaveURL(/\/login$/);

  await loginViaUi(page, e2eUsers.student.email, e2eUsers.password);
  await page.goto('/teacher/dashboard');
  await expect(page).toHaveURL(/\/student(\/dashboard)?$/);

  await logoutViaUi(page);
  await loginViaUi(page, e2eUsers.teacher.email, e2eUsers.password);
  await page.goto('/student/dashboard');
  await expect(page).toHaveURL(/\/teacher(\/dashboard)?$/);
});
