import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/app/store';
import type { UserRole } from '@/types';
import type { ReactNode } from 'react';

interface ProtectedRouteProps {
  roles: UserRole[];
  children: ReactNode;
}

const roleDashboard: Record<UserRole, string> = {
  admin: '/admin',
  teacher: '/teacher',
  student: '/student',
};

export function ProtectedRoute({ roles, children }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!roles.includes(user.role)) {
    return <Navigate to={roleDashboard[user.role]} replace />;
  }

  return <>{children}</>;
}

export default ProtectedRoute;
