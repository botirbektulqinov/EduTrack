import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { FiArrowLeft } from 'react-icons/fi';
import api from '@/lib/api';
import type { Assessment, AssessmentCreate } from '@/types';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Textarea from '@/components/ui/Textarea';
import Card from '@/components/ui/Card';
import styles from './TeacherAssessmentCreatePage.module.scss';

interface TeacherGroupOption {
  id: string;
  name: string;
  subject?: string | null;
  subject_id?: string | null;
  subject_name?: string | null;
}

interface CurriculumSubjectOption {
  id: string;
  name: string;
  code?: string | null;
}

const createSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  assessment_type: z.enum(['test', 'quiz', 'survey', 'practice']),
  subject_id: z.string().min(1, 'Subject is required'),
  group_id: z.string().optional(),
  time_limit_minutes: z.coerce.number().positive().optional(),
  available_from: z.string().optional(),
  available_until: z.string().optional(),
  max_attempts: z.coerce.number().int().positive().default(1),
  passing_score: z.coerce.number().min(0).max(100).default(50),
  shuffle_questions: z.boolean().default(false),
  shuffle_options: z.boolean().default(false),
  max_violations: z.coerce.number().int().min(0).default(3),
  time_penalty_minutes: z.coerce.number().int().min(0).default(2),
  enforce_fullscreen: z.boolean().default(true),
  block_keyboard_shortcuts: z.boolean().default(true),
  tab_switch_detection: z.boolean().default(true),
  devtools_detection: z.boolean().default(true),
  right_click_block: z.boolean().default(true),
  copy_paste_block: z.boolean().default(true),
});

type CreateForm = z.input<typeof createSchema>;
type CreateFormOutput = z.output<typeof createSchema>;

const TYPE_OPTIONS = [
  { value: 'test', label: 'Test' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'survey', label: 'Survey' },
  { value: 'practice', label: 'Practice' },
];

export default function TeacherAssessmentCreatePage() {
  const navigate = useNavigate();

  const { data: groups } = useQuery({
    queryKey: ['teacher', 'groups'],
    queryFn: async () => {
      const res = await api.get('/teacher/assessments/groups');
      return (res.data.data ?? res.data) as TeacherGroupOption[];
    },
  });

  const { data: subjects } = useQuery({
    queryKey: ['teacher', 'assessment-subjects'],
    queryFn: async () => {
      const res = await api.get('/teacher/assessments/subjects');
      return (res.data.data ?? res.data) as CurriculumSubjectOption[];
    },
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
    setValue,
    control,
    formState: { errors },
  } = useForm<CreateForm, unknown, CreateFormOutput>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      assessment_type: 'test',
      subject_id: '',
      group_id: '',
      max_attempts: 1,
      passing_score: 50,
      shuffle_questions: false,
      shuffle_options: false,
      max_violations: 3,
      time_penalty_minutes: 2,
      enforce_fullscreen: true,
      block_keyboard_shortcuts: true,
      tab_switch_detection: true,
      devtools_detection: true,
      right_click_block: true,
      copy_paste_block: true,
    },
  });

  const selectedGroupId = useWatch({ control, name: 'group_id' }) ?? '';
  const selectedGroup = (groups ?? []).find((group) => group.id === selectedGroupId) ?? null;
  const lockedSubjectId = selectedGroup?.subject_id ?? '';

  useEffect(() => {
    if (lockedSubjectId) {
      setValue('subject_id', lockedSubjectId, { shouldDirty: true, shouldValidate: true });
    }
  }, [lockedSubjectId, setValue]);

  const createMutation = useMutation({
    mutationFn: async (payload: CreateFormOutput) => {
      const body: AssessmentCreate = {
        title: payload.title,
        description: payload.description || undefined,
        assessment_type: payload.assessment_type,
        format_type: 'timed_test',
        group_id: payload.group_id || undefined,
        subject_id: payload.subject_id || undefined,
        time_limit_minutes: payload.time_limit_minutes || undefined,
        available_from: payload.available_from || undefined,
        available_until: payload.available_until || undefined,
        max_attempts: payload.max_attempts,
        scoring_policy: 'best',
        passing_score: payload.passing_score,
        score_release_policy: 'immediate',
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
          webcam_proctoring: false,
        },
      };
      const res = await api.post('/teacher/assessments', body);
      return (res.data.data ?? res.data) as Assessment;
    },
    onSuccess: (data) => {
      toast.success('Assessment created');
      navigate(`/teacher/assessments/${data.id}`);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Failed to create assessment';
      toast.error(msg);
    },
  });

  const onSubmit = (formData: CreateFormOutput) => createMutation.mutate(formData);

  return (
    <div className={styles.page}>
      <Link to="/teacher/assessments" className={styles.back}>
        <FiArrowLeft /> Back to Assessments
      </Link>

      <Card title="Create Assessment">
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)}>
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
            <Select
              label="Group"
              options={groupOptions}
              {...register('group_id')}
              error={errors.group_id?.message}
            />
            <Input
              label="Time Limit (minutes)"
              type="number"
              {...register('time_limit_minutes')}
              error={errors.time_limit_minutes?.message}
            />
            <Input
              label="Available From"
              type="datetime-local"
              {...register('available_from')}
              error={errors.available_from?.message}
            />
            <Input
              label="Available Until"
              type="datetime-local"
              {...register('available_until')}
              error={errors.available_until?.message}
            />
            <Input
              label="Max Attempts"
              type="number"
              {...register('max_attempts')}
              error={errors.max_attempts?.message}
            />
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
          </div>

          <Textarea label="Description" {...register('description')} error={errors.description?.message} />

          <p className={styles.helperText}>
            {selectedGroup
              ? lockedSubjectId
                ? `The selected group is already mapped to ${selectedGroup.subject_name ?? 'a curriculum subject'}, so the assessment subject is locked to that subject.`
                : 'The selected group does not have a curriculum subject yet, so choose the assessment subject directly.'
              : 'Assessments can be created without a group, but they still must belong to a curriculum subject.'}
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

          <div className={styles.actions}>
            <Button variant="secondary" type="button" onClick={() => navigate('/teacher/assessments')}>
              Cancel
            </Button>
            <Button type="submit" loading={createMutation.isPending}>
              Create Assessment
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
