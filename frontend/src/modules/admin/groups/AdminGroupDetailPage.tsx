/* ─── Admin: Group Detail Page ─── */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { FiArrowLeft, FiSave, FiUserPlus, FiTrash2 } from 'react-icons/fi';
import api from '@/lib/api';
import type { User } from '@/types';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import Table from '@/components/ui/Table';
import Modal from '@/components/ui/Modal';
import ConfirmModal from '@/components/ui/ConfirmModal';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import styles from './AdminGroupDetailPage.module.scss';

/* ── Types ── */
interface GroupDetail {
  id: string;
  name: string;
  subject?: string;
  academic_year?: string;
  semester?: string;
  teacher_id?: string;
  teacher_name?: string;
  is_archived: boolean;
  student_count: number;
  created_at: string;
}

interface EnrolledStudent {
  id: string;
  full_name: string;
  email: string;
  student_id_number?: string;
  enrolled_at?: string;
}

/* ── Schemas ── */
const editGroupSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  subject: z.string().optional(),
  academic_year: z.string().optional(),
  semester: z.string().optional(),
  teacher_id: z.string().optional(),
});

type EditGroupForm = z.infer<typeof editGroupSchema>;

const enrollSchema = z.object({
  student_ids: z.string().min(1, 'Enter at least one student ID'),
});

type EnrollForm = z.infer<typeof enrollSchema>;

