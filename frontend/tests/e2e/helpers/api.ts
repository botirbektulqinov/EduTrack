import type { APIRequestContext } from '@playwright/test';

import { e2eUsers } from './testUsers';

const apiURL = (process.env.E2E_API_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');

export async function apiLogin(request: APIRequestContext, email: string, password = e2eUsers.password) {
  const response = await request.post(`${apiURL}/auth/login`, {
    data: { email, password },
  });
  if (!response.ok()) {
    throw new Error(`E2E API login failed for ${email}: ${response.status()} ${await response.text()}`);
  }
  return (await response.json()) as { access_token: string; refresh_token: string };
}

export async function findTeacherAssessmentId(
  request: APIRequestContext,
  accessToken: string,
  title: string,
) {
  const response = await request.get(`${apiURL}/teacher/assessments`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok()) {
    throw new Error(`Could not list teacher assessments: ${response.status()} ${await response.text()}`);
  }
  const payload = await response.json();
  const items = payload.data ?? payload;
  const assessment = items.find((item: { title?: string }) => item.title === title);
  if (!assessment?.id) {
    throw new Error(`Seeded assessment not found: ${title}`);
  }
  return String(assessment.id);
}
