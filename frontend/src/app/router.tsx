/* ─── EduTrack — Application Router ─── */
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/shared/AppLayout';
import { AuthLayout } from '@/components/shared/AuthLayout';
import { ProtectedRoute } from '@/components/shared/ProtectedRoute';

/* Auth Pages */
import LoginPage from '@/modules/auth/LoginPage';
import ForgotPasswordPage from '@/modules/auth/ForgotPasswordPage';
import ResetPasswordPage from '@/modules/auth/ResetPasswordPage';

/* Admin Pages */
import AdminUsersPage from '@/modules/admin/users/AdminUsersPage';
import AdminUserDetailPage from '@/modules/admin/users/AdminUserDetailPage';
import AdminGroupsPage from '@/modules/admin/groups/AdminGroupsPage';
import AdminGroupDetailPage from '@/modules/admin/groups/AdminGroupDetailPage';
import AdminDashboardPage from '@/modules/admin/analytics/AdminDashboardPage';
import AdminReportsPage from '@/modules/admin/reports/AdminReportsPage';

/* Teacher Pages */
import TeacherAssessmentsPage from '@/modules/teacher/assessments/TeacherAssessmentsPage';
import TeacherAssessmentDetailPage from '@/modules/teacher/assessments/TeacherAssessmentDetailPage';
import TeacherAssessmentCreatePage from '@/modules/teacher/assessments/TeacherAssessmentCreatePage';
import TeacherQuestionsPage from '@/modules/teacher/questions/TeacherQuestionsPage';
import TeacherResultsPage from '@/modules/teacher/results/TeacherResultsPage';
import TeacherAttemptDetailPage from '@/modules/teacher/results/TeacherAttemptDetailPage';
import TeacherDashboardPage from '@/modules/teacher/analytics/TeacherDashboardPage';
import TeacherStudentSemesterPerformancePage from '@/modules/teacher/analytics/TeacherStudentSemesterPerformancePage';
import TeacherLeaderboardsPage from '@/modules/teacher/analytics/TeacherLeaderboardsPage';

/* Student Pages */
import StudentDashboardPage from '@/modules/student/dashboard/StudentDashboardPage';
import StudentResultsPage from '@/modules/student/results/StudentResultsPage';
import StudentResultDetailPage from '@/modules/student/results/StudentResultDetailPage';
import AssessmentTakePage from '@/modules/student/take/AssessmentTakePage';

export const router = createBrowserRouter([
  /* ── Auth (no sidebar) ── */
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/reset-password', element: <ResetPasswordPage /> },
    ],
  },

  /* ── Assessment Taking (fullscreen, no chrome) ── */
  {
    path: '/take/:token',
    element: (
      <ProtectedRoute roles={['student']}>
        <AssessmentTakePage />
      </ProtectedRoute>
    ),
  },

  /* ── Admin ── */
  {
    element: (
      <ProtectedRoute roles={['admin']}>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/admin', element: <Navigate to="/admin/dashboard" replace /> },
      { path: '/admin/dashboard', element: <AdminDashboardPage /> },
      { path: '/admin/users', element: <AdminUsersPage /> },
      { path: '/admin/users/:id', element: <AdminUserDetailPage /> },
      { path: '/admin/groups', element: <AdminGroupsPage /> },
      { path: '/admin/groups/:id', element: <AdminGroupDetailPage /> },
      { path: '/admin/reports', element: <AdminReportsPage /> },
    ],
  },

  /* ── Teacher ── */
  {
    element: (
      <ProtectedRoute roles={['admin', 'teacher']}>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/teacher', element: <Navigate to="/teacher/dashboard" replace /> },
      { path: '/teacher/dashboard', element: <TeacherDashboardPage /> },
      { path: '/teacher/students/:id/semester-performance', element: <TeacherStudentSemesterPerformancePage /> },
      { path: '/teacher/leaderboards', element: <TeacherLeaderboardsPage /> },
      { path: '/teacher/assessments', element: <TeacherAssessmentsPage /> },
      { path: '/teacher/assessments/new', element: <TeacherAssessmentCreatePage /> },
      { path: '/teacher/assessments/:id', element: <TeacherAssessmentDetailPage /> },
      { path: '/teacher/assessments/:id/questions', element: <TeacherQuestionsPage /> },
      { path: '/teacher/assessments/:id/results', element: <TeacherResultsPage /> },
      { path: '/teacher/attempts/:id', element: <TeacherAttemptDetailPage /> },
    ],
  },

  /* ── Student ── */
  {
    element: (
      <ProtectedRoute roles={['student']}>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/student', element: <Navigate to="/student/dashboard" replace /> },
      { path: '/student/dashboard', element: <StudentDashboardPage /> },
      { path: '/student/results', element: <StudentResultsPage /> },
      { path: '/student/results/:id', element: <StudentResultDetailPage /> },
    ],
  },

  /* ── Root redirect ── */
  { path: '/', element: <Navigate to="/login" replace /> },
  { path: '*', element: <Navigate to="/login" replace /> },
]);