export default function AdminGroupDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [editing, setEditing] = useState(false);
  const [enrollModalOpen, setEnrollModalOpen] = useState(false);

  /* ── Fetch group detail ── */
  const { data: group, isLoading } = useQuery({
    queryKey: ['admin-group', id],
    queryFn: async () => {
      const res = await api.get(`/admin/groups/${id}`);
      return (res.data.data ?? res.data) as GroupDetail;
    },
    enabled: !!id,
  });

  /* ── Fetch enrolled students ── */
  const { data: students = [], isLoading: studentsLoading } = useQuery({
    queryKey: ['admin-group-students', id],
    queryFn: async () => {
      // Fetch enrollments by getting group members — use users endpoint filtered if available
      // Fallback: the group detail may include students or we fetch them separately
      try {
        const res = await api.get(`/admin/groups/${id}/students`);
        return (res.data.data ?? res.data) as EnrolledStudent[];
      } catch {
        return [] as EnrolledStudent[];
      }
    },
    enabled: !!id,
  });

  /* ── Fetch teachers for select ── */
  const { data: teacherData } = useQuery({
    queryKey: ['admin-teachers'],
    queryFn: async () => {
      const res = await api.get('/admin/users', { params: { role: 'teacher', per_page: 100 } });
      return (res.data.data ?? res.data) as User[];
    },
    enabled: editing,
  });

  const teacherOptions = [
    { value: '', label: 'No teacher assigned' },
    ...(teacherData ?? []).map((t) => ({ value: t.id, label: t.full_name })),
  ];

  /* ── Edit form ── */
  const {
    register: registerEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEdit,
    formState: { errors: editErrors },
  } = useForm<EditGroupForm>({
    resolver: zodResolver(editGroupSchema),
    values: group
      ? {
          name: group.name,
          subject: group.subject ?? '',
          academic_year: group.academic_year ?? '',
          semester: group.semester ?? '',
          teacher_id: group.teacher_id ?? '',
        }
      : undefined,
  });

  /* ── Enroll form ── */
  const {
    register: registerEnroll,
    handleSubmit: handleEnrollSubmit,
    reset: resetEnroll,
    formState: { errors: enrollErrors },
  } = useForm<EnrollForm>({
    resolver: zodResolver(enrollSchema),
  });

  /* ── Update group mutation ── */
  const updateMutation = useMutation({
    mutationFn: (payload: EditGroupForm) => {
      const body = { ...payload, teacher_id: payload.teacher_id || undefined };
      return api.patch(`/admin/groups/${id}`, body);
    },
    onSuccess: () => {
      toast.success('Group updated');
      queryClient.invalidateQueries({ queryKey: ['admin-group', id] });
      queryClient.invalidateQueries({ queryKey: ['admin-groups'] });
      setEditing(false);
    },
    onError: () => toast.error('Failed to update group'),
  });

  /* ── Enroll students mutation ── */
  const enrollMutation = useMutation({
    mutationFn: (studentIds: string[]) =>
      api.post(`/admin/groups/${id}/enroll`, { student_ids: studentIds }),
    onSuccess: () => {
      toast.success('Students enrolled');
      queryClient.invalidateQueries({ queryKey: ['admin-group', id] });
      queryClient.invalidateQueries({ queryKey: ['admin-group-students', id] });
      setEnrollModalOpen(false);
      resetEnroll();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Failed to enroll students';
      toast.error(msg);
    },
  });

  /* ── Remove student mutation ── */
  const removeMutation = useMutation({
    mutationFn: (studentId: string) =>
      api.delete(`/admin/groups/${id}/students/${studentId}`),
    onSuccess: () => {
      toast.success('Student removed');
      queryClient.invalidateQueries({ queryKey: ['admin-group', id] });
      queryClient.invalidateQueries({ queryKey: ['admin-group-students', id] });
    },
    onError: () => toast.error('Failed to remove student'),
  });

  const onEditSubmit = (formData: EditGroupForm) => updateMutation.mutate(formData);

  const onEnrollSubmit = (formData: EnrollForm) => {
    const ids = formData.student_ids.split(',').map((s) => s.trim()).filter(Boolean);
    enrollMutation.mutate(ids);
  };

  const [removeStudentId, setRemoveStudentId] = useState<string | null>(null);

  const handleRemoveStudent = (studentId: string) => {
    setRemoveStudentId(studentId);
  };

  /* ── Loading ── */
  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!group) {
    return (
      <div className={styles.center}>
        <p>Group not found.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* Back */}
      <button className={styles.back} onClick={() => navigate('/admin/groups')}>
        <FiArrowLeft /> Back to Groups
      </button>

      {/* Group info */}
      <Card
        title={group.name}
        actions={
          <Badge variant={group.is_archived ? 'neutral' : 'success'}>
            {group.is_archived ? 'Archived' : 'Active'}
          </Badge>
        }
      >
        <div className={styles.infoGrid}>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Subject</span>
            <span className={styles.infoValue}>{group.subject ?? '—'}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Academic Year</span>
            <span className={styles.infoValue}>{group.academic_year ?? '—'}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Semester</span>
            <span className={styles.infoValue}>{group.semester ?? '—'}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Teacher</span>
            <span className={styles.infoValue}>{group.teacher_name ?? '—'}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Students</span>
            <span className={styles.infoValue}>{group.student_count}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Created</span>
            <span className={styles.infoValue}>
              {new Date(group.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </Card>

      {/* Edit form */}
      <Card
        title="Edit Group"
        actions={
          !editing ? (
            <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
              Edit
            </Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={() => { setEditing(false); resetEdit(); }}>
              Cancel
            </Button>
          )
        }
      >
        <form onSubmit={handleEditSubmit(onEditSubmit)} className={styles.form}>
          <div className={styles.formGrid}>
            <Input
              label="Group Name"
              disabled={!editing}
              error={editErrors.name?.message}
              {...registerEdit('name')}
            />
            <Input
              label="Subject"
              disabled={!editing}
              error={editErrors.subject?.message}
              {...registerEdit('subject')}
            />
            <Input
              label="Academic Year"
              disabled={!editing}
              error={editErrors.academic_year?.message}
              {...registerEdit('academic_year')}
            />
            <Input
              label="Semester"
              disabled={!editing}
              error={editErrors.semester?.message}
              {...registerEdit('semester')}
            />
          </div>
          {editing && (
            <>
              <Select
                label="Teacher"
                options={teacherOptions}
                error={editErrors.teacher_id?.message}
                {...registerEdit('teacher_id')}
              />
              <div className={styles.formActions}>
                <Button type="submit" icon={<FiSave />} loading={updateMutation.isPending}>
                  Save Changes
                </Button>
              </div>
            </>
          )}
        </form>
      </Card>

      {/* Enrolled students */}
      <Card
        title="Enrolled Students"
        actions={
          <Button size="sm" icon={<FiUserPlus />} onClick={() => setEnrollModalOpen(true)}>
            Enroll Students
          </Button>
        }
      >
        {studentsLoading ? (
          <div className={styles.center}>
            <Spinner />
          </div>
        ) : students.length === 0 ? (
          <EmptyState title="No students enrolled" description="Enroll students to this group." />
        ) : (
          <Table headers={['Name', 'Email', 'Student ID', 'Actions']}>
            {students.map((s) => (
              <tr key={s.id}>
                <td>{s.full_name}</td>
                <td>{s.email}</td>
                <td>{s.student_id_number ?? '—'}</td>
                <td>
                  <Button
                    variant="danger"
                    size="sm"
                    icon={<FiTrash2 />}
                    onClick={() => handleRemoveStudent(s.id)}
                  >
                    Remove
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      {/* Enroll Modal */}
      <Modal
        isOpen={enrollModalOpen}
        onClose={() => setEnrollModalOpen(false)}
        title="Enroll Students"
        size="md"
      >
        <form onSubmit={handleEnrollSubmit(onEnrollSubmit)} className={styles.form}>
          <Input
            label="Student IDs"
            placeholder="Comma-separated student ID numbers (e.g. S1234, S5678)"
            helperText="Enter student ID numbers (not UUIDs), separated by commas."
            error={enrollErrors.student_ids?.message}
            {...registerEnroll('student_ids')}
          />
          <div className={styles.formActions}>
            <Button variant="secondary" type="button" onClick={() => setEnrollModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={enrollMutation.isPending}>
              Enroll
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        isOpen={!!removeStudentId}
        onClose={() => setRemoveStudentId(null)}
        onConfirm={() => { removeMutation.mutate(removeStudentId!); setRemoveStudentId(null); }}
        title="Remove Student"
        message="Remove this student from the group?"
        confirmLabel="Remove"
        variant="danger"
      />
    </div>
  );
}
