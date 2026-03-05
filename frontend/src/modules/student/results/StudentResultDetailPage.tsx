/* ─── Student: Result Detail Page ─── */
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiClock, FiAlertTriangle } from 'react-icons/fi';
import api from '@/lib/api';
import { formatDateTime, formatTime, scoreColor, gradeFromScore } from '@/lib/utils';
import type { AssessmentAttempt, StudentAnswer, AttemptStatus } from '@/types';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import Spinner from '@/components/ui/Spinner';
import styles from './StudentResultDetailPage.module.scss';

/* ── Helpers ── */
const statusVariant = (status: AttemptStatus) => {
  const map: Record<AttemptStatus, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
    not_started: 'neutral',
    in_progress: 'info',
    submitted: 'info',
    grading: 'warning',
    graded: 'success',
    terminated: 'danger',
  };
  return map[status] ?? 'neutral';
};

const statusLabel = (status: AttemptStatus) =>
  status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

function answerBadge(scoreAwarded: number | undefined, maxPoints = 1) {
  if (scoreAwarded === undefined) return { variant: 'neutral' as const, label: 'Pending' };
  if (scoreAwarded >= maxPoints) return { variant: 'success' as const, label: 'Correct' };
  if (scoreAwarded > 0) return { variant: 'warning' as const, label: 'Partial' };
  return { variant: 'danger' as const, label: 'Incorrect' };
}

function answerPreview(answer: StudentAnswer): string {
  if (answer.answer_text) return answer.answer_text;
  if (answer.selected_option_ids?.length) return `Selected ${answer.selected_option_ids.length} option(s)`;
  if (answer.matched_pairs) return `${Object.keys(answer.matched_pairs).length} pair(s) matched`;
  if (answer.ordered_ids?.length) return `${answer.ordered_ids.length} items ordered`;
  if (answer.categorized) return `${Object.keys(answer.categorized).length} categories`;
  if (answer.code_submission) return answer.code_submission.slice(0, 120) + (answer.code_submission.length > 120 ? '…' : '');
  return '—';
}

interface ResultDetailData extends AssessmentAttempt {
  answers?: StudentAnswer[];
  assessment_title?: string;
}

export default function StudentResultDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading } = useQuery({
    queryKey: ['student-result', id],
    queryFn: async () => {
      const res = await api.get(`/student/results/${id}`);
      return (res.data.data ?? res.data) as ResultDetailData;
    },
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className={styles.center}>
        <p>Result not found.</p>
      </div>
    );
  }

  const attempt = data;
  const answers = data.answers ?? [];

  const timeTaken =
    attempt.started_at && attempt.submitted_at
      ? Math.round(
          (new Date(attempt.submitted_at).getTime() - new Date(attempt.started_at).getTime()) /
            1000,
        )
      : null;

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Result Detail</h1>

      {/* ── Summary Card ── */}
      <Card title="Attempt Summary">
        <div className={styles.summaryGrid}>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Assessment</span>
            <span className={styles.summaryValue}>{attempt.assessment_title ?? attempt.assessment_id.slice(0, 8) + '…'}</span>
          </div>

          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Status</span>
            <Badge variant={statusVariant(attempt.status)}>
              {statusLabel(attempt.status)}
            </Badge>
          </div>

          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Score</span>
            <span
              className={styles.summaryValue}
              style={{ color: scoreColor(attempt.score_percent ?? null) }}
            >
              {attempt.score_percent !== undefined ? `${attempt.score_percent.toFixed(1)}%` : 'N/A'}
            </span>
          </div>

          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Grade</span>
            <span className={styles.summaryValue}>
              {attempt.grade ?? (attempt.score_percent !== undefined ? gradeFromScore(attempt.score_percent) : '—')}
            </span>
          </div>

          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>
              <FiClock size={14} /> Time Taken
            </span>
            <span className={styles.summaryValue}>
              {timeTaken !== null ? formatTime(timeTaken) : '—'}
            </span>
          </div>

          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>
              <FiAlertTriangle size={14} /> Violations
            </span>
            <span className={styles.summaryValue}>
              {attempt.violation_count}
            </span>
          </div>

          {attempt.submitted_at && (
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>Submitted</span>
              <span className={styles.summaryValue}>{formatDateTime(attempt.submitted_at)}</span>
            </div>
          )}

          {attempt.termination_reason && (
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>Termination Reason</span>
              <Badge variant="danger">{attempt.termination_reason}</Badge>
            </div>
          )}
        </div>
      </Card>

      {/* ── Answers List ── */}
      <Card title={`Answers (${answers.length})`}>
        {answers.length === 0 ? (
          <p className={styles.emptyText}>No answers recorded.</p>
        ) : (
          <div className={styles.answersList}>
            {answers.map((ans, idx) => {
              const badge = answerBadge(ans.score_awarded);
              return (
                <div key={ans.id} className={styles.answerCard}>
                  <div className={styles.answerHeader}>
                    <span className={styles.answerNum}>Q{idx + 1}</span>
                    <Badge variant={badge.variant}>{badge.label}</Badge>
                    {ans.score_awarded !== undefined && (
                      <span className={styles.answerScore}>
                        {ans.score_awarded} pt{ans.score_awarded !== 1 ? 's' : ''}
                      </span>
                    )}
                    {ans.is_flagged && <Badge variant="warning">Flagged</Badge>}
                  </div>

                  <div className={styles.answerBody}>
                    <p className={styles.answerPreview}>{answerPreview(ans)}</p>
                    {ans.time_spent_seconds !== undefined && (
                      <span className={styles.timeSpent}>
                        <FiClock size={12} /> {formatTime(ans.time_spent_seconds)}
                      </span>
                    )}
                  </div>

                  {ans.teacher_feedback && (
                    <div className={styles.feedback}>
                      <span className={styles.feedbackLabel}>Teacher Feedback</span>
                      <p className={styles.feedbackText}>{ans.teacher_feedback}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
