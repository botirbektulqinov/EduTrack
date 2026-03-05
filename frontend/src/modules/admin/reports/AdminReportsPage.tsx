/* ─── Admin: Reports / Export Page ─── */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { FiDownload, FiFileText } from 'react-icons/fi';
import api from '@/lib/api';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Card from '@/components/ui/Card';
import styles from './AdminReportsPage.module.scss';

/* ── Schema ── */
const reportSchema = z.object({
  report_type: z.string().min(1, 'Select a report type'),
  format: z.string().min(1, 'Select a format'),
  date_from: z.string().optional(),
  date_to: z.string().optional(),
});

type ReportForm = z.infer<typeof reportSchema>;

export default function AdminReportsPage() {
  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ReportForm>({
    resolver: zodResolver(reportSchema),
    defaultValues: { report_type: 'users', format: 'csv' },
  });

  const onSubmit = async (data: ReportForm) => {
    setLoading(true);
    setDownloadUrl(null);

    try {
      const params: Record<string, string> = {
        report_type: data.report_type,
        format: data.format,
      };

      // Build period string
      if (data.date_from && data.date_to) {
        params.period = `${data.date_from}:${data.date_to}`;
      }

      if (data.format === 'json') {
        // JSON — download as .json file
        const res = await api.get('/admin/reports/export', { params });
        const jsonData = res.data.data ?? res.data;
        const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        setDownloadUrl(url);

        const a = document.createElement('a');
        a.href = url;
        a.download = `edutrack_${data.report_type}_report.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        toast.success('JSON report downloaded!');
      } else {
        // CSV / other — download via blob
        const res = await api.get('/admin/reports/export', {
          params,
          responseType: 'blob',
        });

        const blob = new Blob([res.data], { type: res.headers['content-type'] || 'text/csv' });
        const url = URL.createObjectURL(blob);
        setDownloadUrl(url);

        // Auto-trigger download
        const a = document.createElement('a');
        a.href = url;
        a.download = `edutrack_${data.report_type}_report.${data.format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        toast.success('Report downloaded!');
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } }).response?.data?.message ||
        'Failed to generate report';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Reports & Export</h1>

      <Card title="Generate Report" className={styles.reportCard}>
        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          <div className={styles.formGrid}>
            <Select
              label="Report Type"
              options={[
                { value: 'users', label: 'Users' },
                { value: 'groups', label: 'Groups' },
                { value: 'assessments', label: 'Assessments' },
                { value: 'results', label: 'Results' },
                { value: 'violations', label: 'Violations' },
              ]}
              error={errors.report_type?.message}
              {...register('report_type')}
            />
            <Select
              label="Format"
              options={[
                { value: 'csv', label: 'CSV' },
                { value: 'json', label: 'JSON' },
              ]}
              error={errors.format?.message}
              {...register('format')}
            />
            <Input
              label="Date From"
              type="date"
              error={errors.date_from?.message}
              {...register('date_from')}
            />
            <Input
              label="Date To"
              type="date"
              error={errors.date_to?.message}
              {...register('date_to')}
            />
          </div>

          <div className={styles.formActions}>
            <Button type="submit" icon={<FiDownload />} loading={loading}>
              Generate Report
            </Button>
          </div>
        </form>
      </Card>

      {downloadUrl && (
        <Card className={styles.downloadCard}>
          <div className={styles.downloadContent}>
            <FiFileText size={24} />
            <p>Your report is ready.</p>
            <a href={downloadUrl} download className={styles.downloadLink}>
              Download again
            </a>
          </div>
        </Card>
      )}
    </div>
  );
}
