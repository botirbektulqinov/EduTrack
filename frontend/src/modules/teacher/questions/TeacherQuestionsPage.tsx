/* ─── Teacher: Questions Management Page ─── */
import { useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import {
  FiArrowLeft,
  FiPlus,
  FiEdit2,
  FiTrash2,
  FiUpload,
  FiX,
} from 'react-icons/fi';
import api from '@/lib/api';
import type {
  Assessment,
  Question,
  QuestionCreate,
  QuestionType,
  Difficulty,
} from '@/types';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Textarea from '@/components/ui/Textarea';
import Modal from '@/components/ui/Modal';
import ConfirmModal from '@/components/ui/ConfirmModal';
import Spinner from '@/components/ui/Spinner';
import styles from './TeacherQuestionsPage.module.scss';

/* ── Constants ── */
const QUESTION_TYPE_OPTIONS: { value: QuestionType; label: string }[] = [
  { value: 'true_false', label: 'True / False' },
  { value: 'yes_no', label: 'Yes / No' },
  { value: 'mcq_single', label: 'MCQ — Single' },
  { value: 'mcq_multi', label: 'MCQ — Multiple' },
  { value: 'image_mcq', label: 'Image MCQ' },
  { value: 'short_answer', label: 'Short Answer' },
  { value: 'essay', label: 'Essay' },
  { value: 'fill_blank', label: 'Fill in the Blank' },
  { value: 'numeric', label: 'Numeric' },
  { value: 'matching', label: 'Matching' },
  { value: 'ordering', label: 'Ordering' },
  { value: 'categorization', label: 'Categorization' },
  { value: 'hotspot', label: 'Hotspot' },
  { value: 'code', label: 'Code' },
  { value: 'audio_video', label: 'Audio / Video' },
  { value: 'likert', label: 'Likert Scale' },
];

const DIFFICULTY_OPTIONS: { value: Difficulty; label: string }[] = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
];

const MCQ_TYPES: QuestionType[] = [
  'mcq_single',
  'mcq_multi',
  'image_mcq',
  'true_false',
  'yes_no',
];

const difficultyVariant: Record<Difficulty, 'success' | 'warning' | 'danger'> =
  {
    easy: 'success',
    medium: 'warning',
    hard: 'danger',
  };

/* ── Zod schema ── */
const optionSchema = z.object({
  content: z.string().min(1, 'Option text is required'),
  is_correct: z.boolean(),
});

const questionSchema = z.object({
  question_type: z.string().min(1, 'Type is required'),
  content: z.string().min(1, 'Question content is required'),
  points: z.coerce.number().positive('Points must be > 0'),
  difficulty: z.enum(['easy', 'medium', 'hard']),
  topic_tag: z.string().optional(),
  partial_scoring: z.boolean(),
  negative_marking: z.coerce.number().min(0),
  options: z.array(optionSchema).optional(),
});

type QuestionForm = z.infer<typeof questionSchema>;

