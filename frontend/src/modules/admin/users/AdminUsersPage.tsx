/* ─── Admin: User Management Page ─── */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { FiPlus, FiSearch, FiUsers, FiUpload } from 'react-icons/fi';
import api from '@/lib/api';
import { formatDate } from '@/lib/utils';
import type { User, UserRole, PaginationMeta } from '@/types';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Table from '@/components/ui/Table';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import Textarea from '@/components/ui/Textarea';
import Pagination from '@/components/ui/Pagination';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import styles from './AdminUsersPage.module.scss';

/* ── Zod schema ── */
const createUserSchema = z.object({
  full_name: z.string().min(2, 'Name is required'),
  email: z.string().email('Enter a valid email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  role: z.enum(['admin', 'teacher', 'student']),
  student_id_number: z.string().optional(),
  employee_id: z.string().optional(),
});

type CreateUserForm = z.infer<typeof createUserSchema>;

/* ── Helpers ── */
const roleBadgeVariant = (role: UserRole) => {
  const map = { admin: 'info', teacher: 'warning', student: 'success' } as const;
  return map[role] ?? 'neutral';
};

const statusBadgeVariant = (active: boolean) => (active ? 'success' : 'danger');

const PER_PAGE = 20;

export default function AdminUsersPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  /* ── Local state ── */
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [bulkJson, setBulkJson] = useState('');

  /* ── Fetch users ── */
  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', search, roleFilter, page],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, per_page: PER_PAGE };
      if (search) params.search = search;
      if (roleFilter) params.role = roleFilter;
      const res = await api.get('/admin/users', { params });
      return res.data as { data: User[]; meta?: PaginationMeta & { total_pages?: number } };
    },
  });

  const users = data?.data ?? [];
  const meta = data?.meta;
  const totalPages = meta?.total_pages ?? (meta ? Math.ceil(meta.total / meta.per_page) : 1);

  /* ── Create user mutation ── */
  const createMutation = useMutation({
    mutationFn: (payload: CreateUserForm) => api.post('/admin/users', payload),
    onSuccess: () => {
      toast.success('User created successfully');
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setModalOpen(false);
      reset();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Failed to create user';
      toast.error(msg);
    },
  });

  /* ── Bulk import mutation ── */
  const bulkImportMutation = useMutation({
    mutationFn: (users: Record<string, unknown>[]) =>
      api.post('/admin/users/bulk-import', { users }),
    onSuccess: (res) => {
      const count = (res.data?.data as unknown[])?.length ?? 0;
      toast.success(`Successfully imported ${count} user(s)`);
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setBulkModalOpen(false);
      setBulkJson('');
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Bulk import failed';
      toast.error(msg);
    },
  });

  const handleBulkImport = () => {
    try {
      const parsed = JSON.parse(bulkJson);
      const users = Array.isArray(parsed) ? parsed : parsed.users;
      if (!Array.isArray(users) || users.length === 0) {
        toast.error('Provide a JSON array of users');
        return;
      }
      bulkImportMutation.mutate(users);
    } catch {
      toast.error('Invalid JSON format');
    }
  };

  /* ── Form ── */
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { role: 'student' },
  });

  const watchedRole = useWatch({ control, name: 'role' });

  const onSubmit = (formData: CreateUserForm) => createMutation.mutate(formData);

  /* ── Render ── */
  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.title}>Users</h1>
        <div className={styles.headerActions}>
          <Button variant="secondary" icon={<FiUpload />} onClick={() => setBulkModalOpen(true)}>
            Bulk Import
          </Button>
          <Button icon={<FiPlus />} onClick={() => setModalOpen(true)}>
            Create User
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.searchWrap}>
          <FiSearch className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          options={[
            { value: '', label: 'All Roles' },
            { value: 'admin', label: 'Admin' },
            { value: 'teacher', label: 'Teacher' },
            { value: 'student', label: 'Student' },
          ]}
          value={roleFilter}
          onChange={(e) => {
            setRoleFilter(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className={styles.center}>
          <Spinner size="lg" />
        </div>
      ) : users.length === 0 ? (
        <EmptyState
          icon={<FiUsers size={40} />}
          title="No users found"
          description="Try adjusting your search or filters."
        />
      ) : (
        <>
          <Table headers={['Name', 'Email', 'Role', 'Status', 'Created']}>
            {users.map((u) => (
              <tr
                key={u.id}
                className={styles.row}
                onClick={() => navigate(`/admin/users/${u.id}`)}
              >
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <Badge variant={roleBadgeVariant(u.role)}>{u.role}</Badge>
                </td>
                <td>
                  <Badge variant={statusBadgeVariant(u.is_active)}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </td>
                <td>{formatDate(u.created_at)}</td>
              </tr>
            ))}
          </Table>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {/* Create User Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Create User" size="md">
        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          <Input
            label="Full Name"
            placeholder="John Doe"
            error={errors.full_name?.message}
            {...register('full_name')}
          />
          <Input
            label="Email"
            type="email"
            placeholder="user@university.edu"
            error={errors.email?.message}
            {...register('email')}
          />
          <Select
            label="Role"
            options={[
              { value: 'student', label: 'Student' },
              { value: 'teacher', label: 'Teacher' },
              { value: 'admin', label: 'Admin' },
            ]}
            error={errors.role?.message}
            {...register('role')}
          />
          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            error={errors.password?.message}
            {...register('password')}
          />
          {watchedRole === 'student' && (
            <Input
              label="Student ID"
              placeholder="S12345"
              error={errors.student_id_number?.message}
              {...register('student_id_number')}
            />
          )}
          {(watchedRole === 'teacher' || watchedRole === 'admin') && (
            <Input
              label="Employee ID"
              placeholder="E12345"
              error={errors.employee_id?.message}
              {...register('employee_id')}
            />
          )}
          <div className={styles.formActions}>
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={createMutation.isPending}>
              Create
            </Button>
          </div>
        </form>
      </Modal>

      {/* Bulk Import Modal */}
      <Modal isOpen={bulkModalOpen} onClose={() => setBulkModalOpen(false)} title="Bulk Import Users" size="md">
        <div className={styles.form}>
          <p className={styles.bulkHint}>
            Paste a JSON array of users. Each user needs: <code>email</code>, <code>full_name</code>, <code>role</code>, <code>password</code>.
            Optional: <code>student_id_number</code>, <code>employee_id</code>.
          </p>
          <Textarea
            label="Users JSON"
            rows={10}
            placeholder={`[\n  {\n    "email": "user1@university.edu",\n    "full_name": "User One",\n    "role": "student",\n    "password": "Pass123!",\n    "student_id_number": "S001"\n  }\n]`}
            value={bulkJson}
            onChange={(e) => setBulkJson(e.target.value)}
          />
          <div className={styles.formActions}>
            <Button variant="secondary" onClick={() => setBulkModalOpen(false)}>
              Cancel
            </Button>
            <Button
              icon={<FiUpload />}
              loading={bulkImportMutation.isPending}
              onClick={handleBulkImport}
            >
              Import
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
