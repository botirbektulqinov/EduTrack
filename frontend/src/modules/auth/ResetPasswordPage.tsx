/* ─── Reset Password Page ─── */
import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import api from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import styles from './ResetPasswordPage.module.scss';

const schema = z
  .object({
    password: z.string().min(8, 'Minimum 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type ResetForm = z.infer<typeof schema>;

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetForm>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: ResetForm) => {
    if (!token) {
      toast.error('Invalid or missing reset token');
      return;
    }
    setLoading(true);
    try {
      await api.post('/auth/reset-password', {
        token,
        new_password: data.password,
      });
      toast.success('Password reset successfully');
      navigate('/login');
    } catch {
      toast.error('Failed to reset password. The link may have expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <h2 className={styles.title}>Reset Password</h2>
      <p className={styles.subtitle}>Enter your new password below</p>

      <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
        <Input
          label="New Password"
          type="password"
          placeholder="••••••••"
          error={errors.password?.message}
          {...register('password')}
        />
        <Input
          label="Confirm Password"
          type="password"
          placeholder="••••••••"
          error={errors.confirmPassword?.message}
          {...register('confirmPassword')}
        />
        <Button type="submit" variant="primary" loading={loading} style={{ width: '100%' }}>
          Reset Password
        </Button>
      </form>

      <div className={styles.footer}>
        <Link to="/login">Back to Sign In</Link>
      </div>
    </div>
  );
}
