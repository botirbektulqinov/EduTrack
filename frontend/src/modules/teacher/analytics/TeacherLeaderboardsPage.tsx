/* ─── Teacher: Leaderboards (group / teacher / university) ─── */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import Select from '@/components/ui/Select';
import styles from './TeacherLeaderboardsPage.module.scss';
import type { User } from '@/types';

const SCOPE_OPTIONS = [
  { value: 'group', label: 'Group' },
  { value: 'teacher', label: "Teacher's Groups" },
  { value: 'university', label: 'University' },
];

export default function TeacherLeaderboardsPage() {
  const [scope, setScope] = useState('group');

  const { data, isLoading } = useQuery<User[], Error, User[]>({
    queryKey: ['teacher', 'leaderboards', scope],
    queryFn: async () => {
      const res = await api.get(`/teacher/leaderboards`, { params: { scope } });
      return (res.data.data ?? res.data) as User[];
    },
  });

  return (
    <div className={styles.page}>
      <h1>Leaderboards</h1>
      <div className={styles.controls}>
        <Select
          label="Scope"
          options={SCOPE_OPTIONS}
          value={scope}
          onChange={(e) => setScope((e.target as HTMLSelectElement).value)}
        />
      </div>

      {isLoading ? (
        <div className={styles.center}><Spinner size="lg" /></div>
      ) : (
        <Card title={`Top students — ${scope}`}>
          <ol>
            {(data ?? []).slice(0, 50).map((u: User) => (
              <li key={u.id}>{u.full_name} — {u.student_id_number ?? u.email}</li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}
