import { NavLink } from 'react-router-dom';
import { useAuthStore, useUIStore } from '@/app/store';
import type { UserRole } from '@/types';
import {
  FiHome,
  FiUsers,
  FiLayers,
  FiBarChart2,
  FiClipboard,
  FiAward,
  FiChevronsLeft,
  FiChevronsRight,
} from 'react-icons/fi';
import styles from './Sidebar.module.scss';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
}

const navByRole: Record<UserRole, NavItem[]> = {
  admin: [
    { to: '/admin', label: 'Dashboard', icon: <FiHome /> },
    { to: '/admin/users', label: 'Users', icon: <FiUsers /> },
    { to: '/admin/groups', label: 'Groups', icon: <FiLayers /> },
    { to: '/admin/reports', label: 'Reports', icon: <FiBarChart2 /> },
  ],
  teacher: [
    { to: '/teacher', label: 'Dashboard', icon: <FiHome /> },
    { to: '/teacher/assessments', label: 'Assessments', icon: <FiClipboard /> },
  ],
  student: [
    { to: '/student', label: 'Dashboard', icon: <FiHome /> },
    { to: '/student/results', label: 'Results', icon: <FiAward /> },
  ],
};

export default function Sidebar() {
  const user = useAuthStore((s) => s.user);
  const { sidebarOpen, toggleSidebar } = useUIStore();

  if (!user) return null;

  const items = navByRole[user.role] ?? [];

  return (
    <aside className={`${styles.sidebar} ${sidebarOpen ? '' : styles.collapsed}`}>
      <div className={styles.logo}>
        <span className={styles.logoIcon}>E</span>
        {sidebarOpen && <span className={styles.logoText}>EduTrack</span>}
      </div>

      <nav className={styles.nav}>
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === `/${user.role}`}
            className={({ isActive }) =>
              `${styles.link} ${isActive ? styles.active : ''}`
            }
          >
            <span className={styles.icon}>{item.icon}</span>
            {sidebarOpen && <span className={styles.label}>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <button className={styles.collapseBtn} onClick={toggleSidebar}>
        {sidebarOpen ? <FiChevronsLeft /> : <FiChevronsRight />}
      </button>
    </aside>
  );
}
