import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useFieldArray, useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import {
  FiArrowLeft,
  FiClock,
  FiCode,
  FiCopy,
  FiEdit2,
  FiPlus,
  FiTrash2,
  FiUpload,
  FiX,
} from 'react-icons/fi';
import api from '@/lib/api';
import type {
  Assessment,
  CodeExecutionMode,
  CodeQuestionConfig,
  CodeQuestionTestCase,
  CurriculumTree,
  BulkQuestionPreviewResponse,
  Difficulty,
  Question,
  QuestionCreate,
  QuestionRevision,
  QuestionType,
} from '@/types';
import { formatDateTime } from '@/lib/utils';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import ConfirmModal from '@/components/ui/ConfirmModal';
import Input from '@/components/ui/Input';
import Modal from '@/components/ui/Modal';
import Select from '@/components/ui/Select';
import Spinner from '@/components/ui/Spinner';
import Textarea from '@/components/ui/Textarea';
import styles from './TeacherQuestionsPage.module.scss';

const QUESTION_TYPE_OPTIONS: { value: QuestionType; label: string }[] = [
  { value: 'true_false', label: 'True / False' },
  { value: 'yes_no', label: 'Yes / No' },
  { value: 'mcq_single', label: 'MCQ - Single' },
  { value: 'mcq_multi', label: 'MCQ - Multiple' },
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

const CODE_LANGUAGE_OPTIONS = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'java', label: 'Java' },
  { value: 'cpp', label: 'C++' },
];

const EXECUTION_MODE_OPTIONS: { value: CodeExecutionMode; label: string }[] = [
  { value: 'stdin_stdout', label: 'Standard IO' },
  { value: 'function', label: 'Function' },
];

const MCQ_TYPES: QuestionType[] = ['mcq_single', 'mcq_multi', 'image_mcq', 'true_false', 'yes_no'];

const difficultyVariant: Record<Difficulty, 'success' | 'warning' | 'danger'> = {
  easy: 'success',
  medium: 'warning',
  hard: 'danger',
};

const optionSchema = z.object({
  content: z.string().min(1, 'Option text is required'),
  is_correct: z.boolean(),
});

const codeCaseSchema = z.object({
  input: z.string(),
  output: z.string(),
  is_hidden: z.boolean(),
});

const questionSchema = z.object({
  question_type: z.string().min(1, 'Type is required'),
  content: z.string().min(1, 'Question content is required'),
  points: z.coerce.number().positive('Points must be greater than 0'),
  difficulty: z.enum(['easy', 'medium', 'hard']),
  subject_id: z.string().optional(),
  module_id: z.string().optional(),
  topic_id: z.string().optional(),
  topic_tag: z.string().optional(),
  partial_scoring: z.boolean(),
  negative_marking: z.coerce.number().min(0),
  options: z.array(optionSchema).optional(),
  code_language: z.string().default('python'),
  code_execution_mode: z.enum(['stdin_stdout', 'function']).default('stdin_stdout'),
  code_function_name: z.string().optional(),
  code_starter_code: z.string().optional(),
  code_test_cases: z.array(codeCaseSchema).default([]),
});

type QuestionForm = z.infer<typeof questionSchema>;
type CodeTestCaseForm = QuestionForm['code_test_cases'][number];

const DEFAULT_CODE_CASES: CodeTestCaseForm[] = [
  { input: '', output: '', is_hidden: false },
  { input: '', output: '', is_hidden: true },
];

function getCodeConfig(question?: Question | null): CodeQuestionConfig {
  return (question?.config ?? {}) as CodeQuestionConfig;
}

function getCodeTestCases(question?: Question | null): CodeQuestionTestCase[] {
  const config = getCodeConfig(question);
  if (config.test_cases && config.test_cases.length > 0) {
    return config.test_cases.map((testCase) => ({
      input: testCase.input ?? '',
      output: testCase.output ?? '',
      is_hidden: !!testCase.is_hidden,
    }));
  }

  const visibleCases = (config.visible_test_cases ?? []).map((testCase) => ({
    input: testCase.input ?? '',
    output: testCase.output ?? '',
    is_hidden: false,
  }));
  const hiddenCases = (config.hidden_test_cases ?? []).map((testCase) => ({
    input: testCase.input ?? '',
    output: testCase.output ?? '',
    is_hidden: true,
  }));

  return [...visibleCases, ...hiddenCases];
}

