import { expect, test, type Page } from '@playwright/test';

const now = '2026-04-29T12:00:00Z';

const users = {
  teacher: {
    id: 'teacher-1',
    email: 'teacher@example.invalid',
    full_name: 'Teacher One',
    role: 'teacher',
    is_active: true,
    extra_time_factor: 1,
    created_at: now,
    updated_at: now,
  },
  student: {
    id: 'student-1',
    email: 'student@example.invalid',
    full_name: 'Student One',
    role: 'student',
    is_active: true,
    extra_time_factor: 1,
    created_at: now,
    updated_at: now,
  },
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    class MockWebSocket {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSING = 2;
      static CLOSED = 3;

      readyState = MockWebSocket.OPEN;
      onopen: ((event: Event) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;

      constructor() {
        window.setTimeout(() => this.onopen?.(new Event('open')), 0);
      }

      send() {
        return undefined;
      }

      close() {
        this.readyState = MockWebSocket.CLOSED;
        this.onclose?.(new CloseEvent('close'));
      }
    }

    Object.defineProperty(window, 'WebSocket', {
      configurable: true,
      writable: true,
      value: MockWebSocket,
    });
  });
});

async function mockAuth(page: Page, role: keyof typeof users) {
  const user = users[role];
  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          access_token: `${role}-access-token`,
          refresh_token: `${role}-refresh-token`,
          token_type: 'bearer',
        },
      }),
    });
  });
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: user }),
    });
  });
}

async function mockTeacherDashboard(page: Page) {
  await page.route('**/api/v1/teacher/assessments', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: [] }),
    });
  });
  await page.route('**/api/v1/teacher/assessments/groups', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: [] }),
    });
  });
}

async function mockStudentDashboard(page: Page) {
  await page.route('**/api/v1/student/analytics/dashboard', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          student_name: 'Student One',
          overall_score_avg: null,
          pass_rate: null,
          assessments_taken: 0,
          assessments_passed: 0,
          streak_count: 0,
          improvement_rate: null,
          violation_count_total: 0,
          score_trend: [],
          subject_scores: [],
          weak_topics: [],
          recent_results: [],
        },
      }),
    });
  });
  await page.route('**/api/v1/student/analytics/available-assessments', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: [
          {
            id: 'assessment-1',
            title: 'Algebra Quiz',
            description: 'Short practice quiz',
            assessment_type: 'quiz',
            group_name: 'Math 101',
            time_limit_minutes: 10,
            max_attempts: 1,
            attempts_used: 0,
            can_attempt: true,
            in_progress: false,
            access_token: 'assessment-token',
          },
        ],
      }),
    });
  });
  await page.route('**/api/v1/student/analytics/subjects', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: [] }),
    });
  });
}

async function mockAssessmentTake(page: Page) {
  await page.route('**/api/v1/student/take/assessment-token**', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            assessment: {
              id: 'assessment-1',
              title: 'Algebra Quiz',
              description: 'Short practice quiz',
              assessment_type: 'quiz',
              time_limit_minutes: 10,
              max_attempts: 1,
              passing_score: 70,
              max_violations: 3,
              time_penalty_minutes: 2,
              enforce_fullscreen: false,
              block_keyboard_shortcuts: true,
              tab_switch_detection: true,
              devtools_detection: true,
              right_click_block: true,
              copy_paste_block: true,
            },
          },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          attempt_id: 'attempt-1',
          server_token: 'server-token',
          time_limit_seconds: 600,
          questions: [
            {
              id: 'question-1',
              assessment_id: 'assessment-1',
              question_type: 'mcq_single',
              content: 'Pick the correct answer',
              points: 1,
              partial_scoring: false,
              negative_marking: 0,
              options: [
                {
                  id: 'option-1',
                  question_id: 'question-1',
                  content: 'Correct',
                  is_correct: true,
                },
              ],
            },
          ],
        },
      }),
    });
  });
  await page.route('**/api/v1/student/attempts/attempt-1/save', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: { saved: true } }),
    });
  });
  await page.route('**/api/v1/student/attempts/attempt-1/submit', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: { status: 'submitted' } }),
    });
  });
}

