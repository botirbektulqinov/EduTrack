import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { FiLayers, FiPlus, FiSearch } from 'react-icons/fi';
import api from '@/lib/api';
import type { CurriculumTree, Group, PaginationMeta, User } from '@/types';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import EmptyState from '@/components/ui/EmptyState';
import Input from '@/components/ui/Input';
import Modal from '@/components/ui/Modal';
import Pagination from '@/components/ui/Pagination';
import Select from '@/components/ui/Select';
import Spinner from '@/components/ui/Spinner';
import Table from '@/components/ui/Table';
import styles from './AdminGroupsPage.module.scss';

const createGroupSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  subject_id: z.string().optional(),
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

  const { data, isLoading } = useQuery({
    queryKey: ['admin-groups', search, page],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, per_page: PER_PAGE };
      if (search) params.search = search;
      const res = await api.get('/admin/groups', { params });
      return res.data as { data: GroupListItem[]; meta?: PaginationMeta & { total_pages?: number } };
    },
  });

  const { data: teacherData } = useQuery({
    queryKey: ['admin-teachers'],
    queryFn: async () => {
      const res = await api.get('/admin/users', { params: { role: 'teacher', per_page: 100 } });
      return (res.data.data ?? res.data) as User[];
    },
    enabled: modalOpen,
  });

  const { data: curriculumData } = useQuery({
    queryKey: ['admin-curriculum-tree'],
    queryFn: async () => {
      const res = await api.get('/admin/curriculum/tree');
      return (res.data.data ?? res.data) as CurriculumTree;
    },
    enabled: modalOpen,
  });

  const groups = data?.data ?? [];
  const meta = data?.meta;
  const totalPages = meta?.total_pages ?? (meta ? Math.ceil(meta.total / meta.per_page) : 1);

  const teacherOptions = [
    { value: '', label: 'No teacher assigned' },
    ...(teacherData ?? []).map((teacher) => ({ value: teacher.id, label: teacher.full_name })),
  ];
  const subjectOptions = [
    { value: '', label: 'Use legacy subject text' },
    ...((curriculumData?.subjects ?? []).map((subject) => ({
      value: subject.id,
      label: subject.name,
    }))),
  ];

  const createMutation = useMutation({
    mutationFn: (payload: CreateGroupForm) => {
      const body = {
        ...payload,
        teacher_id: payload.teacher_id || undefined,
        subject_id: payload.subject_id || undefined,
        subject: payload.subject || undefined,
      };
      return api.post('/admin/groups', body);
    },
    onSuccess: () => {
      toast.success('Group created successfully');
      queryClient.invalidateQueries({ queryKey: ['admin-groups'] });
      queryClient.invalidateQueries({ queryKey: ['admin-curriculum-review-queue'] });
      setModalOpen(false);
      reset();
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Failed to create group';
      toast.error(message);
    },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateGroupForm>({
    resolver: zodResolver(createGroupSchema),
    defaultValues: {
      subject_id: '',
      subject: '',
      teacher_id: '',
    },
  });

  const onSubmit = (formData: CreateGroupForm) => createMutation.mutate(formData);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Groups</h1>
        <Button icon={<FiPlus />} onClick={() => setModalOpen(true)}>
          Create Group
        </Button>
      </div>

      <div className={styles.filters}>
        <div className={styles.searchWrap}>
          <FiSearch className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search groups..."
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

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
            {groups.map((group) => (
              <tr
                key={group.id}
                className={styles.row}
                onClick={() => navigate(`/admin/groups/${group.id}`)}
              >
                <td>{group.name}</td>
                <td>{group.subject_name ?? group.subject ?? '-'}</td>
                <td>{group.academic_year ?? '-'}</td>
                <td>{group.semester ?? '-'}</td>
                <td>{group.teacher_name ?? '-'}</td>
                <td>{group.student_count ?? '-'}</td>
                <td>
                  <Badge variant={group.is_archived ? 'neutral' : 'success'}>
                    {group.is_archived ? 'Archived' : 'Active'}
                  </Badge>
                </td>
              </tr>
            ))}
          </Table>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Create Group" size="md">
        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          <Input
            label="Group Name"
            placeholder="CS-101 Section A"
            error={errors.name?.message}
            {...register('name')}
          />
          <Select
            label="Curriculum Subject"
            options={subjectOptions}
            error={errors.subject_id?.message}
            {...register('subject_id')}
          />
          <Input
            label="Legacy Subject / Display Name"
            placeholder="Computer Science"
            helperText="Optional when a curriculum subject is selected."
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
