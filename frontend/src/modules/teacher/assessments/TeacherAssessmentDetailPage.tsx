import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import {
  FiArrowLeft,
  FiCopy,
  FiEdit2,
  FiSave,
  FiX,
  FiList,
  FiBarChart2,
  FiTrash2,
} from 'react-icons/fi';
import api from '@/lib/api';
import type { Assessment } from '@/types';
import { formatDateTime } from '@/lib/utils';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Textarea from '@/components/ui/Textarea';
import Spinner from '@/components/ui/Spinner';
import ConfirmModal from '@/components/ui/ConfirmModal';
import styles from './TeacherAssessmentDetailPage.module.scss';

interface TeacherGroupOption {
  id: string;
  name: string;
  subject_id?: string | null;
  subject_name?: string | null;
}

interface CurriculumSubjectOption {
  id: string;
  name: string;
  code?: string | null;
}

const editSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  assessment_type: z.enum(['test', 'quiz', 'survey', 'practice']),
  subject_id: z.string().min(1, 'Subject is required'),
  group_id: z.string().optional(),
  time_limit_minutes: z.coerce.number().positive().optional(),
  available_from: z.string().optional(),
  available_until: z.string().optional(),
  max_attempts: z.coerce.number().int().positive(),
  passing_score: z.coerce.number().min(0).max(100),
  shuffle_questions: z.boolean(),
  shuffle_options: z.boolean(),
  max_violations: z.coerce.number().int().min(0),
  time_penalty_minutes: z.coerce.number().int().min(0),
  enforce_fullscreen: z.boolean(),
  block_keyboard_shortcuts: z.boolean(),
  tab_switch_detection: z.boolean(),
  devtools_detection: z.boolean(),
  right_click_block: z.boolean(),
  copy_paste_block: z.boolean(),
});

type EditForm = z.input<typeof editSchema>;
type EditFormOutput = z.output<typeof editSchema>;

const TYPE_OPTIONS = [
  { value: 'test', label: 'Test' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'survey', label: 'Survey' },
  { value: 'practice', label: 'Practice' },
];

function toDateTimeInputValue(value?: string | null): string {
  if (!value) {
    return '';
  }
  return value.slice(0, 16);
}

