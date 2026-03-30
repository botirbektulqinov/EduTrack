/* ─── Teacher: Student Semester Performance View ─── */
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api from '@/lib/api';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import Button from '@/components/ui/Button';
import styles from './TeacherStudentSemesterPerformancePage.module.scss';
import type { ScoreTrendPoint, SubjectScore, StudentDashboard } from '@/types';

export default function TeacherStudentSemesterPerformancePage() {
  const { id: studentId } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery<StudentDashboard | null, Error, StudentDashboard | null>({
    queryKey: ['teacher', 'student', studentId, 'semester-performance'],
    queryFn: async () => {
      if (!studentId) return null;
      const res = await api.get(`/teacher/students/${studentId}/semester-performance`);
      return (res.data.data ?? res.data) as StudentDashboard;
    },
    enabled: !!studentId,
    retry: false,
  });

  if (error) {
    const axiosErr = error as { response?: { data?: { message?: string } } };
    const msg = axiosErr.response?.data?.message || 'Failed to load performance';
    toast.error(msg);
  }

  if (isLoading) return (
    <div className={styles.center}><Spinner size="lg" /></div>
  );

  if (!data) {
    return (
      <div className={styles.page}>
        <p>No performance data available.</p>
        <Link to="/teacher/dashboard">
          <Button variant="secondary">Back</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Link to="/teacher/dashboard">
        <Button variant="ghost">Back to Dashboard</Button>
      </Link>

      <h1>Semester Performance</h1>

      <div className={styles.grid}>
        <Card title="Overview">
          <div>
            <div><strong>Average Score:</strong> {data.overall_score_avg ?? '—'}</div>
            <div><strong>Pass Rate:</strong> {data.pass_rate ?? '—'}</div>
            <div><strong>Assessments Taken:</strong> {data.assessments_taken}</div>
            <div><strong>Violations (total):</strong> {data.violation_count_total}</div>
          </div>
        </Card>

        <Card title="Subject Breakdown">
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Subject</th>
                <th>Group</th>
                <th>Assessments</th>
                <th>Avg Score</th>
                <th>Pass Rate</th>
              </tr>
            </thead>
            <tbody>
              {data.subject_scores.map((s: SubjectScore) => (
                <tr key={s.group_id}>
                  <td>{s.subject}</td>
                  <td>{s.group_name}</td>
                  <td>{s.assessments_taken}</td>
                  <td>{s.average_score ?? '—'}</td>
                  <td>{s.pass_rate ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title="Recent Results">
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Date</th>
                <th>Score</th>
                <th>Assessment</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_results.map((r: ScoreTrendPoint) => (
                <tr key={r.assessment_id + r.date}>
                  <td>{r.date}</td>
                  <td>{r.score}</td>
                  <td>{r.assessment_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
