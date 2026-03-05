/* ─── Student: Results List Page ─── */
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiEye, FiFileText } from 'react-icons/fi';
import api from '@/lib/api';
import { formatDate } from '@/lib/utils';
import type { AssessmentAttempt, AttemptStatus } from '@/types';
import Button from '@/components/ui/Button';
import Table from '@/components/ui/Table';
import Badge from '@/components/ui/Badge';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import styles from './StudentResultsPage.module.scss';

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

export default function StudentResultsPage() {
  const navigate = useNavigate();

  const { data: attempts, isLoading } = useQuery({
    queryKey: ['student-results'],
    queryFn: async () => {
      const res = await api.get('/student/results');
      return (res.data.data ?? res.data) as AssessmentAttempt[];
    },
  });

  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>My Results</h1>

      {!attempts || attempts.length === 0 ? (
        <EmptyState
          icon={<FiFileText size={48} />}
          title="No results yet"
          description="Your assessment results will appear here once you have completed an assessment."
        />
      ) : (
        <Table headers={['Assessment', 'Status', 'Score', 'Grade', 'Date', 'Actions']}>
          {attempts.map((a) => (
            <tr
              key={a.id}
              className={styles.row}
              onClick={() => navigate(`/student/results/${a.id}`)}
            >
              <td>
                {a.assessment_title ?? a.assessment_id.slice(0, 8) + '…'}
              </td>
              <td>
                <Badge variant={statusVariant(a.status)}>
                  {statusLabel(a.status)}
                </Badge>
              </td>
              <td>
                {a.score_percent !== undefined ? `${a.score_percent.toFixed(1)}%` : '—'}
              </td>
              <td>{a.grade ?? '—'}</td>
              <td>{a.submitted_at ? formatDate(a.submitted_at) : formatDate(a.created_at)}</td>
              <td>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<FiEye />}
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/student/results/${a.id}`);
                  }}
                >
                  View
                </Button>
              </td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  );
}
