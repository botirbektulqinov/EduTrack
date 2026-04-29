import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { useAuthStore } from '@/app/store';
import { ProtectedRoute } from './ProtectedRoute';

const teacherUser = {
  id: 'teacher-1',
  email: 'teacher@example.edu',
  full_name: 'Teacher One',
  role: 'teacher' as const,
  is_active: true,
  extra_time_factor: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    });
  });

  it('redirects unauthenticated users to login', async () => {
    render(
      <MemoryRouter initialEntries={['/student/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/student/dashboard"
            element={
              <ProtectedRoute roles={['student']}>
                <div>Student Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Login Page')).toBeInTheDocument();
  });

  it('redirects authenticated users with the wrong role to their dashboard', async () => {
    useAuthStore.setState({
      user: teacherUser,
      accessToken: 'access',
      refreshToken: 'refresh',
      isAuthenticated: true,
    });

    render(
      <MemoryRouter initialEntries={['/student/dashboard']}>
        <Routes>
          <Route path="/teacher" element={<div>Teacher Home</div>} />
          <Route
            path="/student/dashboard"
            element={
              <ProtectedRoute roles={['student']}>
                <div>Student Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Teacher Home')).toBeInTheDocument();
  });
});
