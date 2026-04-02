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

  const assessments = (data ?? []).filter((assessment) => {
    const matchesType = typeFilter ? assessment.assessment_type === typeFilter : true;
    const haystack = [
      assessment.title,
      assessment.subject_name,
      assessment.group_subject_name,
      assessment.group_name,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    const matchesSearch = search ? haystack.includes(search.toLowerCase()) : true;
    return matchesType && matchesSearch;
  });

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Assessments</h1>
        <Link to="/teacher/assessments/new">
          <Button icon={<FiPlus />}>Create Assessment</Button>
        </Link>
      </div>

      <div className={styles.filters}>
        <div className={styles.searchWrap}>
          <FiSearch className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search assessments..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <Select options={TYPE_OPTIONS} value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} />
      </div>

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
            'Subject',
            'Group',
            'Time Limit',
            'Status',
            'Available From',
            'Available Until',
          ]}
        >
          {assessments.map((assessment) => (
            <tr
              key={assessment.id}
              className={styles.row}
              onClick={() => navigate(`/teacher/assessments/${assessment.id}`)}
            >
              <td>{assessment.title}</td>
              <td>
                <Badge variant={TYPE_VARIANT[assessment.assessment_type]}>
                  {assessment.assessment_type}
                </Badge>
              </td>
              <td>{assessment.subject_name ?? assessment.group_subject_name ?? '—'}</td>
              <td>{assessment.group_name ?? '—'}</td>
              <td>{assessment.time_limit_minutes ? `${assessment.time_limit_minutes} min` : '—'}</td>
              <td>
                <Badge variant={assessment.is_published ? 'success' : 'neutral'}>
                  {assessment.is_published ? 'Published' : 'Draft'}
                </Badge>
              </td>
              <td>{assessment.available_from ? formatDateTime(assessment.available_from) : '—'}</td>
              <td>{assessment.available_until ? formatDateTime(assessment.available_until) : '—'}</td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  );
}
