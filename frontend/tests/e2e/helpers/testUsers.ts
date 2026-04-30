const requiredEnv = (name: string) => {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Set ${name} before running real E2E tests.`);
  }
  return value;
};

export const e2eUsers = {
  admin: {
    email: requiredEnv('E2E_ADMIN_EMAIL'),
  },
  teacher: {
    email: requiredEnv('E2E_TEACHER_EMAIL'),
  },
  teacher2: {
    email: requiredEnv('E2E_TEACHER2_EMAIL'),
  },
  student: {
    email: requiredEnv('E2E_STUDENT_EMAIL'),
  },
  student2: {
    email: requiredEnv('E2E_STUDENT2_EMAIL'),
  },
  password: requiredEnv('E2E_PASSWORD'),
};

export const seededNames = {
  activeAssessment: 'E2E Seeded Assessment',
  analyticsAssessment: 'E2E Previous Analytics Quiz',
  group: 'E2E QA Group A',
};
