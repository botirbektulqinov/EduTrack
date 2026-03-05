/* ─── Teacher: Analytics Dashboard Page ─── */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { FiTrendingUp, FiCheckCircle, FiFileText, FiAward } from 'react-icons/fi';
import api from '@/lib/api';
import type { Assessment, AssessmentAttempt, GroupAnalytics } from '@/types';
import Card from '@/components/ui/Card';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import styles from './TeacherDashboardPage.module.scss';

interface AssessmentWithStats extends Assessment {
  attempts_count?: number;
  mean_score?: number | null;
  pass_rate?: number | null;
}

export default function TeacherDashboardPage() {
  const [selectedGroupId, setSelectedGroupId] = useState('');

  /* ── Fetch teacher's assessments ── */
  const { data: assessments, isLoading } = useQuery({
    queryKey: ['teacher', 'assessments'],
    queryFn: async () => {
      const res = await api.get('/teacher/assessments');
      return (res.data.data ?? res.data) as AssessmentWithStats[];
    },
  });

  /* ── Fetch attempts for all assessments to compute stats ── */
  const assessmentIds = useMemo(
    () => (assessments ?? []).map((a) => a.id),
    [assessments],
  );

  const { data: allAttempts } = useQuery({
    queryKey: ['teacher', 'all-attempts', assessmentIds],
    queryFn: async () => {
      const results: Record<string, AssessmentAttempt[]> = {};
      await Promise.all(
        assessmentIds.map(async (aid) => {
          try {
            const res = await api.get(`/teacher/assessments/${aid}/attempts`);
            results[aid] = (res.data.data ?? res.data) as AssessmentAttempt[];
          } catch {
            results[aid] = [];
          }
        }),
      );
      return results;
    },
    enabled: assessmentIds.length > 0,
  });

  /* ── Fetch teacher groups ── */
  interface GroupOption { id: string; name: string }
  const { data: groups } = useQuery({
    queryKey: ['teacher', 'groups'],
    queryFn: async () => {
      const res = await api.get('/teacher/assessments/groups');
      return (res.data.data ?? res.data) as GroupOption[];
    },
  });

  /* ── Group analytics (lazy) ── */
  const { data: groupAnalytics, isLoading: groupAnalyticsLoading } = useQuery({
    queryKey: ['teacher', 'group-analytics', selectedGroupId],
    queryFn: async () => {
      const res = await api.get(`/teacher/groups/${selectedGroupId}/analytics`);
      return (res.data.data ?? res.data) as GroupAnalytics;
    },
    enabled: !!selectedGroupId,
  });

  /* ── Compute aggregate stats ── */
  const stats = useMemo(() => {
    const list = assessments ?? [];
    const attemptsMap = allAttempts ?? {};

    let totalAttempts = 0;
    let scoredCount = 0;
    let scoreSum = 0;
    let passedCount = 0;

    for (const a of list) {
      const attempts = attemptsMap[a.id] ?? [];
      totalAttempts += attempts.length;
      for (const att of attempts) {
        if (att.score_percent != null) {
          scoredCount++;
          scoreSum += att.score_percent;
          if (att.score_percent >= (a.passing_score ?? 50)) {
            passedCount++;
          }
        }
      }
    }

    const avgScore = scoredCount > 0 ? scoreSum / scoredCount : 0;
    const passRate = scoredCount > 0 ? (passedCount / scoredCount) * 100 : 0;

    return {
      totalAssessments: list.length,
      totalAttempts,
      avgScore,
      passRate,
    };
  }, [assessments, allAttempts]);

  /* ── Chart data ── */
  const chartData = useMemo(() => {
    const list = assessments ?? [];
    const attemptsMap = allAttempts ?? {};

    return list.map((a) => {
      const attempts = attemptsMap[a.id] ?? [];
      const scored = attempts.filter((att) => att.score_percent != null);
      const meanScore =
        scored.length > 0
          ? scored.reduce((s, att) => s + (att.score_percent ?? 0), 0) / scored.length
          : 0;
      return {
        title: a.title.length > 20 ? `${a.title.slice(0, 20)}…` : a.title,
        mean_score: Math.round(meanScore * 10) / 10,
        assessmentId: a.id,
      };
    });
  }, [assessments, allAttempts]);

  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1>Analytics Dashboard</h1>

      {/* Stat cards */}
      <div className={styles.statsGrid}>
        <Card className={styles.statCard}>
          <FiFileText className={styles.statIcon} />
          <div className={styles.statValue}>{stats.totalAssessments}</div>
          <div className={styles.statLabel}>Total Assessments</div>
        </Card>
        <Card className={styles.statCard}>
          <FiTrendingUp className={styles.statIcon} />
          <div className={styles.statValue}>{stats.totalAttempts}</div>
          <div className={styles.statLabel}>Total Attempts</div>
        </Card>
        <Card className={styles.statCard}>
          <FiAward className={styles.statIcon} />
          <div className={styles.statValue}>{stats.avgScore.toFixed(1)}%</div>
          <div className={styles.statLabel}>Average Score</div>
        </Card>
        <Card className={styles.statCard}>
          <FiCheckCircle className={styles.statIcon} />
          <div className={styles.statValue}>{stats.passRate.toFixed(1)}%</div>
          <div className={styles.statLabel}>Pass Rate</div>
        </Card>
      </div>

      {/* Bar chart */}
      {chartData.length === 0 ? (
        <EmptyState
          icon={<FiTrendingUp size={40} />}
          title="No data yet"
          description="Create assessments and wait for student submissions to see analytics."
        />
      ) : (
        <Card title="Mean Score by Assessment" className={styles.chartSection}>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={chartData} margin={{ top: 8, right: 16, bottom: 40, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis
                dataKey="title"
                tick={{ fontSize: 12 }}
                angle={-30}
                textAnchor="end"
                height={70}
              />
              <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
              <Tooltip
                formatter={(value) => [`${value}%`, 'Mean Score']}
                contentStyle={{ borderRadius: 8, fontSize: 13 }}
              />
              <Bar dataKey="mean_score" fill="#4F46E5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Assessment list with links */}
      {(assessments ?? []).length > 0 && (
        <Card title="Assessments Overview">
          <div className={styles.assessmentList}>
            {(assessments ?? []).map((a) => {
              const attempts = allAttempts?.[a.id] ?? [];
              const scored = attempts.filter((att) => att.score_percent != null);
              const mean =
                scored.length > 0
                  ? scored.reduce((s, att) => s + (att.score_percent ?? 0), 0) /
                    scored.length
                  : null;
              return (
                <Link
                  key={a.id}
                  to={`/teacher/assessments/${a.id}/results`}
                  className={styles.assessmentRow}
                >
                  <span className={styles.assessmentTitle}>{a.title}</span>
                  <span className={styles.assessmentMeta}>
                    {attempts.length} attempt{attempts.length !== 1 ? 's' : ''}
                    {mean != null && ` · Avg: ${mean.toFixed(1)}%`}
                  </span>
                </Link>
              );
            })}
          </div>
        </Card>
      )}

      {/* Group Analytics */}
      {(groups ?? []).length > 0 && (
        <Card title="Group Analytics">
          <div className={styles.groupSelector}>
            <Select
              options={[
                { value: '', label: 'Select a group…' },
                ...(groups ?? []).map((g) => ({ value: g.id, label: g.name })),
              ]}
              value={selectedGroupId}
              onChange={(e) => setSelectedGroupId(e.target.value)}
            />
          </div>
          {selectedGroupId && groupAnalyticsLoading && (
            <div className={styles.center}>
              <Spinner />
            </div>
          )}
          {selectedGroupId && groupAnalytics && !groupAnalyticsLoading && (
            <div className={styles.groupDetails}>
              <div className={styles.groupStatsRow}>
                <div className={styles.groupStat}>
                  <span className={styles.groupStatValue}>{groupAnalytics.total_students_enrolled}</span>
                  <span className={styles.groupStatLabel}>Students</span>
                </div>
                <div className={styles.groupStat}>
                  <span className={styles.groupStatValue}>{groupAnalytics.total_assessments}</span>
                  <span className={styles.groupStatLabel}>Assessments</span>
                </div>
                <div className={styles.groupStat}>
                  <span className={styles.groupStatValue}>
                    {groupAnalytics.average_score != null ? `${groupAnalytics.average_score.toFixed(1)}%` : 'N/A'}
                  </span>
                  <span className={styles.groupStatLabel}>Avg Score</span>
                </div>
                <div className={styles.groupStat}>
                  <span className={styles.groupStatValue}>
                    {groupAnalytics.overall_pass_rate != null ? `${groupAnalytics.overall_pass_rate.toFixed(1)}%` : 'N/A'}
                  </span>
                  <span className={styles.groupStatLabel}>Pass Rate</span>
                </div>
              </div>
              {groupAnalytics.assessment_summaries.length > 0 && (
                <div className={styles.groupAssessments}>
                  {groupAnalytics.assessment_summaries.map((s) => (
                    <Link
                      key={s.assessment_id}
                      to={`/teacher/assessments/${s.assessment_id}/results`}
                      className={styles.assessmentRow}
                    >
                      <span className={styles.assessmentTitle}>{s.title}</span>
                      <span className={styles.assessmentMeta}>
                        {s.attempts_count} attempt{s.attempts_count !== 1 ? 's' : ''}
                        {s.mean_score != null && ` · Avg: ${s.mean_score.toFixed(1)}%`}
                        {s.pass_rate != null && (
                          <Badge variant={s.pass_rate >= 70 ? 'success' : s.pass_rate >= 50 ? 'warning' : 'danger'}>
                            {s.pass_rate.toFixed(0)}% pass
                          </Badge>
                        )}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
