import { useEffect } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  FiArrowLeft,
  FiAward,
  FiBarChart2,
  FiBookOpen,
  FiShield,
  FiTrendingUp,
  FiUsers,
} from 'react-icons/fi';
import toast from 'react-hot-toast';
import api from '@/lib/api';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Select from '@/components/ui/Select';
import Spinner from '@/components/ui/Spinner';
import { formatDate, formatDateTime, scoreColor } from '@/lib/utils';
import type {
  ComparisonSummary,
  ScoreTrendPoint,
  StudentDashboard,
  SubjectScore,
  TopicPerformance,
} from '@/types';
import styles from './TeacherStudentSemesterPerformancePage.module.scss';

interface MetricCardProps {
  label: string;
  value: string;
  hint: string;
  icon: React.ReactNode;
}

function MetricCard({ label, value, hint, icon }: MetricCardProps) {
  return (
    <div className={styles.metricCard}>
      <div className={styles.metricIcon}>{icon}</div>
      <div>
        <div className={styles.metricValue}>{value}</div>
        <div className={styles.metricLabel}>{label}</div>
        <div className={styles.metricHint}>{hint}</div>
      </div>
    </div>
  );
}

function formatDelta(value: number | null | undefined) {
  if (value == null) return 'No peer baseline yet';
  if (value === 0) return 'On par with peer average';
  return `${value > 0 ? '+' : ''}${value.toFixed(1)} pts vs peers`;
}

