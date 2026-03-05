import { Outlet } from 'react-router-dom';
import { useUIStore } from '@/app/store';
import Sidebar from './Sidebar';
import Navbar from './Navbar';
import styles from './AppLayout.module.scss';

export function AppLayout() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);

  return (
    <div className={`${styles.layout} ${sidebarOpen ? '' : styles.collapsed}`}>
      <Sidebar />
      <Navbar />
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;
