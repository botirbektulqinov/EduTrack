/* ─── AssessmentTakePage — Student assessment-taking UI ─── */
import { useState, useCallback, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api from '@/lib/api';
import { useProctoring } from '@/hooks/useProctoring';
import { useTimer } from '@/hooks/useTimer';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAutoSave } from '@/hooks/useAutoSave';
import { formatTime } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import ConfirmModal from '@/components/ui/ConfirmModal';
import { QuestionRenderer } from '@/components/question-types/QuestionRenderer';
import type {
  Assessment,
  Question,
  AssessmentAttempt,
  ViolationEvent,
  WSServerMessage,
  ProctoringConfig,
} from '@/types';
import styles from './AssessmentTakePage.module.scss';

type Phase = 'loading' | 'preview' | 'active' | 'submitted' | 'terminated' | 'error';
type SubmitConfirm = { open: boolean; message: string };

export default function AssessmentTakePage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();

  const [phase, setPhase] = useState<Phase>('loading');
  const [attempt, setAttempt] = useState<AssessmentAttempt | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  const [violationCount, setViolationCount] = useState(0);

  const answersRef = useRef(answers);
  answersRef.current = answers;

  /* ── Validate token ── */
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { isLoading } = useQuery({
    queryKey: ['take', token],
    queryFn: async () => {
      try {
        const res = await api.get(`/student/take/${token}`);
        const data = res.data.data ?? res.data;
        setAssessment(data.assessment ?? data);
        setPhase('preview');
        return data;
      } catch (err: unknown) {
        const axiosErr = err as { response?: { status?: number; data?: { detail?: { message?: string }; message?: string } } };
        const status = axiosErr?.response?.status;
        const msg =
          axiosErr?.response?.data?.detail?.message ??
          axiosErr?.response?.data?.message ??
          'Unable to load assessment.';
        if (status === 403) {
          setErrorMessage(msg);
        } else {
          setErrorMessage('This link may be invalid, expired, or you are not authorized.');
        }
        setPhase('error');
        throw err;
      }
    },
    enabled: !!token,
    retry: false,
  });

  /* ── Start attempt ── */
  const startMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/student/take/${token}/start`);
      return res.data.data ?? res.data;
    },
    onSuccess: (data) => {
      // Backend returns AttemptStartResponse { attempt_id, server_token, time_limit_seconds, questions }
      // Map to AssessmentAttempt shape
      setAttempt({
        id: data.attempt_id,
        server_token: data.server_token,
        time_limit_seconds: data.time_limit_seconds,
        time_remaining_seconds: data.time_limit_seconds,
      } as AssessmentAttempt);
      setQuestions(data.questions ?? []);
      setPhase('active');
    },
    onError: () => {
      toast.error('Failed to start assessment');
      setPhase('error');
    },
  });

  /* ── Submit attempt ── */
  const submitMutation = useMutation({
    mutationFn: async () => {
      if (!attempt) return;
      await api.post(`/student/attempts/${attempt.id}/submit`);
    },
    onSuccess: () => {
      setPhase('submitted');
      toast.success('Assessment submitted!');
    },
    onError: () => {
      toast.error('Submission failed');
    },
  });

  /* ── Save answers ── */
  const saveAnswers = useCallback(async () => {
    if (!attempt) return;
    // Transform Record<questionId, value> → AnswerSaveRequest[]
    const formatted = Object.entries(answersRef.current).map(([questionId, value]) => {
      const q = questions.find((qq) => qq.id === questionId);
      const entry: Record<string, unknown> = { question_id: questionId };
      if (!q) { entry.answer_text = String(value ?? ''); return entry; }
      switch (q.question_type) {
        case 'mcq_single':
        case 'image_mcq':
          entry.selected_option_ids = [value];
          break;
        case 'mcq_multi':
          entry.selected_option_ids = Array.isArray(value) ? value : [value];
          break;
        case 'true_false':
        case 'yes_no':
        case 'short_answer':
        case 'essay':
        case 'fill_blank':
          entry.answer_text = String(value ?? '');
          break;
        case 'code':
          entry.code_submission = String(value ?? '');
          break;
        case 'numeric':
          entry.numeric_answer = Number(value);
          break;
        case 'matching':
          entry.matched_pairs = value;
          break;
        case 'ordering':
          entry.ordered_ids = value;
          break;
        case 'categorization':
          entry.categorized = value;
          break;
        case 'hotspot':
          entry.hotspot_coords = value;
          break;
        case 'likert':
          entry.likert_value = Number(value);
          break;
        default:
          entry.answer_text = String(value ?? '');
      }
      return entry;
    });
    await api.post(`/student/attempts/${attempt.id}/save`, { answers: formatted });
  }, [attempt, questions]);

  /* ── Auto-save ── */
  useAutoSave({
    saveFn: saveAnswers,
    interval: 30_000,
    enabled: phase === 'active',
  });

  /* ── Timer ── */
  const initialSeconds = attempt?.time_remaining_seconds ?? attempt?.time_limit_seconds ?? 0;

  const { remaining, deductTime, syncTime } = useTimer({
    initialSeconds,
    onExpire: () => {
      submitMutation.mutate();
    },
    onWarning: (sec) => {
      const min = Math.floor(sec / 60);
      toast(`${min} minute${min !== 1 ? 's' : ''} remaining!`, { icon: '⏰' });
    },
    enabled: phase === 'active' && initialSeconds > 0,
  });

  /* ── Proctoring ── */
  const proctoringConfig: ProctoringConfig = assessment
    ? {
        maxViolations: assessment.max_violations,
        timePenaltyMinutes: assessment.time_penalty_minutes,
        enforceFullscreen: assessment.enforce_fullscreen,
        blockKeyboardShortcuts: true,
        tabSwitchDetection: true,
        devToolsDetection: true,
        rightClickBlock: true,
        copyPasteBlock: true,
      }
    : {
        maxViolations: 3,
        timePenaltyMinutes: 2,
        enforceFullscreen: true,
        blockKeyboardShortcuts: true,
        tabSwitchDetection: true,
        devToolsDetection: true,
        rightClickBlock: true,
        copyPasteBlock: true,
      };

  const handleViolation = useCallback(
    (event: ViolationEvent) => {
      setViolationCount(event.count);
      deductTime((assessment?.time_penalty_minutes ?? 2) * 60);
      toast.error(`Violation ${event.count}/${proctoringConfig.maxViolations}: ${event.type.replace(/_/g, ' ')}`);

      // Report to server via WebSocket
      wsSend({
        type: 'VIOLATION',
        violation_type: event.type,
        time_remaining: remaining,
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [assessment, remaining],
  );

  const handleTerminate = useCallback(() => {
    setPhase('terminated');
    toast.error('Assessment terminated due to violations');
  }, []);

  const { enterFullscreen } = useProctoring({
    config: proctoringConfig,
    onViolation: handleViolation,
    onTerminate: handleTerminate,
    enabled: phase === 'active' && (assessment?.enforce_fullscreen ?? true),
  });

  /* ── WebSocket ── */
  const handleWSMessage = useCallback(
    (msg: WSServerMessage) => {
      switch (msg.type) {
        case 'TIME_UPDATE':
          syncTime(msg.time_remaining);
          break;
        case 'TIME_PENALTY':
          deductTime(msg.deducted);
          toast.error(`Time penalty: -${Math.floor(msg.deducted / 60)} min`);
          break;
        case 'WARNING':
          toast.error(msg.message);
          setViolationCount(msg.count);
          break;
        case 'TERMINATE':
          setPhase('terminated');
          toast.error(msg.reason);
          break;
        case 'FORCE_SUBMIT':
          submitMutation.mutate();
          break;
        case 'ASSESSMENT_DEACTIVATED':
          setPhase('terminated');
          toast.error(msg.message);
          break;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [syncTime, deductTime],
  );

  const { send: wsSend, connected: wsConnected } = useWebSocket({
    attemptId: attempt?.id ?? '',
    serverToken: attempt?.server_token ?? '',
    onMessage: handleWSMessage,
    enabled: phase === 'active' && !!attempt,
  });

  /* ── Heartbeat ── */
  useEffect(() => {
    if (phase !== 'active') return;
    const interval = setInterval(() => {
      wsSend({ type: 'HEARTBEAT', time_remaining: remaining });
    }, 60_000);
    return () => clearInterval(interval);
  }, [phase, wsSend, remaining]);

  /* ── Answer change handler ── */
  const handleAnswerChange = useCallback((questionId: string, data: unknown) => {
    setAnswers((prev) => ({ ...prev, [questionId]: data }));
  }, []);

  /* ── Flag toggle ── */
  const toggleFlag = useCallback((questionId: string) => {
    setFlagged((prev) => {
      const next = new Set(prev);
      if (next.has(questionId)) next.delete(questionId);
      else next.add(questionId);
      return next;
    });
  }, []);

  /* ── Handle start ── */
  const handleStart = async () => {
    await enterFullscreen();
    startMutation.mutate();
  };

  /* ── Handle submit ── */
  const [submitConfirm, setSubmitConfirm] = useState<SubmitConfirm>({ open: false, message: '' });

  const handleSubmit = () => {
    const unanswered = questions.filter((q) => !answers[q.id]);
    const msg =
      unanswered.length > 0
        ? `You have ${unanswered.length} unanswered question(s). Submit anyway?`
        : 'Are you sure you want to submit?';
    setSubmitConfirm({ open: true, message: msg });
  };

  const confirmSubmit = () => {
    setSubmitConfirm({ open: false, message: '' });
    saveAnswers().then(() => submitMutation.mutate());
  };

  /* ── Current question ── */
  const currentQuestion = questions[currentIndex];

  /* ── RENDER ── */

  if (isLoading && phase === 'loading') {
    return (
      <div className={styles.center}>
        <Spinner size="lg" />
        <p>Loading assessment...</p>
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div className={styles.center}>
        <h2>Unable to Load Assessment</h2>
        <p>{errorMessage ?? 'This link may be invalid, expired, or you are not authorized.'}</p>
        <Button variant="primary" onClick={() => navigate('/student/dashboard')}>
          Go to Dashboard
        </Button>
      </div>
    );
  }

  if (phase === 'preview' && assessment) {
    return (
      <div className={styles.previewPage}>
        <div className={styles.previewCard}>
          <h1>{assessment.title}</h1>
          {assessment.description && <p className={styles.desc}>{assessment.description}</p>}
          <div className={styles.meta}>
            <div><strong>Type:</strong> {assessment.assessment_type}</div>
            <div><strong>Duration:</strong> {assessment.time_limit_minutes} minutes</div>
            <div><strong>Max Attempts:</strong> {assessment.max_attempts}</div>
            <div><strong>Passing Score:</strong> {assessment.passing_score}%</div>
          </div>
          <div className={styles.rules}>
            <h3>Proctoring Rules</h3>
            <ul>
              {assessment.enforce_fullscreen && <li>Fullscreen mode is required</li>}
              <li>Tab switching and window focus loss are monitored</li>
              <li>Developer tools are blocked</li>
              <li>Maximum {assessment.max_violations} violations before termination</li>
              <li>Each violation deducts {assessment.time_penalty_minutes} minutes</li>
            </ul>
          </div>
          <Button
            variant="primary"
            onClick={handleStart}
            loading={startMutation.isPending}
            style={{ width: '100%', marginTop: '1.5rem' }}
          >
            Begin Assessment
          </Button>
        </div>
      </div>
    );
  }

  if (phase === 'submitted') {
    return (
      <div className={styles.center}>
        <h2>Assessment Submitted</h2>
        <p>Your answers have been recorded. Results will be available based on the release policy.</p>
        <Button variant="primary" onClick={() => navigate('/student/results')}>
          View Results
        </Button>
      </div>
    );
  }

  if (phase === 'terminated') {
    return (
      <div className={styles.center}>
        <h2>Assessment Terminated</h2>
        <p>Your assessment has been terminated due to proctoring violations.</p>
        <Button variant="secondary" onClick={() => navigate('/student/dashboard')}>
          Go to Dashboard
        </Button>
      </div>
    );
  }

  /* ── Active assessment ── */
  return (
    <div className={styles.assessmentShell}>
      {/* Top bar */}
      <header className={styles.topBar}>
        <div className={styles.topLeft}>
          <h3>{assessment?.title}</h3>
          <Badge variant={wsConnected ? 'success' : 'danger'}>
            {wsConnected ? 'Connected' : 'Disconnected'}
          </Badge>
        </div>
        <div className={styles.topCenter}>
          <span className={styles.timer} data-warning={remaining <= 300}>
            {formatTime(remaining)}
          </span>
        </div>
        <div className={styles.topRight}>
          <Badge variant={violationCount > 0 ? 'danger' : 'neutral'}>
            Violations: {violationCount}/{proctoringConfig.maxViolations}
          </Badge>
          <Button variant="danger" size="sm" onClick={handleSubmit} loading={submitMutation.isPending}>
            Submit
          </Button>
        </div>
      </header>

      {/* Main content */}
      <div className={styles.mainArea}>
        {/* Question panel */}
        <div className={styles.questionPanel}>
          {currentQuestion && (
            <>
              <div className={styles.questionHeader}>
                <span>Question {currentIndex + 1} of {questions.length}</span>
                <span>{currentQuestion.points} pt{currentQuestion.points !== 1 ? 's' : ''}</span>
              </div>
              <QuestionRenderer
                question={currentQuestion}
                value={answers[currentQuestion.id]}
                onChange={(val) => handleAnswerChange(currentQuestion.id, val)}
              />
              <div className={styles.questionActions}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toggleFlag(currentQuestion.id)}
                >
                  {flagged.has(currentQuestion.id) ? 'Unflag' : 'Flag for Review'}
                </Button>
              </div>
            </>
          )}

          {/* Navigation */}
          <div className={styles.navButtons}>
            <Button
              variant="secondary"
              size="sm"
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex((i) => i - 1)}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={currentIndex === questions.length - 1}
              onClick={() => setCurrentIndex((i) => i + 1)}
            >
              Next
            </Button>
          </div>
        </div>

        {/* Question palette */}
        <aside className={styles.palette}>
          <h4>Questions</h4>
          <div className={styles.paletteGrid}>
            {questions.map((q, i) => {
              let status = 'unanswered';
              if (answers[q.id]) status = 'answered';
              if (flagged.has(q.id)) status = 'flagged';
              return (
                <button
                  key={q.id}
                  className={styles.paletteBtn}
                  data-status={status}
                  data-active={i === currentIndex}
                  onClick={() => setCurrentIndex(i)}
                >
                  {i + 1}
                </button>
              );
            })}
          </div>
          <div className={styles.paletteLegend}>
            <span><span className={styles.dot} data-color="answered" /> Answered</span>
            <span><span className={styles.dot} data-color="flagged" /> Flagged</span>
            <span><span className={styles.dot} data-color="unanswered" /> Unanswered</span>
          </div>
        </aside>
      </div>

      <ConfirmModal
        isOpen={submitConfirm.open}
        onClose={() => setSubmitConfirm({ open: false, message: '' })}
        onConfirm={confirmSubmit}
        title="Submit Assessment"
        message={submitConfirm.message}
        confirmLabel="Submit"
        variant="primary"
      />
    </div>
  );
}