async function setAuthenticatedUser(page: Page, role: keyof typeof users) {
  await page.addInitScript(
    ({ user, accessToken, refreshToken }) => {
      localStorage.setItem(
        'edutrack-auth',
        JSON.stringify({
          state: {
            user,
            accessToken,
            refreshToken,
            isAuthenticated: true,
          },
          version: 0,
        }),
      );
    },
    {
      user: users[role],
      accessToken: `${role}-access-token`,
      refreshToken: `${role}-refresh-token`,
    },
  );
}

test('login page renders and protected routes redirect unauthenticated users', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible();

  await page.goto('/student/dashboard');
  await expect(page).toHaveURL(/\/login$/);
});

test('invalid login shows an error', async ({ page }) => {
  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'Invalid email or password' }),
    });
  });

  await page.goto('/login');
  await page.getByLabel('Email').fill('student@example.edu');
  await page.getByLabel('Password').fill('wrong-password');
  await page.getByRole('button', { name: 'Sign In' }).click();

  await expect(page.getByText('Invalid email or password')).toBeVisible();
});

test('teacher login reaches the analytics dashboard empty state', async ({ page }) => {
  await mockAuth(page, 'teacher');
  await mockTeacherDashboard(page);

  await page.goto('/login');
  await page.getByLabel('Email').fill('teacher@example.invalid');
  await page.getByLabel('Password').fill('test-login-value');
  await page.getByRole('button', { name: 'Sign In' }).click();

  await expect(page).toHaveURL(/\/teacher\/dashboard$/);
  await expect(page.getByRole('heading', { name: 'Analytics Dashboard' })).toBeVisible();
  await expect(page.getByText('No data yet')).toBeVisible();
});

test('student can open the available assessment list and take page', async ({ page }) => {
  await setAuthenticatedUser(page, 'student');
  await mockStudentDashboard(page);
  await mockAssessmentTake(page);

  await page.goto('/student/dashboard');

  await expect(page.getByRole('heading', { name: 'My Dashboard' })).toBeVisible();
  await expect(page.getByText('Available Assessments')).toBeVisible();
  await expect(page.getByText('Algebra Quiz')).toBeVisible();

  await page.getByRole('button', { name: 'Start' }).click();
  await expect(page).toHaveURL(/\/take\/assessment-token$/);
  await expect(page.getByRole('heading', { name: 'Algebra Quiz' })).toBeVisible();
});

test('student can submit a simple mocked assessment', async ({ page }) => {
  await setAuthenticatedUser(page, 'student');
  await mockAssessmentTake(page);

  await page.goto('/take/assessment-token');
  await page.getByRole('button', { name: 'Begin Assessment' }).click();
  await expect(page.getByText('Pick the correct answer')).toBeVisible();

  await page.getByText('Correct', { exact: true }).click();
  await page.getByRole('button', { name: /^Submit$/ }).click();
  await expect(page.getByRole('heading', { name: 'Submit Assessment' })).toBeVisible();
  await page.getByRole('dialog').getByRole('button', { name: /^Submit$/ }).click();

  await expect(page.getByRole('heading', { name: 'Assessment Submitted' })).toBeVisible();
});

test('student analytics empty state renders safely', async ({ page }) => {
  await setAuthenticatedUser(page, 'student');
  await mockStudentDashboard(page);

  await page.goto('/student/dashboard');

  await expect(page.getByText('No score data yet.')).toBeVisible();
  await expect(page.getByText('No subjects yet.')).toBeVisible();
  await expect(page.getByText('No recent results.')).toBeVisible();
});

test('user can logout', async ({ page }) => {
  await setAuthenticatedUser(page, 'student');
  await mockStudentDashboard(page);
  await page.route('**/api/v1/auth/logout', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: { message: 'Logged out' } }),
    });
  });

  await page.goto('/student/dashboard');
  await page.getByTitle('Logout').click();

  await expect(page).toHaveURL(/\/login$/);
});
