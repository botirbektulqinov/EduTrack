/* ─── Teacher: Assessment List Page ─── */
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiSearch, FiPlus, FiFileText } from 'react-icons/fi';
import api from '@/lib/api';
import type { Assessment, AssessmentType } from '@/types';
import { formatDateTime } from '@/lib/utils';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import Table from '@/components/ui/Table';
import Select from '@/components/ui/Select';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import styles from './TeacherAssessmentsPage.module.scss';

const TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'test', label: 'Test' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'survey', label: 'Survey' },
  { value: 'practice', label: 'Practice' },
];

const TYPE_VARIANT: Record<AssessmentType, 'info' | 'warning' | 'success' | 'neutral'> = {
  test: 'info',
  quiz: 'warning',
  survey: 'neutral',
  practice: 'success',
};

export default function TeacherAssessmentsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['teacher', 'assessments'],
    queryFn: async () => {
      const res = await api.get('/teacher/assessments');
      return (res.data.data ?? res.data) as Assessment[];
    },
  });

  const assessments = (data ?? []).filter((a) => {
    const matchesType = typeFilter ? a.assessment_type === typeFilter : true;
    const matchesSearch = search
      ? a.title.toLowerCase().includes(search.toLowerCase())
      : true;
    return matchesType && matchesSearch;
  });

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h1>Assessments</h1>
        <Link to="/teacher/assessments/new">
          <Button icon={<FiPlus />}>Create Assessment</Button>
        </Link>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.searchWrap}>
          <FiSearch className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search assessments…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          options={TYPE_OPTIONS}
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className={styles.center}>
          <Spinner size="lg" />
        </div>
      ) : assessments.length === 0 ? (
        <EmptyState
          icon={<FiFileText size={40} />}
          title="No assessments found"
          description="Create your first assessment to get started."
        />
      ) : (
        <Table
          headers={[
            'Title',
            'Type',
            'Group',
            'Time Limit',
            'Status',
            'Available From',
            'Available Until',
          ]}
        >
          {assessments.map((a) => (
            <tr
              key={a.id}
              className={styles.row}
              onClick={() => navigate(`/teacher/assessments/${a.id}`)}
            >
              <td>{a.title}</td>
              <td>
                <Badge variant={TYPE_VARIANT[a.assessment_type]}>
                  {a.assessment_type}
                </Badge>
              </td>
              <td>{a.group_name ?? '—'}</td>
              <td>{a.time_limit_minutes ? `${a.time_limit_minutes} min` : '—'}</td>
              <td>
                <Badge variant={a.is_published ? 'success' : 'neutral'}>
                  {a.is_published ? 'Published' : 'Draft'}
                </Badge>
              </td>
              <td>{a.available_from ? formatDateTime(a.available_from) : '—'}</td>
              <td>{a.available_until ? formatDateTime(a.available_until) : '—'}</td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  );
}