function createDefaultFormValues(): QuestionForm {
  return {
    question_type: 'mcq_single',
    content: '',
    points: 1,
    difficulty: 'medium',
    subject_id: '',
    module_id: '',
    topic_id: '',
    topic_tag: '',
    partial_scoring: false,
    negative_marking: 0,
    options: [
      { content: '', is_correct: false },
      { content: '', is_correct: false },
    ],
    code_language: 'python',
    code_execution_mode: 'stdin_stdout',
    code_function_name: 'solve',
    code_starter_code: '',
    code_test_cases: DEFAULT_CODE_CASES,
  };
}

function buildBulkTemplate(assessmentId?: string) {
  return JSON.stringify(
    {
      questions: [
        {
          assessment_id: assessmentId,
          question_type: 'mcq_single',
          content: 'Which data structure uses FIFO ordering?',
          points: 2,
          difficulty: 'easy',
          topic_tag: 'data structures',
          partial_scoring: false,
          negative_marking: 0,
          options: [
            { content: 'Stack', is_correct: false },
            { content: 'Queue', is_correct: true },
            { content: 'Tree', is_correct: false },
            { content: 'Graph', is_correct: false },
          ],
        },
        {
          assessment_id: assessmentId,
          question_type: 'short_answer',
          content: 'Define time complexity in one or two sentences.',
          points: 3,
          difficulty: 'easy',
          topic_tag: 'algorithms',
          partial_scoring: false,
          negative_marking: 0,
          config: {
            accepted_answers: [],
          },
        },
        {
          assessment_id: assessmentId,
          question_type: 'code',
          content: 'Write a program that sums two integers read from input.',
          points: 10,
          difficulty: 'easy',
          topic_tag: 'basics',
          partial_scoring: true,
          negative_marking: 0,
          config: {
            language: 'python',
            execution_mode: 'stdin_stdout',
            starter_code: '# Read from stdin and print the sum',
            test_cases: [
              { input: '2 3', output: '5', is_hidden: false },
              { input: '100 250', output: '350', is_hidden: true },
            ],
          },
        },
        {
          assessment_id: assessmentId,
          question_type: 'matching',
          content: 'Match each SQL clause to its purpose.',
          points: 4,
          difficulty: 'medium',
          topic_tag: 'databases',
          partial_scoring: true,
          negative_marking: 0,
          options: [
            { content: 'SELECT', is_correct: true, match_key: 'Choose columns' },
            { content: 'WHERE', is_correct: true, match_key: 'Filter rows' },
            { content: 'ORDER BY', is_correct: true, match_key: 'Sort results' },
          ],
        },
        {
          assessment_id: assessmentId,
          question_type: 'ordering',
          content: 'Put the software development lifecycle phases in a reasonable order.',
          points: 4,
          difficulty: 'easy',
          topic_tag: 'software engineering',
          partial_scoring: true,
          negative_marking: 0,
          options: [
            { content: 'Requirements', is_correct: true, order_position: 1 },
            { content: 'Design', is_correct: true, order_position: 2 },
            { content: 'Implementation', is_correct: true, order_position: 3 },
            { content: 'Testing', is_correct: true, order_position: 4 },
          ],
        },
      ],
    },
    null,
    2,
  );
}

function buildBulkPrompt() {
  return [
    'Generate assessment questions in valid JSON for EduTrack.',
    'Return only JSON. No markdown fences. No explanation.',
    'Use this exact top-level shape:',
    '{"questions":[...]}',
    'Each item may use one of these question_type values:',
    '- true_false or yes_no: include options with exactly one correct answer.',
    '- mcq_single, mcq_multi, image_mcq: include options with content and is_correct.',
    '- short_answer or essay: include content and optional config.accepted_answers.',
    '- fill_blank: include config.blanks with accepted_answers per blank.',
    '- numeric: include config.correct_value and optional config.tolerance.',
    '- matching: include options with match_key.',
    '- ordering: include options with order_position.',
    '- categorization: include options with category_key.',
    '- hotspot: include config.zones.',
    '- likert: include config.scale and labels.',
    '- audio_video: include audio_url or video_url if needed.',
    '- code: include config.language, config.execution_mode, config.starter_code, and config.test_cases as {input, output, is_hidden}.',
    'Every question must include: question_type, content, points, difficulty, topic_tag, partial_scoring, negative_marking.',
    'For code questions, include at least one visible and one hidden test case.',
    'For choice questions, include at least two options and mark the correct ones.',
    'Keep HTML-safe question content and avoid duplicate questions.',
    'Use the provided JSON template as the contract to follow.',
  ].join('\n');
}

