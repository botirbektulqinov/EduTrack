/* ─── Student: Dashboard Page ─── */
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { FiTrendingUp, FiCheckCircle, FiBookOpen, FiZap, FiPlay, FiClock } from 'react-icons/fi';
import api from '@/lib/api';
import { formatDate, formatDateTime, scoreColor } from '@/lib/utils';
import type { StudentDashboard, SubjectScore } from '@/types';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import styles from './StudentDashboardPage.module.scss';

/* ── Stat card ── */
interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  color?: string;
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  return (
    <div className={styles.statCard} style={color ? { borderTopColor: color } : undefined}>
      <div className={styles.statIcon}>{icon}</div>
      <div className={styles.statInfo}>
        <span className={styles.statValue}>{value}</span>
        <span className={styles.statLabel}>{label}</span>
      </div>
    </div>
  );
}

interface AvailableAssessment {
  id: string;
  title: string;
  description?: string;
  assessment_type: string;
  group_name?: string;
  time_limit_minutes?: number;
  available_from?: string;
  available_until?: string;
  max_attempts: number;
  attempts_used: number;
  can_attempt: boolean;
  in_progress: boolean;
  access_token: string;
}

export default function StudentDashboardPage() {
  const navigate = useNavigate();
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['student-dashboard'],
    queryFn: async () => {
      const res = await api.get('/student/analytics/dashboard');
      return (res.data.data ?? res.data) as StudentDashboard;
    },
  });

  /* ── Fetch available assessments ── */
  const { data: availableAssessments } = useQuery({
    queryKey: ['student-available-assessments'],
    queryFn: async () => {
      const res = await api.get('/student/analytics/available-assessments');
      return (res.data.data ?? res.data) as AvailableAssessment[];
    },
  });

  /* ── Fetch subject breakdown (dedicated endpoint) ── */
  const { data: subjectBreakdown } = useQuery({
    queryKey: ['student-subjects'],
    queryFn: async () => {
      const res = await api.get('/student/analytics/subjects');
      return (res.data.data ?? res.data) as SubjectScore[];
    },
  });

  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className={styles.center}>
        <p>Failed to load dashboard data.</p>
      </div>
    );
  }

  const trendData = dashboard.score_trend.map((pt) => ({
    date: formatDate(pt.date, 'MMM d'),
    score: pt.score,
  }));

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>My Dashboard</h1>

      {/* ── Stat cards ── */}
      <div className={styles.statsGrid}>
        <StatCard
          icon={<FiTrendingUp size={24} />}
          label="Overall Average"
          value={dashboard.overall_score_avg !== null ? `${dashboard.overall_score_avg.toFixed(1)}%` : 'N/A'}
          color="#4F46E5"
        />
        <StatCard
          icon={<FiCheckCircle size={24} />}
          label="Pass Rate"
          value={dashboard.pass_rate !== null ? `${dashboard.pass_rate.toFixed(1)}%` : 'N/A'}
          color="#10B981"
        />
        <StatCard
          icon={<FiBookOpen size={24} />}
          label="Assessments Taken"
          value={dashboard.assessments_taken}
          color="#F59E0B"
        />
        <StatCard
          icon={<FiZap size={24} />}
          label="Current Streak"
          value={dashboard.streak_count}
          color="#8B5CF6"
        />
      </div>

      {/* ── Available Assessments ── */}
      <Card title="Available Assessments">
        {!availableAssessments || availableAssessments.length === 0 ? (
          <EmptyState
            icon={<FiBookOpen size={36} />}
            title="No assessments available"
            description="You have no pending assessments right now."
          />
        ) : (
          <div className={styles.assessmentList}>
            {availableAssessments.map((a) => (
              <div key={a.id} className={styles.assessmentCard}>
                <div className={styles.assessmentInfo}>
                  <h3 className={styles.assessmentTitle}>{a.title}</h3>
                  <div className={styles.assessmentMeta}>
                    {a.group_name && <Badge variant="neutral">{a.group_name}</Badge>}
                    <Badge variant="info">{a.assessment_type}</Badge>
                    {a.time_limit_minutes && (
                      <span className={styles.timeBadge}>
                        <FiClock size={12} /> {a.time_limit_minutes} min
                      </span>
                    )}
                    <span className={styles.attemptInfo}>
                      Attempts: {a.attempts_used}/{a.max_attempts}
                    </span>
                  </div>
                  {a.available_until && (
                    <span className={styles.deadline}>
                      Due: {formatDateTime(a.available_until)}
                    </span>
                  )}
                  {a.description && <p className={styles.assessmentDesc}>{a.description}</p>}
                </div>
                <div className={styles.assessmentAction}>
                  {a.can_attempt ? (
                    <Button
                      icon={<FiPlay />}
                      onClick={() => navigate(`/take/${a.access_token}`)}
                    >
                      {a.in_progress ? 'Continue' : 'Start'}
                    </Button>
                  ) : (
                    <Badge variant="neutral">All attempts used</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ── Score Trend ── */}
      <Card title="Score Trend">
        {trendData.length === 0 ? (
          <p className={styles.emptyChart}>No score data yet.</p>
        ) : (
          <div className={styles.chartWrap}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(val) => `${Number(val).toFixed(1)}%`} />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#4F46E5"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {/* ── Subject Performance + Weak Topics ── */}
      <div className={styles.twoCol}>
        {/* Subject Performance (from /analytics/subjects endpoint) */}
        <Card title="Subject Performance">
          {(!subjectBreakdown || subjectBreakdown.length === 0) &&
           dashboard.subject_scores.length === 0 ? (
            <p className={styles.emptyChart}>No subjects yet.</p>
          ) : (
            <>
              {/* Bar chart */}
              {(subjectBreakdown ?? dashboard.subject_scores).length > 0 && (
                <div className={styles.chartWrap} style={{ marginBottom: 16 }}>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart
                      data={(subjectBreakdown ?? dashboard.subject_scores).map((s) => ({
                        name: s.group_name.length > 15 ? `${s.group_name.slice(0, 15)}…` : s.group_name,
                        score: s.average_score ?? 0,
                        passRate: s.pass_rate ?? 0,
                      }))}
                      margin={{ top: 8, right: 8, bottom: 4, left: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                      <Tooltip
                        formatter={(val, name) => [
                          `${Number(val ?? 0).toFixed(1)}%`,
                          name === 'score' ? 'Avg Score' : 'Pass Rate',
                        ]}
                      />
                      <Bar dataKey="score" fill="#4F46E5" radius={[3, 3, 0, 0]} name="score" />
                      <Bar dataKey="passRate" fill="#10B981" radius={[3, 3, 0, 0]} name="passRate" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
              <div className={styles.subjectList}>
                {(subjectBreakdown ?? dashboard.subject_scores).map((s) => (
                  <div key={s.group_id} className={styles.subjectItem}>
                    <div className={styles.subjectHeader}>
                      <span className={styles.subjectName}>{s.group_name}</span>
                      <span className={styles.subjectMeta}>
                        {s.assessments_taken} assessment{s.assessments_taken !== 1 ? 's' : ''}
                        {s.pass_rate != null && (
                          <Badge variant={s.pass_rate >= 70 ? 'success' : s.pass_rate >= 50 ? 'warning' : 'danger'}>
                            {s.pass_rate.toFixed(0)}% pass
                          </Badge>
                        )}
                      </span>
                    </div>
                    <div className={styles.barTrack}>
                      <div
                        className={styles.barFill}
                        style={{
                          width: `${s.average_score ?? 0}%`,
                          backgroundColor: scoreColor(s.average_score),
                        }}
                      />
                    </div>
                    <span className={styles.barLabel}>
                      {s.average_score !== null ? `${s.average_score.toFixed(1)}%` : 'N/A'}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        {/* Weak Topics */}
        <Card title="Weak Topics">
          {dashboard.weak_topics.length === 0 ? (
            <p className={styles.emptyChart}>No weak topics identified.</p>
          ) : (
            <div className={styles.topicTags}>
              {dashboard.weak_topics.map((topic) => (
                <Badge key={topic} variant="warning">{topic}</Badge>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* ── Recent Results ── */}
      <Card title="Recent Results">
        {dashboard.recent_results.length === 0 ? (
          <p className={styles.emptyChart}>No recent results.</p>
        ) : (
          <div className={styles.recentList}>
            {dashboard.recent_results.map((r) => (
              <div key={r.assessment_id} className={styles.recentItem}>
                <div className={styles.recentInfo}>
                  <span className={styles.recentDate}>{formatDate(r.date)}</span>
                  <span className={styles.recentId}>{r.assessment_id.slice(0, 8)}…</span>
                </div>
                <span
                  className={styles.recentScore}
                  style={{ color: scoreColor(r.score) }}
                >
                  {r.score.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
