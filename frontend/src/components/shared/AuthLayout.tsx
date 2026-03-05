import { Outlet } from 'react-router-dom';
import styles from './AuthLayout.module.scss';

export function AuthLayout() {
  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <div className={styles.logo}>
          <h1>EduTrack</h1>
        </div>
        <Outlet />
      </div>
    </div>
  );
}

export default AuthLayout;