export default function TeacherQuestionsPage() {
  'use no memo';

  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const bulkFileRef = useRef<HTMLInputElement>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [bulkPreview, setBulkPreview] = useState<BulkQuestionPreviewResponse | null>(null);
  const [historyQuestion, setHistoryQuestion] = useState<Question | null>(null);

  const { data: assessment, isLoading } = useQuery({
    queryKey: ['teacher', 'assessment', id],
    queryFn: async () => {
      const response = await api.get(`/teacher/assessments/${id}`);
      return (response.data.data ?? response.data) as Assessment;
    },
    enabled: !!id,
  });

  const { data: curriculumData } = useQuery({
    queryKey: ['teacher-curriculum-tree'],
    queryFn: async () => {
      const response = await api.get('/teacher/curriculum/tree');
      return (response.data.data ?? response.data) as CurriculumTree;
    },
  });

  const { data: revisions = [], isLoading: revisionsLoading } = useQuery({
    queryKey: ['teacher-question-revisions', historyQuestion?.id],
    queryFn: async () => {
      const response = await api.get(`/teacher/questions/${historyQuestion?.id}/revisions`);
      return (response.data.data ?? response.data) as QuestionRevision[];
    },
    enabled: !!historyQuestion?.id,
  });

  const {
    register,
    handleSubmit,
    control,
    reset,
    setValue,
    formState: { errors },
  } = useForm<QuestionForm>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(questionSchema) as any,
    defaultValues: createDefaultFormValues(),
  });

  const {
    fields: optionFields,
    append: appendOption,
    remove: removeOption,
  } = useFieldArray({
    control,
    name: 'options',
  });

  const {
    fields: codeCaseFields,
    append: appendCodeCase,
    remove: removeCodeCase,
  } = useFieldArray({
    control,
    name: 'code_test_cases',
  });

  const questions = assessment?.questions ?? [];
  const subjects = curriculumData?.subjects ?? [];
  const watchType = useWatch({ control, name: 'question_type' }) as QuestionType;
  const showOptions = MCQ_TYPES.includes(watchType);
  const showCodeConfig = watchType === 'code';
  const watchExecutionMode = useWatch({ control, name: 'code_execution_mode' }) as CodeExecutionMode;
  const watchSubjectId = useWatch({ control, name: 'subject_id' }) ?? '';
  const watchModuleId = useWatch({ control, name: 'module_id' }) ?? '';
  const watchTopicId = useWatch({ control, name: 'topic_id' }) ?? '';
  const selectedSubject = subjects.find((subject) => subject.id === watchSubjectId) ?? null;
  const selectedModule = (selectedSubject?.modules ?? []).find((module) => module.id === watchModuleId) ?? null;
  const selectedTopic = (selectedModule?.topics ?? []).find((topic) => topic.id === watchTopicId) ?? null;
  const subjectOptions = [
    { value: '', label: 'No curriculum subject' },
    ...subjects.map((subject) => ({ value: subject.id, label: subject.name })),
  ];
  const moduleOptions = [
    { value: '', label: 'No module selected' },
    ...((selectedSubject?.modules ?? []).map((module) => ({ value: module.id, label: module.name }))),
  ];
  const topicOptions = [
    { value: '', label: 'No topic selected' },
    ...((selectedModule?.topics ?? []).map((topic) => ({ value: topic.id, label: topic.name }))),
  ];

  useEffect(() => {
    if (!watchSubjectId) {
      setValue('module_id', '');
      setValue('topic_id', '');
      return;
    }

    const moduleExists = (selectedSubject?.modules ?? []).some((module) => module.id === watchModuleId);
    if (!moduleExists) {
      setValue('module_id', '');
      setValue('topic_id', '');
    }
  }, [selectedSubject, setValue, watchModuleId, watchSubjectId]);

  useEffect(() => {
    if (!watchModuleId) {
      setValue('topic_id', '');
      return;
    }

    const topicExists = (selectedModule?.topics ?? []).some((topic) => topic.id === watchTopicId);
    if (!topicExists) {
      setValue('topic_id', '');
    }
  }, [selectedModule, setValue, watchModuleId, watchTopicId]);

  const createMutation = useMutation({
    mutationFn: async (payload: QuestionCreate) => {
      const response = await api.post(`/teacher/assessments/${id}/questions`, payload);
      return response.data;
    },
    onSuccess: (responseData) => {
      const created = (responseData.data ?? responseData) as Question | undefined;
      if (created) {
        queryClient.setQueryData(['teacher', 'assessment', id], (oldData: Assessment | undefined) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            questions: Array.isArray(oldData.questions) ? [...oldData.questions, created] : [created],
          };
        });
      }
      toast.success('Question added');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      closeModal();
    },
    onError: () => toast.error('Failed to add question'),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ questionId, payload }: { questionId: string; payload: Partial<QuestionCreate> }) => {
      const response = await api.patch(`/teacher/questions/${questionId}`, payload);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Question updated');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      closeModal();
    },
    onError: () => toast.error('Failed to update question'),
  });

  const deleteMutation = useMutation({
    mutationFn: async (questionId: string) => {
      await api.delete(`/teacher/questions/${questionId}`);
    },
    onSuccess: () => {
      toast.success('Question deleted');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
    },
    onError: () => toast.error('Failed to delete question'),
  });

  const bulkMutation = useMutation({
    mutationFn: async (file: File) => {
      const text = await file.text();
      const parsed = JSON.parse(text) as unknown;
      const payload = Array.isArray(parsed) ? { questions: parsed } : parsed;
      const response = await api.post('/teacher/questions/bulk-import', payload);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Questions imported successfully');
      queryClient.invalidateQueries({ queryKey: ['teacher', 'assessment', id] });
      setBulkOpen(false);
    },
    onError: () => toast.error('Bulk import failed'),
  });

  const previewMutation = useMutation({
    mutationFn: async (file: File) => {
      const text = await file.text();
      const parsed = JSON.parse(text) as unknown;
      const payload = Array.isArray(parsed) ? { questions: parsed } : parsed;
      const response = await api.post('/teacher/questions/bulk-import/preview', payload);
      return (response.data.data ?? response.data) as BulkQuestionPreviewResponse;
    },
    onSuccess: (result) => {
      setBulkPreview(result);
      if (result.invalid_items > 0) {
        toast.error(`Preview found ${result.invalid_items} invalid item(s).`);
      } else {
        toast.success('Preview generated');
      }
    },
    onError: () => toast.error('Preview failed'),
  });

  const closeModal = () => {
    setModalOpen(false);
    setEditingQuestion(null);
  };

  const openCreate = () => {
    setEditingQuestion(null);
    reset({
      ...createDefaultFormValues(),
      subject_id: assessment?.subject_id ?? assessment?.group_subject_id ?? '',
    });
    setModalOpen(true);
  };

  const openEdit = (question: Question) => {
    const codeConfig = getCodeConfig(question);
    const codeCases = getCodeTestCases(question);

    reset({
      question_type: question.question_type,
      content: question.content,
      points: question.points,
      difficulty: question.difficulty ?? 'medium',
      subject_id: question.subject_id ?? '',
      module_id: question.module_id ?? '',
      topic_id: question.topic_id ?? '',
      topic_tag: question.topic_tag ?? '',
      partial_scoring: question.partial_scoring,
      negative_marking: question.negative_marking,
      options: question.options?.map((option) => ({
        content: option.content,
        is_correct: option.is_correct,
      })) ?? [
        { content: '', is_correct: false },
        { content: '', is_correct: false },
      ],
      code_language: codeConfig.language ?? 'python',
      code_execution_mode: codeConfig.execution_mode ?? 'stdin_stdout',
      code_function_name: codeConfig.function_name ?? 'solve',
      code_starter_code: codeConfig.starter_code ?? '',
      code_test_cases: codeCases.length > 0 ? codeCases : DEFAULT_CODE_CASES,
    });

    setEditingQuestion(question);
    setModalOpen(true);
  };

  const handleDelete = (questionId: string) => {
    setDeleteConfirmId(questionId);
  };

  const onSubmit = (data: QuestionForm) => {
    let config: CodeQuestionConfig | undefined;

    if (data.question_type === 'code') {
      const testCases = (data.code_test_cases ?? [])
        .filter((testCase) => testCase.input.trim() || testCase.output.trim())
        .map((testCase) => ({
          input: testCase.input,
          output: testCase.output,
          is_hidden: testCase.is_hidden,
        }));

      if (testCases.length === 0) {
        toast.error('Add at least one test case for code questions.');
        return;
      }

      if (data.code_execution_mode === 'function' && !(data.code_function_name ?? '').trim()) {
        toast.error('Function mode requires a function name.');
        return;
      }

      config = {
        language: data.code_language,
        execution_mode: data.code_execution_mode,
        function_name:
          data.code_execution_mode === 'function'
            ? (data.code_function_name || 'solve').trim()
            : undefined,
        starter_code: data.code_starter_code?.trim() || undefined,
        test_cases: testCases,
        time_limit_seconds: 2,
      };
    }

    const payload: QuestionCreate = {
      question_type: data.question_type as QuestionType,
      content: data.content,
      points: data.points,
      difficulty: data.difficulty as Difficulty,
      topic_id: data.topic_id || undefined,
      topic_tag: (selectedTopic?.name ?? data.topic_tag) || undefined,
      partial_scoring: data.partial_scoring,
      negative_marking: data.negative_marking,
      config,
      options: showOptions ? data.options : undefined,
    };

    if (editingQuestion) {
      updateMutation.mutate({ questionId: editingQuestion.id, payload });
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

  const handleBulkPreview = () => {
    const file = bulkFileRef.current?.files?.[0];
    if (!file) {
      toast.error('Please select a JSON file');
      return;
    }
    previewMutation.mutate(file);
  };

  const copyText = async (text: string, successMessage: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(successMessage);
    } catch {
      toast.error('Clipboard access failed');
    }
  };

  const truncate = (text: string, max = 120) => (text.length > max ? `${text.slice(0, max)}...` : text);

  const bulkTemplate = buildBulkTemplate(id);
  const bulkPrompt = buildBulkPrompt();

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
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <Link to={`/teacher/assessments/${id}`} className={styles.backLink}>
            <FiArrowLeft /> Back to assessment
          </Link>
          <h1 className={styles.title}>{assessment.title} - Questions</h1>
        </div>
        <div className={styles.headerActions}>
          <Button
            variant="secondary"
            icon={<FiUpload />}
            onClick={() => {
              setBulkPreview(null);
              setBulkOpen(true);
            }}
          >
            Bulk Import
          </Button>
          <Button icon={<FiPlus />} onClick={openCreate}>
            Add Question
          </Button>
        </div>
      </div>

      {questions.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No questions yet. Add your first question to get started.</p>
          <Button icon={<FiPlus />} onClick={openCreate}>
            Add Question
          </Button>
        </div>
      ) : (
        <div className={styles.questionList}>
          {questions.map((question) => {
            const codeCases = question.question_type === 'code' ? getCodeTestCases(question).length : 0;

            return (
              <div key={question.id} className={styles.questionCard}>
                <div className={styles.questionInfo}>
                  <div className={styles.questionTop}>
                    <span className={styles.orderIndex}>#{question.order_index ?? '-'}</span>
                    <Badge variant="info">{question.question_type.replace(/_/g, ' ')}</Badge>
                    <span className={styles.questionContent}>{truncate(question.content)}</span>
                  </div>
                  <div className={styles.questionMeta}>
                    <span className={styles.points}>{question.points} pts</span>
                    {question.difficulty && (
                      <Badge variant={difficultyVariant[question.difficulty]}>{question.difficulty}</Badge>
                    )}
                    {(question.topic_name ?? question.topic_tag) && (
                      <Badge variant="neutral">{question.topic_name ?? question.topic_tag}</Badge>
                    )}
                    {question.module_name && <Badge variant="warning">{question.module_name}</Badge>}
                    {question.subject_name && <Badge variant="info">{question.subject_name}</Badge>}
                    {question.question_type === 'code' && (
                      <>
                        <Badge variant="warning">{codeCases} cases</Badge>
                        <Badge variant="neutral">
                          {((question.config ?? {}) as CodeQuestionConfig).language ?? 'python'}
                        </Badge>
                      </>
                    )}
                  </div>
                </div>
                <div className={styles.questionActions}>
                  <Button variant="ghost" size="sm" icon={<FiClock />} onClick={() => setHistoryQuestion(question)}>
                    History
                  </Button>
                  <Button variant="ghost" size="sm" icon={<FiEdit2 />} onClick={() => openEdit(question)}>
                    Edit
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    icon={<FiTrash2 />}
                    loading={deleteMutation.isPending}
                    onClick={() => handleDelete(question.id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

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
            placeholder="Enter question content..."
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
              label="Legacy Topic Tag"
              placeholder="e.g. recursion"
              helperText="Used as a fallback when no curriculum topic is selected."
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

          <div className={styles.optionsSection}>
            <div className={styles.sectionHeader}>
              <div>
                <h4 className={styles.optionsSectionTitle}>Curriculum Mapping</h4>
                <p className={styles.sectionHint}>
                  Link each question to a subject, module, and topic when possible.
                  If you skip the mapping, analytics falls back to the legacy topic tag.
                </p>
              </div>
            </div>

            <div className={styles.formRow}>
              <Select label="Subject" options={subjectOptions} {...register('subject_id')} />
              <Select label="Module" options={moduleOptions} {...register('module_id')} />
            </div>

            <div className={styles.formRow}>
              <Select label="Topic" options={topicOptions} {...register('topic_id')} />
              <Input
                label="Assessment Subject"
                value={assessment.subject_name ?? assessment.group_subject_name ?? 'No subject assigned to assessment'}
                disabled
              />
            </div>
          </div>

          {showOptions && (
            <div className={styles.optionsSection}>
              <div className={styles.sectionHeader}>
                <h4 className={styles.optionsSectionTitle}>Answer Options</h4>
              </div>

              {optionFields.map((field, index) => (
                <div key={field.id} className={styles.optionRow}>
                  <div className={styles.optionInput}>
                    <Input
                      placeholder={`Option ${index + 1}`}
                      error={errors.options?.[index]?.content?.message}
                      {...register(`options.${index}.content`)}
                    />
                  </div>
                  <label className={styles.optionCorrect}>
                    <input type="checkbox" {...register(`options.${index}.is_correct`)} />
                    Correct
                  </label>
                  {optionFields.length > 2 && (
                    <button type="button" className={styles.removeOption} onClick={() => removeOption(index)}>
                      <FiX size={14} />
                    </button>
                  )}
                </div>
              ))}

              <button
                type="button"
                className={styles.addOption}
                onClick={() => appendOption({ content: '', is_correct: false })}
              >
                <FiPlus size={14} /> Add Option
              </button>
            </div>
          )}

          {showCodeConfig && (
            <div className={styles.codeSection}>
              <div className={styles.sectionHeader}>
                <div>
                  <h4 className={styles.optionsSectionTitle}>Code Question Settings</h4>
                  <p className={styles.sectionHint}>
                    Python submissions can now be auto-graded against visible and hidden test cases.
                    Other languages stay available for authoring but fall back to manual review.
                  </p>
                </div>
                <Badge variant="warning">Auto-grade: Python</Badge>
              </div>

              <div className={styles.formRow}>
                <Select label="Language" options={CODE_LANGUAGE_OPTIONS} {...register('code_language')} />
                <Select
                  label="Execution Mode"
                  options={EXECUTION_MODE_OPTIONS}
                  {...register('code_execution_mode')}
                />
              </div>

              {watchExecutionMode === 'function' && (
                <Input
                  label="Function Name"
                  placeholder="solve"
                  error={errors.code_function_name?.message}
                  helperText="The student's code should define this callable."
                  {...register('code_function_name')}
                />
              )}

              <Textarea
                label="Starter Code"
                placeholder={watchExecutionMode === 'function' ? 'def solve(input_data: str):\n    pass' : '# Read from stdin and print the result'}
                rows={8}
                {...register('code_starter_code')}
              />

              <div className={styles.codeCases}>
                <div className={styles.sectionHeader}>
                  <div>
                    <h4 className={styles.optionsSectionTitle}>Test Cases</h4>
                    <p className={styles.sectionHint}>
                      Visible cases are shown to students before submission. Hidden cases are used only for grading.
                    </p>
                  </div>
                </div>

                {codeCaseFields.map((field, index) => (
                  <div key={field.id} className={styles.codeCaseCard}>
                    <div className={styles.codeCaseHeader}>
                      <strong>Case {index + 1}</strong>
                      <div className={styles.codeCaseActions}>
                        <label className={styles.optionCorrect}>
                          <input type="checkbox" {...register(`code_test_cases.${index}.is_hidden`)} />
                          Hidden
                        </label>
                        {codeCaseFields.length > 1 && (
                          <button type="button" className={styles.removeOption} onClick={() => removeCodeCase(index)}>
                            <FiX size={14} />
                          </button>
                        )}
                      </div>
                    </div>
                    <div className={styles.codeCaseGrid}>
                      <Textarea
                        label="Input"
                        rows={4}
                        error={errors.code_test_cases?.[index]?.input?.message}
                        {...register(`code_test_cases.${index}.input`)}
                      />
                      <Textarea
                        label="Expected Output"
                        rows={4}
                        error={errors.code_test_cases?.[index]?.output?.message}
                        {...register(`code_test_cases.${index}.output`)}
                      />
                    </div>
                  </div>
                ))}

                <button
                  type="button"
                  className={styles.addOption}
                  onClick={() => appendCodeCase({ input: '', output: '', is_hidden: false })}
                >
                  <FiPlus size={14} /> Add Test Case
                </button>
              </div>
            </div>
          )}

          <div className={styles.formActions}>
            <Button variant="secondary" type="button" onClick={closeModal}>
              Cancel
            </Button>
            <Button type="submit" loading={createMutation.isPending || updateMutation.isPending}>
              {editingQuestion ? 'Save Changes' : 'Add Question'}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={bulkOpen}
        onClose={() => {
          setBulkOpen(false);
          setBulkPreview(null);
        }}
        title="Bulk Import Questions"
        size="lg"
      >
        <div className={styles.bulkSection}>
          <p className={styles.bulkHint}>
            Upload a JSON file with a top-level <code>{'{"questions":[...]}'}</code> object. A raw array is also accepted
            and will be wrapped automatically before upload.
          </p>

          <div className={styles.bulkPanel}>
            <div className={styles.bulkPanelHeader}>
              <div className={styles.bulkPanelTitle}>
                <FiCode size={16} /> AI Prompt
              </div>
              <Button variant="ghost" size="sm" icon={<FiCopy />} onClick={() => copyText(bulkPrompt, 'Prompt copied')}>
                Copy
              </Button>
            </div>
            <pre className={styles.bulkCode}>{bulkPrompt}</pre>
          </div>

          <div className={styles.bulkPanel}>
            <div className={styles.bulkPanelHeader}>
              <div className={styles.bulkPanelTitle}>
                <FiCode size={16} /> JSON Template
              </div>
              <Button
                variant="ghost"
                size="sm"
                icon={<FiCopy />}
                onClick={() => copyText(bulkTemplate, 'Template copied')}
              >
                Copy
              </Button>
            </div>
            <pre className={styles.bulkCode}>{bulkTemplate}</pre>
          </div>

          <input ref={bulkFileRef} type="file" accept=".json" className={styles.fileInput} />

          {bulkPreview && (
            <div className={styles.previewSection}>
              <div className={styles.previewSummary}>
                <Badge variant={bulkPreview.invalid_items === 0 ? 'success' : 'danger'}>
                  {bulkPreview.valid_items}/{bulkPreview.total_items} valid
                </Badge>
                {bulkPreview.invalid_items > 0 && (
                  <Badge variant="danger">{bulkPreview.invalid_items} invalid</Badge>
                )}
              </div>

              <div className={styles.previewList}>
                {bulkPreview.questions.map((item) => (
                  <div key={`${item.index}-${item.content_preview}`} className={styles.previewItem}>
                    <div className={styles.previewHeader}>
                      <div>
                        <strong>#{item.index} {item.question_type ?? 'Unknown type'}</strong>
                        <p>{item.content_preview ?? 'Validation failed before content parsing.'}</p>
                      </div>
                      <Badge variant={item.is_valid ? 'success' : 'danger'}>
                        {item.is_valid ? 'Valid' : 'Invalid'}
                      </Badge>
                    </div>
                    <div className={styles.previewMeta}>
                      <span>{item.points ?? 0} pts</span>
                      {item.difficulty && <span>{item.difficulty}</span>}
                      {item.resolved_topic_name && <span>Topic: {item.resolved_topic_name}</span>}
                      {item.options_count > 0 && <span>{item.options_count} options</span>}
                      {(item.visible_test_cases + item.hidden_test_cases) > 0 && (
                        <span>
                          {item.visible_test_cases} visible / {item.hidden_test_cases} hidden cases
                        </span>
                      )}
                    </div>
                    {item.warnings.length > 0 && (
                      <div className={styles.previewWarnings}>
                        {item.warnings.map((warning) => (
                          <div key={warning}>{warning}</div>
                        ))}
                      </div>
                    )}
                    {item.errors.length > 0 && (
                      <div className={styles.previewErrors}>
                        {item.errors.map((error) => (
                          <div key={error}>{error}</div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className={styles.formActions}>
            <Button variant="secondary" onClick={() => setBulkOpen(false)}>
              Cancel
            </Button>
            <Button variant="secondary" loading={previewMutation.isPending} onClick={handleBulkPreview}>
              Preview Import
            </Button>
            <Button
              icon={<FiUpload />}
              loading={bulkMutation.isPending}
              onClick={handleBulkImport}
              disabled={!bulkPreview || bulkPreview.invalid_items > 0}
            >
              Import Validated Questions
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={!!historyQuestion}
        onClose={() => setHistoryQuestion(null)}
        title={historyQuestion ? `Revision History - ${historyQuestion.content.slice(0, 50)}` : 'Revision History'}
        size="lg"
      >
        {revisionsLoading ? (
          <div className={styles.centered}>
            <Spinner />
          </div>
        ) : revisions.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No revisions recorded for this question yet.</p>
          </div>
        ) : (
          <div className={styles.historyList}>
            {revisions.map((revision) => {
              const snapshot = revision.snapshot ?? {};
              const options = Array.isArray(snapshot.options) ? snapshot.options.length : 0;
              const difficulty =
                typeof snapshot.difficulty === 'string' && snapshot.difficulty.trim()
                  ? snapshot.difficulty
                  : null;
              const topicTag =
                typeof snapshot.topic_tag === 'string' && snapshot.topic_tag.trim()
                  ? snapshot.topic_tag
                  : null;
              const content =
                typeof snapshot.content === 'string' && snapshot.content.trim()
                  ? snapshot.content
                  : null;
              return (
                <div key={revision.id} className={styles.historyItem}>
                  <div className={styles.historyHeader}>
                    <div>
                      <strong>Version {revision.version_number}</strong>
                      <p>{revision.summary ?? revision.source}</p>
                    </div>
                    <Badge variant="info">{revision.source}</Badge>
                  </div>
                  <div className={styles.historyMeta}>
                    <span>{formatDateTime(revision.created_at)}</span>
                    {difficulty && <span>{difficulty}</span>}
                    {topicTag && <span>Topic: {topicTag}</span>}
                    {options > 0 && <span>{options} options</span>}
                  </div>
                  {content && (
                    <div className={styles.historyBody}>
                      {content}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Modal>

      <ConfirmModal
        isOpen={!!deleteConfirmId}
        onClose={() => setDeleteConfirmId(null)}
        onConfirm={() => {
          deleteMutation.mutate(deleteConfirmId!);
          setDeleteConfirmId(null);
        }}
        title="Delete Question"
        message="Are you sure you want to delete this question?"
        confirmLabel="Delete"
        variant="danger"
      />
    </div>
  );
}
