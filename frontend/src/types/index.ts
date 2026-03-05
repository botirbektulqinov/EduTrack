/* ─── EduTrack — Core Type Definitions ─── */

/* ── User ── */
export type UserRole = 'admin' | 'teacher' | 'student';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  student_id_number?: string;
  employee_id?: string;
  department_id?: string;
  is_active: boolean;
  extra_time_factor: number;
  avatar_url?: string;
  phone?: string;
  created_at: string;
  updated_at: string;
}

/* ── Auth ── */
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

/* ── Group ── */
export interface Group {
  id: string;
  name: string;
  subject?: string;
  academic_year?: string;
  semester?: string;
  teacher_id?: string;
  teacher_name?: string;
  student_count?: number;
  is_archived: boolean;
  created_at: string;
}

export interface GroupEnrollment {
  id: string;
  group_id: string;
  student_id: string;
  enrolled_at: string;
}

/* ── Assessment ── */
export type AssessmentType = 'test' | 'quiz' | 'survey' | 'practice';
export type ScoreReleasePolicy = 'immediate' | 'after_review' | 'after_window';

export interface Assessment {
  id: string;
  title: string;
  description?: string;
  assessment_type: AssessmentType;
  group_id?: string;
  group_name?: string;
  teacher_id?: string;
  time_limit_minutes?: number;
  available_from?: string;
  available_until?: string;
  max_attempts: number;
  passing_score: number;
  score_release_policy: ScoreReleasePolicy;
  shuffle_questions: boolean;
  shuffle_options: boolean;
  max_violations: number;
  time_penalty_minutes: number;
  enforce_fullscreen: boolean;
  access_token?: string;
  is_published: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  questions?: Question[];
}

export interface AssessmentCreate {
  title: string;
  description?: string;
  assessment_type: AssessmentType;
  group_id: string;
  time_limit_minutes?: number;
  available_from?: string;
  available_until?: string;
  max_attempts?: number;
  passing_score?: number;
  score_release_policy?: ScoreReleasePolicy;
  shuffle_questions?: boolean;
  shuffle_options?: boolean;
  max_violations?: number;
  time_penalty_minutes?: number;
  enforce_fullscreen?: boolean;
}

/* ── Question ── */
export type QuestionType =
  | 'true_false'
  | 'yes_no'
  | 'mcq_single'
  | 'mcq_multi'
  | 'image_mcq'
  | 'short_answer'
  | 'essay'
  | 'fill_blank'
  | 'numeric'
  | 'matching'
  | 'ordering'
  | 'categorization'
  | 'hotspot'
  | 'code'
  | 'audio_video'
  | 'likert';

export type Difficulty = 'easy' | 'medium' | 'hard';

export interface Question {
  id: string;
  assessment_id: string;
  question_type: QuestionType;
  content: string;
  image_url?: string;
  points: number;
  partial_scoring: boolean;
  negative_marking: number;
  order_index?: number;
  topic_tag?: string;
  difficulty?: Difficulty;
  blooms_level?: string;
  options?: QuestionOption[];
}

export interface QuestionOption {
  id: string;
  question_id: string;
  content: string;
  is_correct: boolean;
  match_key?: string;
  category_key?: string;
  order_position?: number;
  image_url?: string;
}

export interface QuestionCreate {
  question_type: QuestionType;
  content: string;
  image_url?: string;
  points?: number;
  partial_scoring?: boolean;
  negative_marking?: number;
  order_index?: number;
  topic_tag?: string;
  difficulty?: Difficulty;
  blooms_level?: string;
  options?: Omit<QuestionOption, 'id' | 'question_id'>[];
}

/* ── Attempt ── */
export type AttemptStatus =
  | 'not_started'
  | 'in_progress'
  | 'submitted'
  | 'terminated'
  | 'grading'
  | 'graded';

export interface AssessmentAttempt {
  id: string;
  assessment_id: string;
  student_id: string;
  student_name?: string;
  assessment_title?: string;
  status: AttemptStatus;
  started_at: string;
  submitted_at?: string;
  time_limit_seconds?: number;
  time_remaining_seconds?: number;
  score_raw?: number;
  score_percent?: number;
  grade?: string;
  violation_count: number;
  termination_reason?: string;
  server_token?: string;
  created_at: string;
}