/* ── Component ── */
export default function TeacherQuestionsPage() {
  'use no memo'; // react-hook-form watch() is incompatible with React Compiler
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const bulkFileRef = useRef<HTMLInputElement>(null);

  /* ── Fetch assessment (includes questions) ── */
  const { data: assessment, isLoading } = useQuery({
    queryKey: ['teacher', 'assessment', id],
    queryFn: async () => {
      const res = await api.get(`/teacher/assessments/${id}`);
      return (res.data.data ?? res.data) as Assessment;
    },
    enabled: !!id,
  });

  const questions = assessment?.questions ?? [];

  /* ── Form ── */
  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    formState: { errors },
  } = useForm<QuestionForm>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(questionSchema) as any,
    defaultValues: {
      question_type: 'mcq_single',
      content: '',
      points: 1,
      difficulty: 'medium',
      topic_tag: '',
      partial_scoring: false,
      negative_marking: 0,
      options: [
        { content: '', is_correct: false },
        { content: '', is_correct: false },
      ],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'options',
  });

  // eslint-disable-next-line react-hooks/incompatible-library
  const watchType = watch('question_type') as QuestionType;
  const showOptions = MCQ_TYPES.includes(watchType);

  /* ── Create mutation ── */
  const createMutation = useMutation({
    mutationFn: async (data: QuestionCreate) => {
      const res = await api.post(`/teacher/assessments/${id}/questions`, data);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Question added');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      closeModal();
    },
    onError: () => toast.error('Failed to add question'),
  });

  /* ── Update mutation ── */
  const updateMutation = useMutation({
    mutationFn: async ({
      qid,
      data,
    }: {
      qid: string;
      data: Partial<QuestionCreate>;
    }) => {
      const res = await api.patch(`/teacher/questions/${qid}`, data);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Question updated');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      closeModal();
    },
    onError: () => toast.error('Failed to update question'),
  });

  /* ── Delete mutation ── */
  const deleteMutation = useMutation({
    mutationFn: async (qid: string) => {
      await api.delete(`/teacher/questions/${qid}`);
    },
    onSuccess: () => {
      toast.success('Question deleted');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
    },
    onError: () => toast.error('Failed to delete question'),
  });

  /* ── Bulk import mutation ── */
  const bulkMutation = useMutation({
    mutationFn: async (file: File) => {
      const text = await file.text();
      const json = JSON.parse(text);
      const res = await api.post('/teacher/questions/bulk-import', json);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Questions imported successfully');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      setBulkOpen(false);
    },
    onError: () => toast.error('Bulk import failed'),
  });

  /* ── Helpers ── */
  const openCreate = () => {
    setEditingQuestion(null);
    reset({
      question_type: 'mcq_single',
      content: '',
      points: 1,
      difficulty: 'medium',
      topic_tag: '',
      partial_scoring: false,
      negative_marking: 0,
      options: [
        { content: '', is_correct: false },
        { content: '', is_correct: false },
      ],
    });
    setModalOpen(true);
  };

  const openEdit = (q: Question) => {
    setEditingQuestion(q);
    reset({
      question_type: q.question_type,
      content: q.content,
      points: q.points,
      difficulty: q.difficulty ?? 'medium',
      topic_tag: q.topic_tag ?? '',
      partial_scoring: q.partial_scoring,
      negative_marking: q.negative_marking,
      options:
        q.options?.map((o) => ({ content: o.content, is_correct: o.is_correct })) ??
        [],
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingQuestion(null);
  };

  const handleDelete = (qid: string) => {
    setDeleteConfirmId(qid);
  };

  const onSubmit = (data: QuestionForm) => {
    const payload: QuestionCreate = {
      question_type: data.question_type as QuestionType,
      content: data.content,
      points: data.points,
      difficulty: data.difficulty as Difficulty,
      topic_tag: data.topic_tag || undefined,
      partial_scoring: data.partial_scoring,
      negative_marking: data.negative_marking,
      options: showOptions ? data.options : undefined,
    };

    if (editingQuestion) {
      updateMutation.mutate({ qid: editingQuestion.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleBulkImport = () => {
    const file = bulkFileRef.current?.files?.[0];
    if (!file) {
      toast.error('Please select a JSON file');
      return;
    }
    bulkMutation.mutate(file);
  };

  const truncate = (text: string, max = 120) =>
    text.length > max ? `${text.slice(0, max)}…` : text;

  /* ── Render ── */
  if (isLoading) {
    return (
      <div className={styles.centered}>
        <Spinner />
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className={styles.centered}>
        <p>Assessment not found.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* ── Header ── */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Link to={`/teacher/assessments/${id}`} className={styles.backLink}>
            <FiArrowLeft /> Back to assessment
          </Link>
          <h1 className={styles.title}>{assessment.title} — Questions</h1>
        </div>
        <div className={styles.headerActions}>
          <Button variant="secondary" icon={<FiUpload />} onClick={() => setBulkOpen(true)}>
            Bulk Import
          </Button>
          <Button icon={<FiPlus />} onClick={openCreate}>
            Add Question
          </Button>
        </div>
      </div>

      {/* ── Question list ── */}
      {questions.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No questions yet. Add your first question to get started.</p>
          <Button icon={<FiPlus />} onClick={openCreate}>
            Add Question
          </Button>
        </div>
      ) : (
        <div className={styles.questionList}>
          {questions.map((q) => (
            <div key={q.id} className={styles.questionCard}>
              <div className={styles.questionInfo}>
                <div className={styles.questionTop}>
                  <span className={styles.orderIndex}>
                    #{q.order_index ?? '—'}
                  </span>
                  <Badge variant="info">{q.question_type.replace(/_/g, ' ')}</Badge>
                  <span className={styles.questionContent}>
                    {truncate(q.content)}
                  </span>
                </div>
                <div className={styles.questionMeta}>
                  <span className={styles.points}>{q.points} pts</span>
                  {q.difficulty && (
                    <Badge variant={difficultyVariant[q.difficulty]}>
                      {q.difficulty}
                    </Badge>
                  )}
                  {q.topic_tag && <Badge variant="neutral">{q.topic_tag}</Badge>}
                </div>
              </div>
              <div className={styles.questionActions}>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<FiEdit2 />}
                  onClick={() => openEdit(q)}
                >
                  Edit
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  icon={<FiTrash2 />}
                  loading={deleteMutation.isPending}
                  onClick={() => handleDelete(q.id)}
                >
                  Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Add / Edit Modal ── */}
      <Modal
        isOpen={modalOpen}
        onClose={closeModal}
        title={editingQuestion ? 'Edit Question' : 'Add Question'}
        size="lg"
      >
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)}>
          <div className={styles.formRow}>
            <Select
              label="Question Type"
              options={QUESTION_TYPE_OPTIONS}
              error={errors.question_type?.message}
              {...register('question_type')}
            />
            <Select
              label="Difficulty"
              options={DIFFICULTY_OPTIONS}
              error={errors.difficulty?.message}
              {...register('difficulty')}
            />
          </div>

          <Textarea
            label="Content"
            placeholder="Enter question content…"
            error={errors.content?.message}
            rows={4}
            {...register('content')}
          />

          <div className={styles.formRowThree}>
            <Input
              label="Points"
              type="number"
              min={0}
              error={errors.points?.message}
              {...register('points')}
            />
            <Input
              label="Negative Marking"
              type="number"
              min={0}
              step={0.1}
              error={errors.negative_marking?.message}
              {...register('negative_marking')}
            />
            <Input
              label="Topic Tag"
              placeholder="e.g. algebra"
              error={errors.topic_tag?.message}
              {...register('topic_tag')}
            />
          </div>

          <div className={styles.checkboxRow}>
            <label className={styles.checkboxLabel}>
              <input type="checkbox" {...register('partial_scoring')} />
              Partial Scoring
            </label>
          </div>

          {/* ── Options (MCQ types) ── */}
          {showOptions && (
            <div className={styles.optionsSection}>
              <h4 className={styles.optionsSectionTitle}>Answer Options</h4>

              {fields.map((field, index) => (
                <div key={field.id} className={styles.optionRow}>
                  <div className={styles.optionInput}>
                    <Input
                      placeholder={`Option ${index + 1}`}
                      error={errors.options?.[index]?.content?.message}
                      {...register(`options.${index}.content`)}
                    />
                  </div>
                  <label className={styles.optionCorrect}>
                    <input
                      type="checkbox"
                      {...register(`options.${index}.is_correct`)}
                    />
                    Correct
                  </label>
                  {fields.length > 2 && (
                    <button
                      type="button"
                      className={styles.removeOption}
                      onClick={() => remove(index)}
                    >
                      <FiX size={14} />
                    </button>
                  )}
                </div>
              ))}

              <button
                type="button"
                className={styles.addOption}
                onClick={() => append({ content: '', is_correct: false })}
              >
                <FiPlus size={14} /> Add Option
              </button>
            </div>
          )}

          <div className={styles.formActions}>
            <Button variant="secondary" type="button" onClick={closeModal}>
              Cancel
            </Button>
            <Button
              type="submit"
              loading={createMutation.isPending || updateMutation.isPending}
            >
              {editingQuestion ? 'Save Changes' : 'Add Question'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ── Bulk Import Modal ── */}
      <Modal
        isOpen={bulkOpen}
        onClose={() => setBulkOpen(false)}
        title="Bulk Import Questions"
        size="md"
      >
        <div className={styles.bulkSection}>
          <p className={styles.bulkHint}>
            Upload a JSON file containing an array of question objects. Each
            object should follow the standard question format with{' '}
            <code>question_type</code>, <code>content</code>,{' '}
            <code>points</code>, and optional <code>options</code>.
          </p>
          <input
            ref={bulkFileRef}
            type="file"
            accept=".json"
            className={styles.fileInput}
          />
          <div className={styles.formActions}>
            <Button variant="secondary" onClick={() => setBulkOpen(false)}>
              Cancel
            </Button>
            <Button
              icon={<FiUpload />}
              loading={bulkMutation.isPending}
              onClick={handleBulkImport}
            >
              Import
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmModal
        isOpen={!!deleteConfirmId}
        onClose={() => setDeleteConfirmId(null)}
        onConfirm={() => { deleteMutation.mutate(deleteConfirmId!); setDeleteConfirmId(null); }}
        title="Delete Question"
        message="Are you sure you want to delete this question?"
        confirmLabel="Delete"
        variant="danger"
      />
    </div>
  );
}
