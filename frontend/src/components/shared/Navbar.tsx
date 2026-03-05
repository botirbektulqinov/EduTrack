import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { useAuthStore, useUIStore } from '@/app/store';
import api from '@/lib/api';
import { FiLogOut, FiSun, FiMoon, FiLock } from 'react-icons/fi';
import Modal from '@/components/ui/Modal';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import styles from './Navbar.module.scss';

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(6, 'New password must be at least 6 characters'),
    confirm_password: z.string().min(1, 'Please confirm your new password'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  });

type ChangePasswordForm = z.infer<typeof changePasswordSchema>;

export default function Navbar() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useUIStore();
  const [pwModalOpen, setPwModalOpen] = useState(false);
  const [pwLoading, setPwLoading] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ChangePasswordForm>({
    resolver: zodResolver(changePasswordSchema),
  });

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      /* proceed regardless */
    }
    logout();
    navigate('/login');
  };

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  const onChangePassword = async (data: ChangePasswordForm) => {
    setPwLoading(true);
    try {
      await api.post('/auth/change-password', {
        current_password: data.current_password,
        new_password: data.new_password,
      });
      toast.success('Password changed successfully');
      setPwModalOpen(false);
      reset();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Failed to change password';
      toast.error(msg);
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <>
      <header className={styles.navbar}>
        <div className={styles.left} />

        <div className={styles.right}>
          <button
            className={styles.iconBtn}
            onClick={toggleTheme}
            title="Toggle theme"
          >
            {theme === 'light' ? <FiMoon /> : <FiSun />}
          </button>

          {user && (
            <div className={styles.user}>
              <div className={styles.avatar}>
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <div className={styles.info}>
                <span className={styles.name}>{user.full_name}</span>
                <span className={styles.role}>{user.role}</span>
              </div>
            </div>
          )}

          <button
            className={styles.iconBtn}
            onClick={() => setPwModalOpen(true)}
            title="Change Password"
          >
            <FiLock />
          </button>

          <button
            className={styles.iconBtn}
            onClick={handleLogout}
            title="Logout"
          >
            <FiLogOut />
          </button>
        </div>
      </header>

      {/* Change Password Modal */}
      <Modal
        isOpen={pwModalOpen}
        onClose={() => { setPwModalOpen(false); reset(); }}
        title="Change Password"
        size="sm"
      >
        <form onSubmit={handleSubmit(onChangePassword)} className={styles.pwForm}>
          <Input
            label="Current Password"
            type="password"
            placeholder="••••••••"
            error={errors.current_password?.message}
            {...register('current_password')}
          />
          <Input
            label="New Password"
            type="password"
            placeholder="••••••••"
            error={errors.new_password?.message}
            {...register('new_password')}
          />
          <Input
            label="Confirm New Password"
            type="password"
            placeholder="••••••••"
            error={errors.confirm_password?.message}
            {...register('confirm_password')}
          />
          <div className={styles.pwActions}>
            <Button
              variant="secondary"
              type="button"
              onClick={() => { setPwModalOpen(false); reset(); }}
            >
              Cancel
            </Button>
            <Button type="submit" loading={pwLoading}>
              Change Password
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
