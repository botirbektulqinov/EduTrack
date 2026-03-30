/* ─── Teacher: Attempt Detail & Manual Grading Page ─── */
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useFieldArray } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import { FiArrowLeft, FiSave } from 'react-icons/fi';
import api from '@/lib/api';
import type { AssessmentAttempt, StudentAnswer, Question } from '@/types';
import { formatDateTime, getErrorMessage } from '@/lib/utils';
import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Textarea from '@/components/ui/Textarea';
import Spinner from '@/components/ui/Spinner';
import styles from './TeacherAttemptDetailPage.module.scss';

const STATUS_VARIANT: Record<string, 'info' | 'success' | 'danger' | 'warning' | 'neutral'> = {
  submitted: 'info',
  graded: 'success',
  terminated: 'danger',
  in_progress: 'warning',
  grading: 'info',
  not_started: 'neutral',
};

/* ── Grading form schema ── */
const gradeItemSchema = z.object({
  question_id: z.string(),
  score_awarded: z.coerce.number().min(0),
  feedback: z.string().optional(),
});

const gradingSchema = z.object({
  grades: z.array(gradeItemSchema),
});

type GradingForm = z.infer<typeof gradingSchema>;

interface AttemptDetail extends AssessmentAttempt {
  answers?: StudentAnswer[];
  questions?: Question[];
  assessment_title?: string;
  student_name?: string;
}

