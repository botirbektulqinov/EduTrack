/* ─── Admin: Group Management Page ─── */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { FiPlus, FiSearch, FiLayers } from 'react-icons/fi';
import api from '@/lib/api';
import type { Group, User, PaginationMeta } from '@/types';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Table from '@/components/ui/Table';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import Pagination from '@/components/ui/Pagination';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import styles from './AdminGroupsPage.module.scss';

/* ── Zod schema ── */
const createGroupSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  subject: z.string().optional(),
  academic_year: z.string().optional(),
  semester: z.string().optional(),
  teacher_id: z.string().optional(),
});

type CreateGroupForm = z.infer<typeof createGroupSchema>;

interface GroupListItem extends Group {
  teacher_name?: string;
  student_count?: number;
}

const PER_PAGE = 20;

export default function AdminGroupsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);

  /* ── Fetch groups ── */
  const { data, isLoading } = useQuery({
    queryKey: ['admin-groups', search, page],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, per_page: PER_PAGE };
      if (search) params.search = search;
      const res = await api.get('/admin/groups', { params });
      return res.data as { data: GroupListItem[]; meta?: PaginationMeta & { total_pages?: number } };
    },
  });

  const groups = data?.data ?? [];
  const meta = data?.meta;
  const totalPages = meta?.total_pages ?? (meta ? Math.ceil(meta.total / meta.per_page) : 1);

  /* ── Fetch teachers for select ── */
  const { data: teacherData } = useQuery({
    queryKey: ['admin-teachers'],
    queryFn: async () => {
      const res = await api.get('/admin/users', { params: { role: 'teacher', per_page: 100 } });
      return (res.data.data ?? res.data) as User[];
    },
    enabled: modalOpen,
  });

  const teacherOptions = [
    { value: '', label: 'No teacher assigned' },
    ...(teacherData ?? []).map((t) => ({ value: t.id, label: t.full_name })),
  ];

  /* ── Create group mutation ── */
  const createMutation = useMutation({
    mutationFn: (payload: CreateGroupForm) => {
      const body = {
        ...payload,
        teacher_id: payload.teacher_id || undefined,
      };
      return api.post('/admin/groups', body);
    },
    onSuccess: () => {
      toast.success('Group created successfully');
      queryClient.invalidateQueries({ queryKey: ['admin-groups'] });
      setModalOpen(false);
      reset();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Failed to create group';
      toast.error(msg);
    },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateGroupForm>({
    resolver: zodResolver(createGroupSchema),
  });

  const onSubmit = (formData: CreateGroupForm) => createMutation.mutate(formData);

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.title}>Groups</h1>
        <Button icon={<FiPlus />} onClick={() => setModalOpen(true)}>
          Create Group
        </Button>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.searchWrap}>
          <FiSearch className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search groups…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className={styles.center}>
          <Spinner size="lg" />
        </div>
      ) : groups.length === 0 ? (
        <EmptyState
          icon={<FiLayers size={40} />}
          title="No groups found"
          description="Create a group to get started."
        />
      ) : (
        <>
          <Table headers={['Name', 'Subject', 'Year', 'Semester', 'Teacher', 'Students', 'Status']}>
            {groups.map((g) => (
              <tr
                key={g.id}
                className={styles.row}
                onClick={() => navigate(`/admin/groups/${g.id}`)}
              >
                <td>{g.name}</td>
                <td>{g.subject ?? '—'}</td>
                <td>{g.academic_year ?? '—'}</td>
                <td>{g.semester ?? '—'}</td>
                <td>{g.teacher_name ?? '—'}</td>
                <td>{g.student_count ?? '—'}</td>
                <td>
                  <Badge variant={g.is_archived ? 'neutral' : 'success'}>
                    {g.is_archived ? 'Archived' : 'Active'}
                  </Badge>
                </td>
              </tr>
            ))}
          </Table>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {/* Create Group Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Create Group" size="md">
        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          <Input
            label="Group Name"
            placeholder="CS-101 Section A"
            error={errors.name?.message}
            {...register('name')}
          />
          <Input
            label="Subject"
            placeholder="Computer Science"
            error={errors.subject?.message}
            {...register('subject')}
          />
          <div className={styles.formRow}>
            <Input
              label="Academic Year"
              placeholder="2025-2026"
              error={errors.academic_year?.message}
              {...register('academic_year')}
            />
            <Input
              label="Semester"
              placeholder="Fall"
              error={errors.semester?.message}
              {...register('semester')}
            />
          </div>
          <Select
            label="Teacher"
            options={teacherOptions}
            error={errors.teacher_id?.message}
            {...register('teacher_id')}
          />
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
    </div>
  );
}
