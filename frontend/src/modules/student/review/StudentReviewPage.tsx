import { useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
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
  FiCalendar,
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
  ReviewSubjectScore,
  StudentReview,
  TopicPerformance,
} from '@/types';
import styles from './StudentReviewPage.module.scss';

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
  if (value == null) return 'No baseline yet';
  if (value === 0) return 'On baseline';
  return `${value > 0 ? '+' : ''}${value.toFixed(1)} pts`;
}

export default function StudentReviewPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedPeriod = searchParams.get('period') === 'year' ? 'year' : 'semester';
  const selectedAcademicYear = searchParams.get('academic_year') ?? undefined;
  const selectedSemester = searchParams.get('semester') ?? undefined;

  const { data, isLoading, error } = useQuery<StudentReview | null>({
    queryKey: [
      'student-review',
      selectedPeriod,
      selectedAcademicYear ?? 'latest-year',
      selectedSemester ?? 'latest-semester',
    ],
    queryFn: async () => {
      const res = await api.get('/student/analytics/review', {
        params: {
          period: selectedPeriod,
          academic_year: selectedAcademicYear,
          semester: selectedPeriod === 'semester' ? selectedSemester : undefined,
        },
      });
      return (res.data.data ?? res.data) as StudentReview;
    },
    retry: false,
  });

  useEffect(() => {
    if (!error) {
      return;
    }
    const axiosErr = error as { response?: { data?: { message?: string } } };
    toast.error(axiosErr.response?.data?.message || 'Failed to load review');
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
        <p>No review data available.</p>
        <Link to="/student/dashboard">
          <Button variant="secondary">Back</Button>
        </Link>
      </div>
    );
  }

  const comparisonSummary = data.comparison_summary ?? null;
  const periodOptions = [
    { value: 'semester', label: 'Semester review' },
    { value: 'year', label: 'Whole year review' },
  ];
  const academicYearOptions = data.available_academic_years.map((year) => ({ value: year, label: year }));
  const semesterOptions = data.available_semesters.map((semester) => ({ value: semester, label: semester }));
  const trendData = data.score_trend.map((point) => ({
    label: formatDate(point.date, 'MMM d'),
    score: point.score,
    assessmentTitle: point.assessment_title ?? point.assessment_id,
  }));
  const subjectChartData = data.subject_scores.map((subject) => ({
    name: subject.subject_name.length > 18 ? `${subject.subject_name.slice(0, 18)}...` : subject.subject_name,
    student: subject.average_score ?? 0,
    peers: subject.peer_average ?? 0,
  }));

  return (
    <div className={styles.page}>
      <div className={styles.hero}>
        <div className={styles.heroCopy}>
          <Link to="/student/dashboard">
            <Button variant="ghost" icon={<FiArrowLeft />}>Back to Dashboard</Button>
          </Link>
          <h1>{data.student_name ? `${data.student_name} - Performance Review` : 'Performance Review'}</h1>
          <p>
            Review your semester or full academic year against your groups, subject cohorts,
            teacher cohorts, and the university baseline.
          </p>
        </div>

        <div className={styles.heroControls}>
          <Select
            label="Scope"
            options={periodOptions}
            value={selectedPeriod}
            onChange={(event) => {
              const next = new URLSearchParams(searchParams);
              next.set('period', event.target.value);
              if (event.target.value === 'year') {
                next.delete('semester');
              }
              setSearchParams(next);
            }}
          />
          {academicYearOptions.length > 0 && (
            <Select
              label="Academic year"
              options={academicYearOptions}
              value={data.selected_academic_year ?? academicYearOptions[0].value}
              onChange={(event) => {
                const next = new URLSearchParams(searchParams);
                next.set('academic_year', event.target.value);
                next.delete('semester');
                setSearchParams(next);
              }}
            />
          )}
          {selectedPeriod === 'semester' && semesterOptions.length > 0 && (
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
          )}
        </div>
      </div>

      <div className={styles.metricsGrid}>
        <MetricCard
          label="Average"
          value={data.overall_score_avg != null ? `${data.overall_score_avg.toFixed(1)}%` : 'N/A'}
          hint={`${data.assessments_taken} graded attempts`}
          icon={<FiTrendingUp size={20} />}
        />
        <MetricCard
          label="Pass Rate"
          value={data.pass_rate != null ? `${data.pass_rate.toFixed(1)}%` : 'N/A'}
          hint={`${data.assessments_passed} passing attempts`}
          icon={<FiAward size={20} />}
        />
        <MetricCard
          label="Group Delta"
          value={comparisonSummary?.delta_vs_peer != null ? `${comparisonSummary.delta_vs_peer > 0 ? '+' : ''}${comparisonSummary.delta_vs_peer.toFixed(1)}` : 'N/A'}
          hint={formatDelta(comparisonSummary?.delta_vs_peer)}
          icon={<FiUsers size={20} />}
        />
        <MetricCard
          label="Violations"
          value={String(data.violation_count_total)}
          hint="Proctoring events in scope"
          icon={<FiShield size={20} />}
        />
      </div>

      <Card title="Comparison Matrix">
        <div className={styles.comparisonMatrix}>
          {data.comparison_matrix.map((item: ComparisonSummary) => (
            <div key={item.key ?? item.label} className={styles.comparisonCard}>
              <div className={styles.comparisonHeading}>
                <strong>{item.label}</strong>
                <span>{item.description}</span>
              </div>
              <div className={styles.comparisonStats}>
                <div>
                  <span className={styles.comparisonLabel}>Peer Avg</span>
                  <strong>{item.peer_average != null ? `${item.peer_average.toFixed(1)}%` : 'N/A'}</strong>
                </div>
                <div>
                  <span className={styles.comparisonLabel}>Delta</span>
                  <strong>{formatDelta(item.delta_vs_peer)}</strong>
                </div>
                <div>
                  <span className={styles.comparisonLabel}>Percentile</span>
                  <strong>{item.percentile_estimate != null ? `${item.percentile_estimate.toFixed(1)}th` : 'N/A'}</strong>
                </div>
                <div>
                  <span className={styles.comparisonLabel}>Peer Count</span>
                  <strong>{item.peer_students ?? 0} students</strong>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className={styles.twoCol}>
        <Card title="Score Trend" className={styles.cardStretch}>
          {trendData.length === 0 ? (
            <p className={styles.empty}>No graded attempts yet for this scope.</p>
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

        <Card title={selectedPeriod === 'year' ? 'Semester Breakdown' : 'Scope Snapshot'} className={styles.cardStretch}>
          {selectedPeriod === 'year' ? (
            data.period_breakdown.length === 0 ? (
              <p className={styles.empty}>No semester breakdown available yet.</p>
            ) : (
              <div className={styles.chartWrapSmall}>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.period_breakdown}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                    <Bar dataKey="average_score" fill="#14B8A6" radius={[4, 4, 0, 0]} name="Average" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )
          ) : (
            <div className={styles.comparisonGrid}>
              <div className={styles.comparisonBlock}>
                <span className={styles.comparisonLabel}>Student Average</span>
                <strong>{comparisonSummary?.student_average != null ? `${comparisonSummary.student_average.toFixed(1)}%` : 'N/A'}</strong>
              </div>
              <div className={styles.comparisonBlock}>
                <span className={styles.comparisonLabel}>Group Average</span>
                <strong>{comparisonSummary?.peer_average != null ? `${comparisonSummary.peer_average.toFixed(1)}%` : 'N/A'}</strong>
              </div>
              <div className={styles.comparisonBlock}>
                <span className={styles.comparisonLabel}>Percentile</span>
                <strong>{comparisonSummary?.percentile_estimate != null ? `${comparisonSummary.percentile_estimate.toFixed(1)}th` : 'N/A'}</strong>
              </div>
              <div className={styles.comparisonBlock}>
                <span className={styles.comparisonLabel}>Improvement Rate</span>
                <strong>{data.improvement_rate != null ? data.improvement_rate.toFixed(2) : 'N/A'}</strong>
              </div>
            </div>
          )}
        </Card>
      </div>

      <div className={styles.twoCol}>
        <Card title="Subject Breakdown">
          {data.subject_scores.length === 0 ? (
            <p className={styles.empty}>No subject-level data found.</p>
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
                {data.subject_scores.map((subject: ReviewSubjectScore) => (
                  <div key={subject.subject_id} className={styles.subjectItem}>
                    <div className={styles.subjectHeader}>
                      <div>
                        <div className={styles.subjectName}>{subject.subject_name}</div>
                        <div className={styles.subjectMeta}>
                          {subject.assessments_taken} graded attempt{subject.assessments_taken !== 1 ? 's' : ''}
                        </div>
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
                            style={{ width: `${subject.peer_average ?? 0}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    <div className={styles.subjectFooter}>
                      <span>Student: {subject.average_score != null ? `${subject.average_score.toFixed(1)}%` : 'N/A'}</span>
                      <span>Peers: {subject.peer_average != null ? `${subject.peer_average.toFixed(1)}%` : 'N/A'}</span>
                      <span>{formatDelta(subject.delta_vs_peer)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        <Card title="Topic Performance">
          {data.topic_performance.length === 0 ? (
            <p className={styles.empty}>No topic-tagged answers were found in this scope.</p>
          ) : (
            <div className={styles.topicList}>
              {data.topic_performance.map((topic: TopicPerformance) => (
                <div key={topic.topic} className={styles.topicItem}>
                  <div className={styles.topicHeader}>
                    <div>
                      <div className={styles.topicName}>{topic.topic}</div>
                      <div className={styles.topicMeta}>
                        {topic.attempts} response{topic.attempts !== 1 ? 's' : ''}
                      </div>
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
          {data.insights.length > 0 ? (
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
            <p className={styles.empty}>No recent graded submissions in this scope.</p>
          ) : (
            <div className={styles.resultList}>
              {data.recent_results.map((result) => (
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
          <div><FiCalendar size={16} /> Academic year: {data.selected_academic_year ?? 'N/A'}</div>
          {selectedPeriod === 'semester' && <div><FiBookOpen size={16} /> Semester: {data.selected_semester ?? 'N/A'}</div>}
          <div><FiUsers size={16} /> Comparison matrix excludes your own attempts from peer baselines.</div>
          <div><FiBarChart2 size={16} /> Topic insights depend on questions having curriculum topics or topic tags.</div>
        </div>
      </Card>
    </div>
  );
}