export default function TeacherAttemptDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  /* ── Fetch attempt detail ── */
  const { data: attempt, isLoading } = useQuery({
    queryKey: ['teacher', 'attempt', id],
    queryFn: async () => {
      const res = await api.get(`/teacher/attempts/${id}`);
      return (res.data.data ?? res.data) as AttemptDetail;
    },
    enabled: !!id,
  });

  /* ── Answers that need manual review ── */
  const reviewableAnswers = (attempt?.answers ?? []).filter((a) => !a.auto_graded);

  /* ── Form setup ── */
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<GradingForm>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(gradingSchema) as any,
    values: {
      grades: reviewableAnswers.map((a) => ({
        question_id: a.question_id,
        score_awarded: a.score_awarded ?? 0,
        feedback: a.teacher_feedback ?? '',
      })),
    },
  });

  const { fields } = useFieldArray({ control, name: 'grades' });

  /* ── Submit grades ── */
  const { mutate: submitGrades, isPending } = useMutation({
    mutationFn: async (data: GradingForm) => {
      await api.patch(`/teacher/attempts/${id}/grade`, data);
    },
    onSuccess: () => {
      toast.success('Grades saved successfully');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'attempt', id] });
    },
    onError: (err) => {
      toast.error(getErrorMessage(err));
    },
  });

  /* ── Helpers ── */
  const getQuestion = (questionId: string) =>
    attempt?.questions?.find((q) => q.id === questionId);

  const [now] = useState(() => Date.now());
  const computeTimeUsed = () => {
    if (!attempt?.started_at) return '—';
    const start = new Date(attempt.started_at).getTime();
    const end = attempt.submitted_at
      ? new Date(attempt.submitted_at).getTime()
      : now;
    const mins = Math.round((end - start) / 60000);
    return `${mins} min`;
  };

  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!attempt) {
    return (
      <div className={styles.page}>
        <p>Attempt not found.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* Back link */}
      <Link
        to={`/teacher/assessments/${attempt.assessment_id}`}
        className={styles.backLink}
      >
        <FiArrowLeft /> Back to Results
      </Link>

      {/* Header */}
      <div className={styles.header}>
        <div>
          <h1>{attempt.assessment_title ?? 'Attempt Detail'}</h1>
          <Badge variant={STATUS_VARIANT[attempt.status] ?? 'neutral'}>
            {attempt.status.replace('_', ' ')}
          </Badge>
        </div>
      </div>

      {/* Attempt info */}
      <Card title="Attempt Information">
        <div className={styles.infoGrid}>
          <div>
            <span className={styles.infoLabel}>Student</span>
            <span className={styles.infoValue}>
              <Link
                to={`/teacher/students/${attempt.student_id}/semester-performance`}
                style={{ color: '#4f46e5', textDecoration: 'underline' }}
                title="View Student Semester Performance"
              >
                {attempt.student_name ?? attempt.student_id}
              </Link>
            </span>
          </div>
          <div>
            <span className={styles.infoLabel}>Score</span>
            <span className={styles.infoValue}>
              {attempt.score_percent != null
                ? `${attempt.score_percent.toFixed(1)}%`
                : '—'}
              {attempt.score_raw != null && ` (${attempt.score_raw} pts)`}
            </span>
          </div>
          <div>
            <span className={styles.infoLabel}>Grade</span>
            <span className={styles.infoValue}>{attempt.grade ?? '—'}</span>
          </div>
          <div>
            <span className={styles.infoLabel}>Violations</span>
            <span className={styles.infoValue}>{attempt.violation_count}</span>
          </div>
          <div>
            <span className={styles.infoLabel}>Started</span>
            <span className={styles.infoValue}>
              {formatDateTime(attempt.started_at)}
            </span>
          </div>
          <div>
            <span className={styles.infoLabel}>Submitted</span>
            <span className={styles.infoValue}>
              {attempt.submitted_at ? formatDateTime(attempt.submitted_at) : '—'}
            </span>
          </div>
          <div>
            <span className={styles.infoLabel}>Time Used</span>
            <span className={styles.infoValue}>{computeTimeUsed()}</span>
          </div>
        </div>
      </Card>

      {/* Student answers */}
      {attempt.answers && attempt.answers.length > 0 && (
        <Card title="Student Answers">
          <div className={styles.answersSection}>
            {attempt.answers.map((answer, idx) => {
              const question = getQuestion(answer.question_id);
              return (
                <div key={answer.id} className={styles.answerCard}>
                  <div className={styles.answerHeader}>
                    <strong>Q{idx + 1}.</strong>{' '}
                    {question?.content ?? answer.question_id}
                    {question && (
                      <Badge variant="neutral">
                        {question.points} pt{question.points !== 1 ? 's' : ''}
                      </Badge>
                    )}
                  </div>
                  <div className={styles.answerBody}>
                    {answer.answer_text && <p>{answer.answer_text}</p>}
                    {answer.code_submission && (
                      <pre className={styles.codeBlock}>{answer.code_submission}</pre>
                    )}
                    {answer.selected_option_ids &&
                      answer.selected_option_ids.length > 0 && (
                        <p>
                          Selected:{' '}
                          {answer.selected_option_ids
                            .map((optId) => {
                              const opt = question?.options?.find(
                                (o) => o.id === optId,
                              );
                              return opt ? opt.content : optId;
                            })
                            .join(', ')}
                        </p>
                      )}
                  </div>
                  <div className={styles.answerMeta}>
                    <Badge variant={answer.auto_graded ? 'success' : 'warning'}>
                      {answer.auto_graded ? 'Auto-graded' : 'Needs Review'}
                    </Badge>
                    {answer.score_awarded != null && (
                      <span>Score: {answer.score_awarded}</span>
                    )}
                    {answer.is_flagged && <Badge variant="danger">Flagged</Badge>}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Manual grading form */}
      {reviewableAnswers.length > 0 && (
        <Card title="Manual Grading">
          <form
            className={styles.gradeForm}
            onSubmit={handleSubmit((data) => submitGrades(data))}
          >
            {fields.map((field, idx) => {
              const answer = reviewableAnswers[idx];
              const question = getQuestion(answer.question_id);
              return (
                <div key={field.id} className={styles.gradeItem}>
                  <div className={styles.gradeQuestion}>
                    <strong>Q: </strong>
                    {question?.content ?? answer.question_id}
                    {question && (
                      <span className={styles.maxPoints}>
                        (max {question.points} pts)
                      </span>
                    )}
                  </div>
                  <div className={styles.gradeFields}>
                    <Input
                      label="Score"
                      type="number"
                      step="0.5"
                      min={0}
                      max={question?.points}
                      error={errors.grades?.[idx]?.score_awarded?.message}
                      {...register(`grades.${idx}.score_awarded`)}
                    />
                    <Textarea
                      label="Feedback"
                      rows={2}
                      {...register(`grades.${idx}.feedback`)}
                    />
                  </div>
                </div>
              );
            })}
            <div className={styles.actions}>
              <Button type="submit" loading={isPending} icon={<FiSave />}>
                Save Grades
              </Button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
