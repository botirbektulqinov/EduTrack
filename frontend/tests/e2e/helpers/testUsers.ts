export const e2eUsers = {
  admin: {
    email: process.env.E2E_ADMIN_EMAIL || 'admin.e2e@edutrack.test',
  },
  teacher: {
    email: process.env.E2E_TEACHER_EMAIL || 'teacher.e2e@edutrack.test',
  },
  teacher2: {
    email: process.env.E2E_TEACHER2_EMAIL || 'teacher2.e2e@edutrack.test',
  },
  student: {
    email: process.env.E2E_STUDENT_EMAIL || 'student.e2e@edutrack.test',
  },
  student2: {
    email: process.env.E2E_STUDENT2_EMAIL || 'student2.e2e@edutrack.test',
  },
  password: process.env.E2E_PASSWORD || 'E2EPassword123!',
};

export const seededNames = {
  activeAssessment: 'E2E Seeded Assessment',
  analyticsAssessment: 'E2E Previous Analytics Quiz',
  group: 'E2E QA Group A',
};