export default function TeacherStudentSemesterPerformancePage() {
  const { id: studentId } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedSemester = searchParams.get('semester') ?? undefined;

  const { data, isLoading, error } = useQuery<StudentDashboard | null>({
    queryKey: ['teacher', 'student', studentId, 'semester-performance', selectedSemester ?? 'latest'],
    queryFn: async () => {
      if (!studentId) return null;
      const res = await api.get(`/teacher/students/${studentId}/semester-performance`, {
        params: selectedSemester ? { semester: selectedSemester } : undefined,
      });
      return (res.data.data ?? res.data) as StudentDashboard;
    },
    enabled: !!studentId,
    retry: false,
  });

  useEffect(() => {
    if (!error) return;
    const axiosErr = error as { response?: { data?: { message?: string } } };
    toast.error(axiosErr.response?.data?.message || 'Failed to load performance');
  }, [error]);

  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

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

  const trendData = data.score_trend.map((point) => ({
    label: formatDate(point.date, 'MMM d'),
    score: point.score,
    assessmentTitle: point.assessment_title ?? point.assessment_id,
  }));

  const subjectChartData = data.subject_scores.map((subject) => ({
    name: subject.group_name.length > 18 ? `${subject.group_name.slice(0, 18)}...` : subject.group_name,
    student: subject.average_score ?? 0,
    peers: subject.group_average ?? 0,
  }));

  const comparison = data.comparison_summary as ComparisonSummary | undefined;
  const topicPerformance = data.topic_performance ?? [];
  const semesterOptions = (data.available_semesters ?? []).map((semester) => ({
    value: semester,
    label: semester,
  }));
  const heading = data.student_name ? `${data.student_name} - Semester Performance` : 'Semester Performance';

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div className={styles.heroCopy}>
          <Link to="/teacher/dashboard">
            <Button variant="ghost" icon={<FiArrowLeft />}>Back to Dashboard</Button>
          </Link>
          <h1>{heading}</h1>
          <p>
            Teacher-facing review of semester outcomes, subject balance, peer comparison,
            and topic-level weak spots.
          </p>
        </div>

        {semesterOptions.length > 0 && (
          <div className={styles.heroControls}>
            <Select
              label="Semester"
              options={semesterOptions}
              value={data.selected_semester ?? semesterOptions[0].value}
              onChange={(event) => {
                const next = new URLSearchParams(searchParams);
                next.set('semester', event.target.value);
                setSearchParams(next);
              }}
            />
          </div>
        )}
      </div>

      <div className={styles.metricsGrid}>
        <MetricCard
          label="Semester Average"
          value={data.overall_score_avg != null ? `${data.overall_score_avg.toFixed(1)}%` : 'N/A'}
          hint={`${data.assessments_taken} graded attempts in scope`}
          icon={<FiTrendingUp size={20} />}
        />
        <MetricCard
          label="Pass Rate"
          value={data.pass_rate != null ? `${data.pass_rate.toFixed(1)}%` : 'N/A'}
          hint={`${data.assessments_passed} passing attempts`}
          icon={<FiAward size={20} />}
        />
        <MetricCard
          label="Peer Delta"
          value={comparison?.delta_vs_peer != null ? `${comparison.delta_vs_peer > 0 ? '+' : ''}${comparison.delta_vs_peer.toFixed(1)}` : 'N/A'}
          hint={formatDelta(comparison?.delta_vs_peer)}
          icon={<FiUsers size={20} />}
        />
        <MetricCard
          label="Violations"
          value={String(data.violation_count_total)}
          hint="Proctoring events this semester"
          icon={<FiShield size={20} />}
        />
      </div>

      <div className={styles.twoCol}>
        <Card title="Score Trend" className={styles.cardStretch}>
          {trendData.length === 0 ? (
            <p className={styles.empty}>No graded attempts yet for this semester.</p>
          ) : (
            <div className={styles.chartWrap}>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Score']}
                    labelFormatter={(_, payload) => {
                      const point = payload?.[0]?.payload as { assessmentTitle?: string } | undefined;
                      return point?.assessmentTitle ?? '';
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#4F46E5"
                    strokeWidth={3}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card title="Comparison Snapshot" className={styles.cardStretch}>
          <div className={styles.comparisonGrid}>
            <div className={styles.comparisonBlock}>
              <span className={styles.comparisonLabel}>Student Average</span>
              <strong>{comparison?.student_average != null ? `${comparison.student_average.toFixed(1)}%` : 'N/A'}</strong>
            </div>
            <div className={styles.comparisonBlock}>
              <span className={styles.comparisonLabel}>Peer Average</span>
              <strong>{comparison?.peer_average != null ? `${comparison.peer_average.toFixed(1)}%` : 'N/A'}</strong>
            </div>
            <div className={styles.comparisonBlock}>
              <span className={styles.comparisonLabel}>Percentile Estimate</span>
              <strong>{comparison?.percentile_estimate != null ? `${comparison.percentile_estimate.toFixed(1)}th` : 'N/A'}</strong>
            </div>
            <div className={styles.comparisonBlock}>
              <span className={styles.comparisonLabel}>Improvement Rate</span>
              <strong>{data.improvement_rate != null ? data.improvement_rate.toFixed(2) : 'N/A'}</strong>
            </div>
          </div>

          <div className={styles.insightBanner}>
            <FiBarChart2 size={18} />
            <span>{formatDelta(comparison?.delta_vs_peer)}</span>
          </div>
        </Card>
      </div>

      <div className={styles.twoCol}>
        <Card title="Subject Breakdown">
          {data.subject_scores.length === 0 ? (
            <p className={styles.empty}>No subject-level semester data found.</p>
          ) : (
            <>
              <div className={styles.chartWrapSmall}>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={subjectChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                    <Bar dataKey="student" fill="#4F46E5" radius={[4, 4, 0, 0]} name="Student" />
                    <Bar dataKey="peers" fill="#14B8A6" radius={[4, 4, 0, 0]} name="Peers" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className={styles.subjectList}>
                {data.subject_scores.map((subject: SubjectScore) => (
                  <div key={subject.group_id} className={styles.subjectItem}>
                    <div className={styles.subjectHeader}>
                      <div>
                        <div className={styles.subjectName}>{subject.subject}</div>
                        <div className={styles.subjectMeta}>{subject.group_name}</div>
                      </div>
                      <Badge variant={subject.pass_rate != null && subject.pass_rate >= 70 ? 'success' : subject.pass_rate != null && subject.pass_rate >= 50 ? 'warning' : 'danger'}>
                        {subject.pass_rate != null ? `${subject.pass_rate.toFixed(0)}% pass` : 'No pass rate'}
                      </Badge>
                    </div>

                    <div className={styles.subjectBars}>
                      <div>
                        <span className={styles.barLegend}>Student</span>
                        <div className={styles.barTrack}>
                          <div
                            className={styles.barFill}
                            style={{ width: `${subject.average_score ?? 0}%`, backgroundColor: scoreColor(subject.average_score ?? null) }}
                          />
                        </div>
                      </div>
                      <div>
                        <span className={styles.barLegend}>Peers</span>
                        <div className={styles.barTrackMuted}>
                          <div
                            className={styles.barFillMuted}
                            style={{ width: `${subject.group_average ?? 0}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    <div className={styles.subjectFooter}>
                      <span>Student: {subject.average_score != null ? `${subject.average_score.toFixed(1)}%` : 'N/A'}</span>
                      <span>Peers: {subject.group_average != null ? `${subject.group_average.toFixed(1)}%` : 'N/A'}</span>
                      <span>{formatDelta(subject.delta_from_group_avg)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        <Card title="Topic Performance">
          {topicPerformance.length === 0 ? (
            <p className={styles.empty}>No topic-tagged answers were found for this semester.</p>
          ) : (
            <div className={styles.topicList}>
              {topicPerformance.map((topic: TopicPerformance) => (
                <div key={topic.topic} className={styles.topicItem}>
                  <div className={styles.topicHeader}>
                    <div>
                      <div className={styles.topicName}>{topic.topic}</div>
                      <div className={styles.topicMeta}>{topic.attempts} question response{topic.attempts !== 1 ? 's' : ''}</div>
                    </div>
                    <Badge variant={topic.needs_attention ? 'warning' : 'success'}>
                      {topic.needs_attention ? 'Needs attention' : 'Stable'}
                    </Badge>
                  </div>

                  <div className={styles.barTrack}>
                    <div
                      className={styles.barFill}
                      style={{ width: `${topic.average_score}%`, backgroundColor: scoreColor(topic.average_score) }}
                    />
                  </div>

                  <div className={styles.topicFooter}>
                    <span>{topic.average_score.toFixed(1)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className={styles.weakTopics}>
            <h4>Weak Topics</h4>
            {data.weak_topics.length === 0 ? (
              <p className={styles.emptyInline}>No weak topics flagged.</p>
            ) : (
              <div className={styles.badges}>
                {data.weak_topics.map((topic) => (
                  <Badge key={topic} variant="warning">{topic}</Badge>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>

      <div className={styles.twoCol}>
        <Card title="Actionable Insights">
          {data.insights && data.insights.length > 0 ? (
            <ul className={styles.insightList}>
              {data.insights.map((insight) => (
                <li key={insight}>{insight}</li>
              ))}
            </ul>
          ) : (
            <p className={styles.empty}>No additional insights yet.</p>
          )}
        </Card>

        <Card title="Recent Results">
          {data.recent_results.length === 0 ? (
            <p className={styles.empty}>No recent graded submissions in this semester.</p>
          ) : (
            <div className={styles.resultList}>
              {data.recent_results.map((result: ScoreTrendPoint) => (
                <div key={`${result.assessment_id}-${result.date}`} className={styles.resultItem}>
                  <div>
                    <div className={styles.resultTitle}>{result.assessment_title ?? result.assessment_id}</div>
                    <div className={styles.resultMeta}>
                      {result.subject ? `${result.subject} | ` : ''}
                      {formatDateTime(result.date)}
                    </div>
                  </div>
                  <div className={styles.resultScoreWrap}>
                    <span className={styles.resultScore} style={{ color: scoreColor(result.score) }}>
                      {result.score.toFixed(1)}%
                    </span>
                    {result.passed != null && (
                      <Badge variant={result.passed ? 'success' : 'danger'}>
                        {result.passed ? 'Pass' : 'Fail'}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="Scope Notes">
        <div className={styles.scopeNotes}>
          <div><FiBookOpen size={16} /> Semester: {data.selected_semester ?? 'N/A'}</div>
          <div><FiUsers size={16} /> Peer comparison uses other graded attempts from the same semester scope.</div>
          <div><FiBarChart2 size={16} /> Topic insights depend on questions having a `topic_tag` and graded answer data.</div>
        </div>
      </Card>
    </div>
  );
}