export default function TeacherAssessmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  const { data: assessment, isLoading } = useQuery({
    queryKey: ['teacher', 'assessment', id],
    queryFn: async () => {
      const res = await api.get(`/teacher/assessments/${id}`);
      return (res.data.data ?? res.data) as Assessment;
    },
    enabled: Boolean(id),
  });

  const { data: groups } = useQuery({
    queryKey: ['teacher', 'groups'],
    queryFn: async () => {
      const res = await api.get('/teacher/assessments/groups');
      return (res.data.data ?? res.data) as TeacherGroupOption[];
    },
    enabled: editing,
  });

  const { data: subjects } = useQuery({
    queryKey: ['teacher', 'assessment-subjects'],
    queryFn: async () => {
      const res = await api.get('/teacher/assessments/subjects');
      return (res.data.data ?? res.data) as CurriculumSubjectOption[];
    },
    enabled: editing,
  });

  const groupOptions = [
    { value: '', label: 'No group' },
    ...(groups ?? []).map((group) => ({
      value: group.id,
      label: `${group.name}${group.subject_name ? ` - ${group.subject_name}` : ''}`,
    })),
  ];
  const subjectOptions = [
    { value: '', label: 'Select a subject...' },
    ...(subjects ?? []).map((subject) => ({
      value: subject.id,
      label: subject.code ? `${subject.code} - ${subject.name}` : subject.name,
    })),
  ];

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    formState: { errors },
  } = useForm<EditForm, unknown, EditFormOutput>({
    resolver: zodResolver(editSchema),
  });

  useEffect(() => {
    if (!assessment) {
      return;
    }
    reset({
      title: assessment.title,
      description: assessment.description ?? '',
      assessment_type: assessment.assessment_type,
      subject_id: assessment.subject_id ?? assessment.group_subject_id ?? '',
      group_id: assessment.group_id ?? '',
      time_limit_minutes: assessment.time_limit_minutes ?? undefined,
      available_from: toDateTimeInputValue(assessment.available_from),
      available_until: toDateTimeInputValue(assessment.available_until),
      max_attempts: assessment.max_attempts,
      passing_score: assessment.passing_score,
      shuffle_questions: assessment.shuffle_questions,
      shuffle_options: assessment.shuffle_options,
      max_violations: assessment.max_violations,
      time_penalty_minutes: assessment.time_penalty_minutes ?? 2,
      enforce_fullscreen: assessment.enforce_fullscreen,
      block_keyboard_shortcuts: assessment.block_keyboard_shortcuts,
      tab_switch_detection: assessment.tab_switch_detection,
      devtools_detection: assessment.devtools_detection,
      right_click_block: assessment.right_click_block,
      copy_paste_block: assessment.copy_paste_block,
    });
  }, [assessment, reset]);

  const selectedGroupId = useWatch({ control, name: 'group_id' }) ?? '';
  const selectedGroup = (groups ?? []).find((group) => group.id === selectedGroupId) ?? null;
  const lockedSubjectId = selectedGroup?.subject_id ?? '';

  useEffect(() => {
    if (lockedSubjectId) {
      setValue('subject_id', lockedSubjectId, { shouldDirty: true, shouldValidate: true });
    }
  }, [lockedSubjectId, setValue]);

  const updateMutation = useMutation({
    mutationFn: (payload: EditFormOutput) => {
      const body = {
        title: payload.title,
        description: payload.description || undefined,
        assessment_type: payload.assessment_type,
        group_id: payload.group_id || undefined,
        subject_id: payload.subject_id || undefined,
        time_limit_minutes: payload.time_limit_minutes || undefined,
        available_from: payload.available_from || undefined,
        available_until: payload.available_until || undefined,
        max_attempts: payload.max_attempts,
        passing_score: payload.passing_score,
        shuffle_questions: payload.shuffle_questions,
        shuffle_options: payload.shuffle_options,
        proctoring: {
          enforce_fullscreen: payload.enforce_fullscreen,
          max_violations: payload.max_violations,
          time_penalty_minutes: payload.time_penalty_minutes,
          block_keyboard_shortcuts: payload.block_keyboard_shortcuts,
          tab_switch_detection: payload.tab_switch_detection,
          devtools_detection: payload.devtools_detection,
          right_click_block: payload.right_click_block,
          copy_paste_block: payload.copy_paste_block,
          webcam_proctoring: assessment?.webcam_proctoring ?? false,
        },
      };
      return api.patch(`/teacher/assessments/${id}`, body);
    },
    onSuccess: () => {
      toast.success('Assessment updated');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessments'] });
      setEditing(false);
    },
    onError: () => toast.error('Failed to update assessment'),
  });

  const publishMutation = useMutation({
    mutationFn: () => api.post(`/teacher/assessments/${id}/publish`),
    onSuccess: () => {
      toast.success('Assessment published');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessments'] });
    },
    onError: () => toast.error('Failed to publish'),
  });

  const unpublishMutation = useMutation({
    mutationFn: () => api.post(`/teacher/assessments/${id}/unpublish`),
    onSuccess: () => {
      toast.success('Assessment unpublished');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessments'] });
    },
    onError: () => toast.error('Failed to unpublish'),
  });

  const deactivateMutation = useMutation({
    mutationFn: () => api.post(`/teacher/assessments/${id}/deactivate`),
    onSuccess: () => {
      toast.success('Assessment deactivated');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessments'] });
    },
    onError: () => toast.error('Failed to deactivate'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/teacher/assessments/${id}`),
    onSuccess: () => {
      toast.success('Assessment deleted');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessments'] });
      navigate('/teacher/assessments');
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Failed to delete assessment';
      toast.error(msg);
    },
  });

  const onEditSubmit = (formData: EditFormOutput) => updateMutation.mutate(formData);

  const handleCopyLink = () => {
    if (!assessment?.access_token) {
      return;
    }
    const link = `${window.location.origin}/take/${assessment.access_token}`;
    navigator.clipboard.writeText(link).then(() => toast.success('Link copied'));
  };

  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className={styles.page}>
        <Link to="/teacher/assessments" className={styles.backLink}>
          <FiArrowLeft /> Back
        </Link>
        <p>Assessment not found.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Link to="/teacher/assessments" className={styles.backLink}>
        <FiArrowLeft /> Back to Assessments
      </Link>

      <div className={styles.header}>
        <div>
          <h1>{assessment.title}</h1>
          <div className={styles.badges}>
            <Badge variant={assessment.is_published ? 'success' : 'neutral'}>
              {assessment.is_published ? 'Published' : 'Draft'}
            </Badge>
            <Badge variant={assessment.is_active ? 'success' : 'danger'}>
              {assessment.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </div>
        </div>
        <div className={styles.actions}>
          {!editing && (
            <Button variant="secondary" icon={<FiEdit2 />} onClick={() => setEditing(true)}>
              Edit
            </Button>
          )}
          {assessment.is_published ? (
            <Button variant="ghost" loading={unpublishMutation.isPending} onClick={() => unpublishMutation.mutate()}>
              Unpublish
            </Button>
          ) : (
            <Button loading={publishMutation.isPending} onClick={() => publishMutation.mutate()}>
              Publish
            </Button>
          )}
          {assessment.is_active && (
            <Button variant="danger" loading={deactivateMutation.isPending} onClick={() => deactivateMutation.mutate()}>
              Deactivate
            </Button>
          )}
          {!assessment.is_published && (
            <Button
              variant="danger"
              icon={<FiTrash2 />}
              loading={deleteMutation.isPending}
              onClick={() => setDeleteConfirmOpen(true)}
            >
              Delete
            </Button>
          )}
        </div>
      </div>

      <Card title="Assessment Details">
        {editing ? (
          <form className={styles.editForm} onSubmit={handleSubmit(onEditSubmit)}>
            <div className={styles.formGrid}>
              <Input label="Title" {...register('title')} error={errors.title?.message} />
              <Select
                label="Type"
                options={TYPE_OPTIONS}
                {...register('assessment_type')}
                error={errors.assessment_type?.message}
              />
              <Select
                label="Subject"
                options={subjectOptions}
                {...register('subject_id')}
                disabled={Boolean(lockedSubjectId)}
                error={errors.subject_id?.message}
              />
              <Select label="Group" options={groupOptions} {...register('group_id')} error={errors.group_id?.message} />
              <Input
                label="Time Limit (minutes)"
                type="number"
                {...register('time_limit_minutes')}
                error={errors.time_limit_minutes?.message}
              />
              <Input label="Max Attempts" type="number" {...register('max_attempts')} error={errors.max_attempts?.message} />
              <Input
                label="Passing Score (%)"
                type="number"
                {...register('passing_score')}
                error={errors.passing_score?.message}
              />
              <Input
                label="Max Violations"
                type="number"
                {...register('max_violations')}
                error={errors.max_violations?.message}
              />
              <Input
                label="Time Penalty (minutes)"
                type="number"
                {...register('time_penalty_minutes')}
                error={errors.time_penalty_minutes?.message}
              />
              <Input label="Available From" type="datetime-local" {...register('available_from')} />
              <Input label="Available Until" type="datetime-local" {...register('available_until')} />
            </div>
            <Textarea label="Description" {...register('description')} />
            <p className={styles.helperText}>
              {selectedGroup
                ? lockedSubjectId
                  ? `The selected group is mapped to ${selectedGroup.subject_name ?? 'a curriculum subject'}, so the assessment subject is locked to that subject.`
                  : 'This group does not have a curriculum subject yet, so choose the assessment subject directly.'
                : 'Assessments can stay ungrouped, but they still must be attached to a subject.'}
            </p>
            <div className={styles.checkboxGroup}>
              <label>
                <input type="checkbox" {...register('shuffle_questions')} />
                Shuffle Questions
              </label>
              <label>
                <input type="checkbox" {...register('shuffle_options')} />
                Shuffle Options
              </label>
              <label>
                <input type="checkbox" {...register('enforce_fullscreen')} />
                Enforce Fullscreen
              </label>
              <label>
                <input type="checkbox" {...register('block_keyboard_shortcuts')} />
                Block Keyboard Shortcuts
              </label>
              <label>
                <input type="checkbox" {...register('tab_switch_detection')} />
                Detect Tab Switching
              </label>
              <label>
                <input type="checkbox" {...register('devtools_detection')} />
                Detect DevTools
              </label>
              <label>
                <input type="checkbox" {...register('right_click_block')} />
                Block Right-Click
              </label>
              <label>
                <input type="checkbox" {...register('copy_paste_block')} />
                Block Copy/Paste
              </label>
            </div>
            <div className={styles.formActions}>
              <Button
                variant="secondary"
                icon={<FiX />}
                type="button"
                onClick={() => {
                  setEditing(false);
                  reset();
                }}
              >
                Cancel
              </Button>
              <Button icon={<FiSave />} type="submit" loading={updateMutation.isPending}>
                Save
              </Button>
            </div>
          </form>
        ) : (
          <div className={styles.infoGrid}>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Type</span>
              <span className={styles.infoValue}>{assessment.assessment_type}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Subject</span>
              <span className={styles.infoValue}>{assessment.subject_name ?? '—'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Group</span>
              <span className={styles.infoValue}>{assessment.group_name ?? '—'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Time Limit</span>
              <span className={styles.infoValue}>
                {assessment.time_limit_minutes ? `${assessment.time_limit_minutes} min` : '—'}
              </span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Max Attempts</span>
              <span className={styles.infoValue}>{assessment.max_attempts}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Passing Score</span>
              <span className={styles.infoValue}>{assessment.passing_score}%</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Max Violations</span>
              <span className={styles.infoValue}>{assessment.max_violations}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Time Penalty</span>
              <span className={styles.infoValue}>
                {assessment.time_penalty_minutes ? `${assessment.time_penalty_minutes} min` : '—'}
              </span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Available From</span>
              <span className={styles.infoValue}>
                {assessment.available_from ? formatDateTime(assessment.available_from) : '—'}
              </span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Available Until</span>
              <span className={styles.infoValue}>
                {assessment.available_until ? formatDateTime(assessment.available_until) : '—'}
              </span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Shuffle Questions</span>
              <span className={styles.infoValue}>{assessment.shuffle_questions ? 'Yes' : 'No'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Shuffle Options</span>
              <span className={styles.infoValue}>{assessment.shuffle_options ? 'Yes' : 'No'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Enforce Fullscreen</span>
              <span className={styles.infoValue}>{assessment.enforce_fullscreen ? 'Yes' : 'No'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Block Keyboard Shortcuts</span>
              <span className={styles.infoValue}>{assessment.block_keyboard_shortcuts ? 'Yes' : 'No'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Detect Tab Switching</span>
              <span className={styles.infoValue}>{assessment.tab_switch_detection ? 'Yes' : 'No'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Detect DevTools</span>
              <span className={styles.infoValue}>{assessment.devtools_detection ? 'Yes' : 'No'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Block Right-Click</span>
              <span className={styles.infoValue}>{assessment.right_click_block ? 'Yes' : 'No'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Block Copy/Paste</span>
              <span className={styles.infoValue}>{assessment.copy_paste_block ? 'Yes' : 'No'}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Score Release</span>
              <span className={styles.infoValue}>{assessment.score_release_policy}</span>
            </div>
            {assessment.description && (
              <div className={`${styles.infoItem} ${styles.fullWidth}`}>
                <span className={styles.infoLabel}>Description</span>
                <span className={styles.infoValue}>{assessment.description}</span>
              </div>
            )}
          </div>
        )}
      </Card>

      {assessment.is_published && assessment.access_token && (
        <Card title="Access Link">
          <div className={styles.linkBox}>
            <code className={styles.linkText}>
              {window.location.origin}/take/{assessment.access_token}
            </code>
            <Button variant="secondary" icon={<FiCopy />} onClick={handleCopyLink}>
              Copy
            </Button>
          </div>
        </Card>
      )}

      <div className={styles.section}>
        <Link to={`/teacher/assessments/${id}/questions`}>
          <Button variant="secondary" icon={<FiList />}>
            Manage Questions
          </Button>
        </Link>
        <Link to={`/teacher/assessments/${id}/results`}>
          <Button variant="secondary" icon={<FiBarChart2 />}>
            View Results
          </Button>
        </Link>
      </div>

      <ConfirmModal
        isOpen={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        onConfirm={() => deleteMutation.mutate()}
        title="Delete Assessment"
        message="Are you sure you want to delete this assessment? This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
