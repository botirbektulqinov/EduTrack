/* ─── Teacher: Assessment Results Page ─── */
import { useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiBarChart2, FiAlertTriangle } from 'react-icons/fi';
import api from '@/lib/api';
import type { AssessmentAttempt, ItemAnalysis, Violation } from '@/types';
import { formatDateTime } from '@/lib/utils';
import Badge from '@/components/ui/Badge';
import Table from '@/components/ui/Table';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import Button from '@/components/ui/Button';
import styles from './TeacherResultsPage.module.scss';

const STATUS_VARIANT: Record<string, 'info' | 'success' | 'danger' | 'warning' | 'neutral'> = {
  submitted: 'info',
  graded: 'success',
  terminated: 'danger',
  in_progress: 'warning',
  grading: 'info',
  not_started: 'neutral',
};

export default function TeacherResultsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showItemAnalysis, setShowItemAnalysis] = useState(false);
  const [showViolations, setShowViolations] = useState(false);

  /* ── Fetch attempts ── */
  const { data: attempts, isLoading } = useQuery({
    queryKey: ['teacher', 'attempts', id],
    queryFn: async () => {
      const res = await api.get(`/teacher/assessments/${id}/attempts`);
      return (res.data.data ?? res.data) as AssessmentAttempt[];
    },
    enabled: !!id,
  });

  /* ── Fetch item analysis (lazy) ── */
  const { data: itemAnalysis, isLoading: itemsLoading } = useQuery({
    queryKey: ['teacher', 'item-analysis', id],
    queryFn: async () => {
      const res = await api.get(`/teacher/assessments/${id}/item-analysis`);
      return (res.data.data ?? res.data) as ItemAnalysis[];
    },
    enabled: !!id && showItemAnalysis,
  });

  /* ── Fetch violations (lazy) ── */
  const { data: violations, isLoading: violationsLoading } = useQuery({
    queryKey: ['teacher', 'violations', id],
    queryFn: async () => {
      const res = await api.get(`/teacher/assessments/${id}/violations`);
      return (res.data.data ?? res.data) as Violation[];
    },
    enabled: !!id && showViolations,
  });

  /* ── Computed stats ── */
  const stats = useMemo(() => {
    if (!attempts || attempts.length === 0) {
      return { total: 0, avgScore: 0, passRate: 0 };
    }
    const scored = attempts.filter((a) => a.score_percent != null);
    const avgScore =
      scored.length > 0
        ? scored.reduce((s, a) => s + (a.score_percent ?? 0), 0) / scored.length
        : 0;
    const passed = scored.filter((a) => (a.score_percent ?? 0) >= 50).length;
    const passRate = scored.length > 0 ? (passed / scored.length) * 100 : 0;
    return { total: attempts.length, avgScore, passRate };
  }, [attempts]);

  return (
    <div className={styles.page}>
      {/* Back link */}
      <Link to={`/teacher/assessments/${id}`} className={styles.backLink}>
        <FiArrowLeft /> Back to Assessment
      </Link>

      {/* Header */}
      <div className={styles.header}>
        <h1>Results</h1>
        <div className={styles.headerActions}>
          <Button
            variant="secondary"
            icon={<FiBarChart2 />}
            onClick={() => setShowItemAnalysis((v) => !v)}
          >
            {showItemAnalysis ? 'Hide' : 'Show'} Item Analysis
          </Button>
          <Button
            variant="secondary"
            icon={<FiAlertTriangle />}
            onClick={() => setShowViolations((v) => !v)}
          >
            {showViolations ? 'Hide' : 'Show'} Violations
          </Button>
        </div>
      </div>

      {/* Summary stats */}
      <div className={styles.stats}>
        <Card className={styles.statCard}>
          <div className={styles.statValue}>{stats.total}</div>
          <div className={styles.statLabel}>Total Attempts</div>
        </Card>
        <Card className={styles.statCard}>
          <div className={styles.statValue}>{stats.avgScore.toFixed(1)}%</div>
          <div className={styles.statLabel}>Average Score</div>
        </Card>
        <Card className={styles.statCard}>
          <div className={styles.statValue}>{stats.passRate.toFixed(1)}%</div>
          <div className={styles.statLabel}>Pass Rate</div>
        </Card>
      </div>

      {/* Attempts table */}
      {isLoading ? (
        <div className={styles.center}>
          <Spinner size="lg" />
        </div>
      ) : !attempts || attempts.length === 0 ? (
        <EmptyState
          icon={<FiBarChart2 size={40} />}
          title="No attempts yet"
          description="No students have attempted this assessment."
        />
      ) : (
        <Table
          headers={['Student', 'Status', 'Score', 'Grade', 'Violations', 'Submitted']}
        >
          {attempts.map((a) => (
            <tr
              key={a.id}
              className={styles.row}
              onClick={() => navigate(`/teacher/attempts/${a.id}`)}
            >
              <td>{a.student_name ?? a.student_id}</td>
              <td>
                <Badge variant={STATUS_VARIANT[a.status] ?? 'neutral'}>
                  {a.status.replace('_', ' ')}
                </Badge>
              </td>
              <td>{a.score_percent != null ? `${a.score_percent.toFixed(1)}%` : '—'}</td>
              <td>{a.grade ?? '—'}</td>
              <td>{a.violation_count}</td>
              <td>{a.submitted_at ? formatDateTime(a.submitted_at) : '—'}</td>
            </tr>
          ))}
        </Table>
      )}

      {/* Item Analysis section */}
      {showItemAnalysis && (
        <Card title="Item Analysis">
          {itemsLoading ? (
            <div className={styles.center}>
              <Spinner />
            </div>
          ) : !itemAnalysis || itemAnalysis.length === 0 ? (
            <p>No item analysis data available.</p>
          ) : (
            <Table
              headers={[
                'Question',
                'Type',
                'Difficulty Index',
                'Discrimination Index',
                'Point-Biserial',
                'Classification',
              ]}
            >
              {itemAnalysis.map((item) => (
                <tr key={item.question_id}>
                  <td className={styles.questionContent}>{item.content}</td>
                  <td>
                    <Badge variant="neutral">{item.question_type}</Badge>
                  </td>
                  <td>{item.difficulty_index?.toFixed(2) ?? '—'}</td>
                  <td>{item.discrimination_index?.toFixed(2) ?? '—'}</td>
                  <td>{item.point_biserial?.toFixed(2) ?? '—'}</td>
                  <td>
                    <Badge
                      variant={
                        item.classification === 'good'
                          ? 'success'
                          : item.classification === 'poor'
                            ? 'danger'
                            : 'warning'
                      }
                    >
                      {item.classification}
                    </Badge>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      )}

      {/* Violations section */}
      {showViolations && (
        <Card title="Violations">
          {violationsLoading ? (
            <div className={styles.center}>
              <Spinner />
            </div>
          ) : !violations || violations.length === 0 ? (
            <p>No violations recorded for this assessment.</p>
          ) : (
            <Table
              headers={['Student', 'Type', 'Count After', 'Time Deducted', 'Resolved', 'Occurred At']}
            >
              {violations.map((v) => (
                <tr key={v.id}>
                  <td>{v.student_id.slice(0, 8)}…</td>
                  <td>
                    <Badge variant="danger">{v.violation_type.replace('_', ' ')}</Badge>
                  </td>
                  <td>{v.violation_count_after}</td>
                  <td>{v.time_deducted_seconds ? `${v.time_deducted_seconds}s` : '—'}</td>
                  <td>
                    <Badge variant={v.resolved ? 'success' : 'warning'}>
                      {v.resolved ? 'Yes' : 'No'}
                    </Badge>
                  </td>
                  <td>{formatDateTime(v.occurred_at)}</td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      )}
    </div>
  );
}