/* ── Student Answer ── */
export interface StudentAnswer {
  id: string;
  attempt_id: string;
  question_id: string;
  answer_text?: string;
  selected_option_ids?: string[];
  matched_pairs?: Record<string, string>;
  ordered_ids?: string[];
  categorized?: Record<string, string[]>;
  hotspot_coords?: { x: number; y: number; width: number; height: number };
  code_submission?: string;
  is_flagged: boolean;
  time_spent_seconds?: number;
  score_awarded?: number;
  auto_graded: boolean;
  teacher_feedback?: string;
}

/* ── Violation ── */
export type ViolationType =
  | 'FULLSCREEN_EXIT'
  | 'TAB_SWITCH'
  | 'DEVTOOLS_DETECTED'
  | 'F11_PRESSED'
  | 'ESCAPE_PRESSED'
  | 'WINDOW_FOCUS_LOST'
  | 'PAGE_UNLOAD_ATTEMPT'
  | 'INJECTED_ELEMENT_DETECTED'
  | 'ALT_TAB'
  | 'API_MANIPULATION';

export interface Violation {
  id: string;
  attempt_id: string;
  student_id: string;
  assessment_id: string;
  violation_type: ViolationType;
  occurred_at: string;
  time_remaining_at_event?: number;
  time_deducted_seconds?: number;
  violation_count_after: number;
  resolved: boolean;
  notes?: string;
}

/* ── Analytics ── */
export interface StudentDashboard {
  overall_score_avg: number | null;
  pass_rate: number | null;
  assessments_taken: number;
  assessments_passed: number;
  streak_count: number;
  improvement_rate: number | null;
  violation_count_total: number;
  score_trend: ScoreTrendPoint[];
  subject_scores: SubjectScore[];
  weak_topics: string[];
  recent_results: ScoreTrendPoint[];
}

export interface ScoreTrendPoint {
  date: string;
  score: number;
  assessment_id: string;
}

export interface SubjectScore {
  group_id: string;
  group_name: string;
  subject: string;
  assessments_taken: number;
  average_score: number | null;
  pass_rate: number | null;
}

export interface AdminOverview {
  total_students: number;
  total_teachers: number;
  total_groups: number;
  total_assessments: number;
  university_pass_rate: number | null;
  department_stats: unknown[];
  violation_summary: Record<string, number>;
  completion_rate: number | null;
  semester_trends: unknown[];
}

export interface GroupAnalytics {
  group_id: string;
  group_name: string;
  total_assessments: number;
  total_students_enrolled: number;
  overall_pass_rate: number | null;
  average_score: number | null;
  assessment_summaries: AssessmentSummary[];
}

export interface AssessmentSummary {
  assessment_id: string;
  title: string;
  attempts_count: number;
  mean_score: number | null;
  pass_rate: number | null;
}

export interface ItemAnalysis {
  question_id: string;
  question_type: QuestionType;
  content: string;
  difficulty_index: number | null;
  discrimination_index: number | null;
  point_biserial: number | null;
  classification: string;
}

/* ── API Response Wrappers ── */
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: PaginationMeta;
}

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

export interface PaginationMeta {
  page: number;
  total: number;
  per_page: number;
}

/* ── Proctoring ── */
export interface ProctoringConfig {
  maxViolations: number;
  timePenaltyMinutes: number;
  enforceFullscreen: boolean;
  blockKeyboardShortcuts: boolean;
  tabSwitchDetection: boolean;
  devToolsDetection: boolean;
  rightClickBlock: boolean;
  copyPasteBlock: boolean;
}

export interface ViolationEvent {
  type: ViolationType;
  count: number;
  timestamp: string;
}

/* ── WebSocket Messages ── */
export type WSClientMessage =
  | { type: 'HEARTBEAT'; time_remaining: number }
  | { type: 'ANSWER_SAVE'; question_id: string; data: Record<string, unknown> }
  | { type: 'VIOLATION'; violation_type: ViolationType; time_remaining: number };

export type WSServerMessage =
  | { type: 'TIME_UPDATE'; time_remaining: number }
  | { type: 'TIME_PENALTY'; deducted: number; new_remaining: number }
  | { type: 'WARNING'; count: number; message: string }
  | { type: 'TERMINATE'; reason: string; score: number }
  | { type: 'FORCE_SUBMIT'; reason: string }
  | { type: 'ASSESSMENT_DEACTIVATED'; message: string };
