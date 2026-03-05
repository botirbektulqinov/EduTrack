/* ─── Teacher: Create Assessment Page ─── */
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
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

/* ── Zod schema ── */
const createSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  assessment_type: z.enum(['test', 'quiz', 'survey', 'practice']),
  group_id: z.string().min(1, 'Group is required'),
  time_limit_minutes: z.coerce.number().positive().optional(),
  available_from: z.string().optional(),
  available_until: z.string().optional(),
  max_attempts: z.coerce.number().int().positive().default(1),
  passing_score: z.coerce.number().min(0).max(100).default(50),
  shuffle_questions: z.boolean().default(false),
  shuffle_options: z.boolean().default(false),
  max_violations: z.coerce.number().int().min(0).default(3),
  enforce_fullscreen: z.boolean().default(true),
});

type CreateForm = z.infer<typeof createSchema>;

const TYPE_OPTIONS = [
  { value: 'test', label: 'Test' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'survey', label: 'Survey' },
  { value: 'practice', label: 'Practice' },
];

export default function TeacherAssessmentCreatePage() {
  const navigate = useNavigate();

  /* ── Fetch teacher groups ── */
  const { data: groups } = useQuery({
    queryKey: ['teacher', 'groups'],
    queryFn: async () => {
      const res = await api.get('/teacher/assessments/groups');
      return (res.data.data ?? res.data) as { id: string; name: string; subject?: string }[];
    },
  });

  const groupOptions = [
    { value: '', label: 'Select a group…' },
    ...(groups ?? []).map((g) => ({ value: g.id, label: `${g.name}${g.subject ? ` — ${g.subject}` : ''}` })),
  ];

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CreateForm>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(createSchema) as any,
    defaultValues: {
      assessment_type: 'test',
      max_attempts: 1,
      passing_score: 50,
      shuffle_questions: false,
      shuffle_options: false,
      max_violations: 3,
      enforce_fullscreen: true,
    },
  });

  const createMutation = useMutation({
    mutationFn: async (payload: CreateForm) => {
      const body: AssessmentCreate = {
        ...payload,
        available_from: payload.available_from || undefined,
        available_until: payload.available_until || undefined,
        time_limit_minutes: payload.time_limit_minutes || undefined,
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

  const onSubmit = (formData: CreateForm) => createMutation.mutate(formData);

  return (
    <div className={styles.page}>
      <Link to="/teacher/assessments" className={styles.back}>
        <FiArrowLeft /> Back to Assessments
      </Link>

      <Card title="Create Assessment">
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)}>
          <div className={styles.formGrid}>
            <Input
              label="Title"
              {...register('title')}
              error={errors.title?.message}
            />
            <Select
              label="Type"
              options={TYPE_OPTIONS}
              {...register('assessment_type')}
              error={errors.assessment_type?.message}
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
          </div>

          <Textarea
            label="Description"
            {...register('description')}
            error={errors.description?.message}
          />

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
          </div>

          <div className={styles.actions}>
            <Button
              variant="secondary"
              type="button"
              onClick={() => navigate('/teacher/assessments')}
            >
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
