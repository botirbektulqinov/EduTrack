/* ─── Admin: User Detail Page ─── */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { FiArrowLeft, FiSave, FiUserX, FiUserCheck, FiLock } from 'react-icons/fi';
import api from '@/lib/api';
import { formatDate } from '@/lib/utils';
import type { User } from '@/types';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import ConfirmModal from '@/components/ui/ConfirmModal';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import styles from './AdminUserDetailPage.module.scss';

/* ── Schemas ── */
const updateUserSchema = z.object({
  full_name: z.string().min(2, 'Name is required'),
  email: z.string().email('Enter a valid email'),
  role: z.enum(['admin', 'teacher', 'student']),
  is_active: z.string(),
  student_id_number: z.string().optional(),
  employee_id: z.string().optional(),
  phone: z.string().optional(),
});

type UpdateUserForm = z.infer<typeof updateUserSchema>;

const resetPasswordSchema = z.object({
  new_password: z.string().min(6, 'Password must be at least 6 characters'),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

export default function AdminUserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [resetModalOpen, setResetModalOpen] = useState(false);

  /* ── Fetch user ── */
  const { data: user, isLoading } = useQuery({
    queryKey: ['admin-user', id],
    queryFn: async () => {
      const res = await api.get(`/admin/users/${id}`);
      return (res.data.data ?? res.data) as User;
    },
    enabled: !!id,
  });

  /* ── Edit Form ── */
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<UpdateUserForm>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(updateUserSchema) as any,
    values: user
      ? {
          full_name: user.full_name,
          email: user.email,
          role: user.role,
          is_active: String(user.is_active),
          student_id_number: user.student_id_number ?? '',
          employee_id: user.employee_id ?? '',
          phone: user.phone ?? '',
        }
      : undefined,
  });

  /* ── Reset Password Form ── */
  const {
    register: registerReset,
    handleSubmit: handleResetSubmit,
    reset: resetResetForm,
    formState: { errors: resetErrors },
  } = useForm<ResetPasswordForm>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(resetPasswordSchema) as any,
  });

  /* ── Update mutation ── */
  const updateMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.patch(`/admin/users/${id}`, payload),
    onSuccess: () => {
      toast.success('User updated');
      queryClient.invalidateQueries({ queryKey: ['admin-user', id] });
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setEditing(false);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Update failed';
      toast.error(msg);
    },
  });

  /* ── Deactivate mutation ── */
  const deactivateMutation = useMutation({
    mutationFn: () => api.delete(`/admin/users/${id}`),
    onSuccess: () => {
      toast.success('User deactivated');
      queryClient.invalidateQueries({ queryKey: ['admin-user', id] });
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: () => toast.error('Failed to deactivate user'),
  });

  /* ── Reactivate mutation ── */
  const reactivateMutation = useMutation({
    mutationFn: () => api.post(`/admin/users/${id}/reactivate`),
    onSuccess: () => {
      toast.success('User reactivated');
      queryClient.invalidateQueries({ queryKey: ['admin-user', id] });
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: () => toast.error('Failed to reactivate user'),
  });

  /* ── Reset password mutation ── */
  const resetPasswordMutation = useMutation({
    mutationFn: (newPassword: string) =>
      api.post(`/admin/users/${id}/reset-password`, { new_password: newPassword }),
    onSuccess: () => {
      toast.success('Password has been reset');
      setResetModalOpen(false);
      resetResetForm();
    },
    onError: () => toast.error('Failed to reset password'),
  });

  const onSubmit = (formData: UpdateUserForm) => {
    const payload: Record<string, unknown> = {
      full_name: formData.full_name,
      email: formData.email,
      role: formData.role,
      is_active: formData.is_active === 'true',
    };
    if (formData.student_id_number) payload.student_id_number = formData.student_id_number;
    if (formData.employee_id) payload.employee_id = formData.employee_id;
    if (formData.phone) payload.phone = formData.phone;
    updateMutation.mutate(payload);
  };

  const [deactivateConfirm, setDeactivateConfirm] = useState(false);
  const [reactivateConfirm, setReactivateConfirm] = useState(false);

  const handleDeactivate = () => setDeactivateConfirm(true);
  const handleReactivate = () => setReactivateConfirm(true);

  const onResetPassword = (formData: ResetPasswordForm) => {
    resetPasswordMutation.mutate(formData.new_password);
  };

  /* ── Loading ── */
  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className={styles.center}>
        <EmptyState
          title="User not found"
          description="The user you're looking for doesn't exist or has been removed."
        />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* Back button */}
      <button className={styles.back} onClick={() => navigate('/admin/users')}>
        <FiArrowLeft /> Back to Users
      </button>

      {/* User info card */}
      <Card
        title={user.full_name}
        actions={
          <div className={styles.cardActions}>
            <Badge variant={user.is_active ? 'success' : 'danger'}>
              {user.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <Badge
              variant={
                user.role === 'admin' ? 'info' : user.role === 'teacher' ? 'warning' : 'success'
              }
            >
              {user.role}
            </Badge>
          </div>
        }
      >
        <div className={styles.infoGrid}>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Email</span>
            <span className={styles.infoValue}>{user.email}</span>
          </div>
          {user.student_id_number && (
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Student ID</span>
              <span className={styles.infoValue}>{user.student_id_number}</span>
            </div>
          )}
          {user.employee_id && (
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Employee ID</span>
              <span className={styles.infoValue}>{user.employee_id}</span>
            </div>
          )}
          {user.phone && (
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Phone</span>
              <span className={styles.infoValue}>{user.phone}</span>
            </div>
          )}
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Created</span>
            <span className={styles.infoValue}>
              {formatDate(user.created_at)}
            </span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Updated</span>
            <span className={styles.infoValue}>
              {formatDate(user.updated_at)}
            </span>
          </div>
        </div>
      </Card>

      {/* Edit form */}
      <Card
        title="Edit User"
        actions={
          !editing ? (
            <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
              Edit
            </Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={() => { setEditing(false); reset(); }}>
              Cancel
            </Button>
          )
        }
      >
        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          <div className={styles.formGrid}>
            <Input
              label="Full Name"
              disabled={!editing}
              error={errors.full_name?.message}
              {...register('full_name')}
            />
            <Input
              label="Email"
              type="email"
              disabled={!editing}
              error={errors.email?.message}
              {...register('email')}
            />
            <Select
              label="Role"
              disabled={!editing}
              options={[
                { value: 'student', label: 'Student' },
                { value: 'teacher', label: 'Teacher' },
                { value: 'admin', label: 'Admin' },
              ]}
              error={errors.role?.message}
              {...register('role')}
            />
            <Select
              label="Status"
              disabled={!editing}
              options={[
                { value: 'true', label: 'Active' },
                { value: 'false', label: 'Inactive' },
              ]}
              error={errors.is_active?.message}
              {...register('is_active')}
            />
            <Input
              label="Student ID Number"
              disabled={!editing}
              placeholder="e.g. S12345"
              error={errors.student_id_number?.message}
              {...register('student_id_number')}
            />
            <Input
              label="Employee ID"
              disabled={!editing}
              placeholder="e.g. E001"
              error={errors.employee_id?.message}
              {...register('employee_id')}
            />
            <Input
              label="Phone"
              disabled={!editing}
              placeholder="+1234567890"
              error={errors.phone?.message}
              {...register('phone')}
            />
          </div>
          {editing && (
            <div className={styles.formActions}>
              <Button type="submit" icon={<FiSave />} loading={updateMutation.isPending}>
                Save Changes
              </Button>
            </div>
          )}
        </form>
      </Card>

      {/* Actions */}
      <Card title="Account Actions">
        <div className={styles.dangerZone}>
          <div className={styles.actionRow}>
            <div>
              <strong>Reset Password</strong>
              <p>Set a new password for this user.</p>
            </div>
            <Button
              variant="secondary"
              icon={<FiLock />}
              onClick={() => setResetModalOpen(true)}
            >
              Reset Password
            </Button>
          </div>

          <div className={styles.actionRow}>
            {user.is_active ? (
              <>
                <div>
                  <strong>Deactivate User</strong>
                  <p>Deactivating this user will prevent them from logging in.</p>
                </div>
                <Button
                  variant="danger"
                  icon={<FiUserX />}
                  loading={deactivateMutation.isPending}
                  onClick={handleDeactivate}
                >
                  Deactivate
                </Button>
              </>
            ) : (
              <>
                <div>
                  <strong>Reactivate User</strong>
                  <p>This user is currently inactive. Reactivate to restore access.</p>
                </div>
                <Button
                  variant="primary"
                  icon={<FiUserCheck />}
                  loading={reactivateMutation.isPending}
                  onClick={handleReactivate}
                >
                  Reactivate
                </Button>
              </>
            )}
          </div>
        </div>
      </Card>

      {/* Reset Password Modal */}
      <Modal
        isOpen={resetModalOpen}
        onClose={() => setResetModalOpen(false)}
        title="Reset Password"
        size="sm"
      >
        <form onSubmit={handleResetSubmit(onResetPassword)} className={styles.form}>
          <Input
            label="New Password"
            type="password"
            placeholder="Enter new password"
            error={resetErrors.new_password?.message}
            {...registerReset('new_password')}
          />
          <Input
            label="Confirm Password"
            type="password"
            placeholder="Confirm new password"
            error={resetErrors.confirm_password?.message}
            {...registerReset('confirm_password')}
          />
          <div className={styles.formActions}>
            <Button variant="secondary" type="button" onClick={() => setResetModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={resetPasswordMutation.isPending}>
              Reset Password
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        isOpen={deactivateConfirm}
        onClose={() => setDeactivateConfirm(false)}
        onConfirm={() => { deactivateMutation.mutate(); setDeactivateConfirm(false); }}
        title="Deactivate User"
        message="Are you sure you want to deactivate this user? They will no longer be able to sign in."
        confirmLabel="Deactivate"
        variant="danger"
      />

      <ConfirmModal
        isOpen={reactivateConfirm}
        onClose={() => setReactivateConfirm(false)}
        onConfirm={() => { reactivateMutation.mutate(); setReactivateConfirm(false); }}
        title="Reactivate User"
        message="Reactivate this user? They will be able to sign in again."
        confirmLabel="Reactivate"
        variant="primary"
      />
    </div>
  );
}
