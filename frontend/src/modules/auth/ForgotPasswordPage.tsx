/* ─── Forgot Password Page ─── */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import api from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import styles from './ForgotPasswordPage.module.scss';

const schema = z.object({
  email: z.string().email('Enter a valid email'),
});

type ForgotForm = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotForm>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: ForgotForm) => {
    setLoading(true);
    try {
      await api.post('/auth/forgot-password', data);
      setSent(true);
      toast.success('Password reset email sent');
    } catch {
      toast.error('Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className={styles.wrapper}>
        <h2 className={styles.title}>Check Your Email</h2>
        <p className={styles.subtitle}>
          We've sent a password reset link to your email address. Please check your inbox.
        </p>
        <Link to="/login" className={styles.backLink}>
          Back to Sign In
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <h2 className={styles.title}>Forgot Password</h2>
      <p className={styles.subtitle}>Enter your email and we'll send you a reset link</p>

      <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
        <Input
          label="Email"
          type="email"
          placeholder="you@university.edu"
          error={errors.email?.message}
          {...register('email')}
        />
        <Button type="submit" variant="primary" loading={loading} style={{ width: '100%' }}>
          Send Reset Link
        </Button>
      </form>

      <div className={styles.footer}>
        <Link to="/login">Back to Sign In</Link>
      </div>
    </div>
  );
}
