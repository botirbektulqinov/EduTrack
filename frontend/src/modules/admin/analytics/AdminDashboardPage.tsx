/* ─── Admin: Analytics Dashboard Page ─── */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import { FiUsers, FiBook, FiLayers, FiCheckCircle, FiDownload } from 'react-icons/fi';
import toast from 'react-hot-toast';
import api from '@/lib/api';
import type { AdminOverview } from '@/types';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import Table from '@/components/ui/Table';
import Spinner from '@/components/ui/Spinner';
import Select from '@/components/ui/Select';
import styles from './AdminDashboardPage.module.scss';

/* ── Chart palette ── */
const PIE_COLORS = ['#10B981', '#EF4444'];
const BAR_COLOR = '#4F46E5';

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

export default function AdminDashboardPage() {
  const [exportFormat, setExportFormat] = useState('csv');

  const { data: overview, isLoading } = useQuery({
    queryKey: ['admin-overview'],
    queryFn: async () => {
      const res = await api.get('/admin/analytics/overview');
      return (res.data.data ?? res.data) as AdminOverview;
    },
  });

  /* ── Fetch violations from dedicated endpoint ── */
  const { data: violationDetail } = useQuery({
    queryKey: ['admin-violations'],
    queryFn: async () => {
      const res = await api.get('/admin/analytics/violations');
      return (res.data.data ?? res.data) as Record<string, number>;
    },
  });

  /* ── Export handler ── */
  const handleExport = async (reportType: string) => {
    try {
      const res = await api.get('/admin/reports/export', {
        params: { format: exportFormat, report_type: reportType },
        responseType: exportFormat === 'csv' ? 'blob' : 'json',
      });
      if (exportFormat === 'csv') {
        const blob = new Blob([res.data], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `edutrack_${reportType}_report.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        toast.success('Report downloaded');
      } else {
        // JSON — just download as JSON file
        const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `edutrack_${reportType}_report.json`;
        a.click();
        window.URL.revokeObjectURL(url);
        toast.success('Report downloaded');
      }
    } catch {
      toast.error('Failed to export report');
    }
  };

  if (isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!overview) {
    return (
      <div className={styles.center}>
        <p>Failed to load dashboard data.</p>
      </div>
    );
  }

  /* ── Derived data ── */
  const passRate = overview.university_pass_rate ?? 0;
  const pieData = [
    { name: 'Pass', value: passRate },
    { name: 'Fail', value: 100 - passRate },
  ];

  const violationData = Object.entries(overview.violation_summary ?? {}).map(([type, count]) => ({
    type: type.replace(/_/g, ' '),
    count,
  }));

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Admin Dashboard</h1>

      {/* Stat cards */}
      <div className={styles.statsGrid}>
        <StatCard
          icon={<FiUsers size={24} />}
          label="Total Students"
          value={overview.total_students}
          color="#10B981"
        />
        <StatCard
          icon={<FiUsers size={24} />}
          label="Total Teachers"
          value={overview.total_teachers}
          color="#F59E0B"
        />
        <StatCard
          icon={<FiLayers size={24} />}
          label="Total Groups"
          value={overview.total_groups}
          color="#4F46E5"
        />
        <StatCard
          icon={<FiBook size={24} />}
          label="Total Assessments"
          value={overview.total_assessments}
          color="#8B5CF6"
        />
        <StatCard
          icon={<FiCheckCircle size={24} />}
          label="University Pass Rate"
          value={passRate !== null ? `${passRate.toFixed(1)}%` : 'N/A'}
          color="#10B981"
        />
      </div>

      {/* Charts */}
      <div className={styles.chartsGrid}>
        {/* Pass/Fail Pie */}
        <Card title="Pass / Fail Ratio">
          <div className={styles.chartWrap}>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                >
                  {pieData.map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx]} />
                  ))}
                </Pie>
                <Tooltip formatter={(val) => `${Number(val).toFixed(1)}%`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Violation Bar Chart */}
        <Card title="Violation Summary">
          {violationData.length === 0 ? (
            <p className={styles.emptyChart}>No violations recorded.</p>
          ) : (
            <div className={styles.chartWrap}>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={violationData} layout="vertical" margin={{ left: 120 }}>
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis
                    type="category"
                    dataKey="type"
                    tick={{ fontSize: 12 }}
                    width={120}
                  />
                  <Tooltip />
                  <Bar dataKey="count" fill={BAR_COLOR} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      {/* Violations Detail Table (from /analytics/violations endpoint) */}
      {violationDetail && Object.keys(violationDetail).length > 0 && (
        <Card title="Violations Breakdown">
          <Table headers={['Violation Type', 'Count', 'Severity']}>
            {Object.entries(violationDetail)
              .sort(([, a], [, b]) => b - a)
              .map(([type, count]) => (
                <tr key={type}>
                  <td>{type.replace(/_/g, ' ')}</td>
                  <td><strong>{count}</strong></td>
                  <td>
                    <Badge variant={count > 10 ? 'danger' : count > 3 ? 'warning' : 'success'}>
                      {count > 10 ? 'High' : count > 3 ? 'Medium' : 'Low'}
                    </Badge>
                  </td>
                </tr>
              ))}
          </Table>
        </Card>
      )}

      {/* Export Reports */}
      <Card title="Export Reports">
        <div className={styles.exportSection}>
          <Select
            label="Format"
            options={[
              { value: 'csv', label: 'CSV' },
              { value: 'json', label: 'JSON' },
            ]}
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
          />
          <div className={styles.exportButtons}>
            <Button variant="secondary" icon={<FiDownload />} onClick={() => handleExport('users')}>
              Users
            </Button>
            <Button variant="secondary" icon={<FiDownload />} onClick={() => handleExport('groups')}>
              Groups
            </Button>
            <Button variant="secondary" icon={<FiDownload />} onClick={() => handleExport('assessments')}>
              Assessments
            </Button>
            <Button variant="secondary" icon={<FiDownload />} onClick={() => handleExport('results')}>
              Results
            </Button>
            <Button variant="secondary" icon={<FiDownload />} onClick={() => handleExport('violations')}>
              Violations
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
