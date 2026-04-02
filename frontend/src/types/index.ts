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
  subject_id?: string;
  subject_name?: string;
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
  subject_id?: string;
  subject_name?: string;
  group_subject_id?: string;
  group_subject_name?: string;
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
  block_keyboard_shortcuts: boolean;
  tab_switch_detection: boolean;
  devtools_detection: boolean;
  right_click_block: boolean;
  copy_paste_block: boolean;
  webcam_proctoring: boolean;
  access_token?: string;
  is_published: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  questions?: Question[];
}

export interface AssessmentProctoringPayload {
  enforce_fullscreen: boolean;
  max_violations: number;
  time_penalty_minutes: number;
  block_keyboard_shortcuts: boolean;
  tab_switch_detection: boolean;
  devtools_detection: boolean;
  right_click_block: boolean;
  copy_paste_block: boolean;
  webcam_proctoring?: boolean;
}

export interface AssessmentCreate {
  title: string;
  description?: string;
  assessment_type: AssessmentType;
  format_type?: string;
  group_id?: string;
  subject_id?: string;
  time_limit_minutes?: number;
  available_from?: string;
  available_until?: string;
  max_attempts?: number;
  scoring_policy?: string;
  passing_score?: number;
  score_release_policy?: ScoreReleasePolicy;
  shuffle_questions?: boolean;
  shuffle_options?: boolean;
  proctoring: AssessmentProctoringPayload;
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

export type CodeExecutionMode = 'stdin_stdout' | 'function';

export interface CodeQuestionTestCase {
  input: string;
  output: string;
  is_hidden?: boolean;
}

export interface CodeQuestionConfig extends Record<string, unknown> {
  language?: string;
  execution_mode?: CodeExecutionMode;
  function_name?: string;
  starter_code?: string;
  test_cases?: CodeQuestionTestCase[];
  visible_test_cases?: CodeQuestionTestCase[];
  hidden_test_cases?: CodeQuestionTestCase[];
  time_limit_seconds?: number;
  memory_limit_mb?: number;
}

export interface CodeRunCaseResult {
  index: number;
  input: string;
  expected_output: string;
  actual_output: string;
  passed: boolean;
  error?: string | null;
}

export interface CodeRunResult {
  language: string;
  execution_mode: CodeExecutionMode;
  passed_cases: number;
  total_cases: number;
  feedback: string;
  cases: CodeRunCaseResult[];
}

export type QuestionConfig = Record<string, unknown>;

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
  topic_id?: string;
  topic_name?: string;
  module_id?: string;
  module_name?: string;
  subject_id?: string;
  subject_name?: string;
  difficulty?: Difficulty;
  blooms_level?: string;
  config?: QuestionConfig;
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
  topic_id?: string;
  difficulty?: Difficulty;
  blooms_level?: string;
  config?: QuestionConfig;
  options?: Omit<QuestionOption, 'id' | 'question_id'>[];
}

export interface QuestionRevision {
  id: string;
  question_id: string;
  version_number: number;
  source: string;
  summary?: string;
  snapshot: Record<string, unknown>;
  created_by_id?: string;
  created_at: string;
}

export interface BulkQuestionPreviewItem {
  index: number;
  is_valid: boolean;
  question_type?: string;
  content_preview?: string;
  assessment_id?: string;
  assessment_title?: string;
  question_bank_id?: string;
  difficulty?: string;
  points?: number;
  topic_tag?: string;
  resolved_topic_id?: string;
  resolved_topic_name?: string;
  options_count: number;
  visible_test_cases: number;
  hidden_test_cases: number;
  warnings: string[];
  errors: string[];
}

export interface BulkQuestionPreviewResponse {
  total_items: number;
  valid_items: number;
  invalid_items: number;
  questions: BulkQuestionPreviewItem[];
}

/* -- Curriculum -- */
export interface CurriculumTopic {
  id: string;
  module_id: string;
  module_name?: string;
  subject_id?: string;
  subject_name?: string;
  name: string;
  description?: string;
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface CurriculumModule {
  id: string;
  subject_id: string;
  name: string;
  description?: string;
  order_index: number;
  created_at: string;
  updated_at: string;
  topics?: CurriculumTopic[];
}

export interface CurriculumSubject {
  id: string;
  name: string;
  code?: string;
  description?: string;
  created_at: string;
  updated_at: string;
  modules?: CurriculumModule[];
}

export interface CurriculumTree {
  subjects: CurriculumSubject[];
}

export interface LegacyGroupMapping {
  group_id: string;
  group_name: string;
  legacy_subject?: string;
  current_subject_id?: string;
  current_subject_name?: string;
  suggested_subject_id?: string;
  suggested_subject_name?: string;
}

export interface LegacyQuestionMapping {
  question_id: string;
  assessment_id?: string;
  assessment_title?: string;
  content_preview: string;
  legacy_topic?: string;
  subject_id?: string;
  subject_name?: string;
  current_topic_id?: string;
  current_topic_name?: string;
  suggested_topic_id?: string;
  suggested_topic_name?: string;
}

export interface CurriculumReviewQueue {
  groups: LegacyGroupMapping[];
  questions: LegacyQuestionMapping[];
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
  student_name?: string | null;
  selected_semester?: string | null;
  available_semesters?: string[];
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
  topic_performance?: TopicPerformance[];
  comparison_summary?: ComparisonSummary;
  insights?: string[];
}

export interface ScoreTrendPoint {
  date: string;
  score: number;
  assessment_id: string;
  assessment_title?: string;
  group_name?: string | null;
  subject?: string | null;
  passed?: boolean;
}

export interface SubjectScore {
  group_id: string;
  group_name: string;
  subject: string;
  assessments_taken: number;
  average_score: number | null;
  pass_rate: number | null;
  group_average?: number | null;
  delta_from_group_avg?: number | null;
}

export interface TopicPerformance {
  topic: string;
  average_score: number;
  attempts: number;
  needs_attention: boolean;
}

export interface ComparisonSummary {
  key?: string;
  label?: string;
  description?: string;
  student_average: number | null;
  peer_average: number | null;
  delta_vs_peer: number | null;
  percentile_estimate: number | null;
  peer_attempts?: number;
  peer_students?: number;
}

export interface ReviewSubjectScore {
  subject_id: string;
  subject_name: string;
  assessments_taken: number;
  assessment_titles: string[];
  average_score: number | null;
  peer_average: number | null;
  delta_vs_peer: number | null;
  pass_rate: number | null;
}

export interface ReviewPeriodBreakdown {
  label: string;
  average_score: number | null;
  pass_rate: number | null;
  assessments_taken: number;
}

export interface StudentReview {
  student_name?: string | null;
  period: 'semester' | 'year';
  selected_academic_year?: string | null;
  selected_semester?: string | null;
  available_academic_years: string[];
  available_semesters: string[];
  overall_score_avg: number | null;
  pass_rate: number | null;
  assessments_taken: number;
  assessments_passed: number;
  streak_count: number;
  improvement_rate: number | null;
  violation_count_total: number;
  score_trend: ScoreTrendPoint[];
  subject_scores: ReviewSubjectScore[];
  weak_topics: string[];
  topic_performance: TopicPerformance[];
  comparison_summary?: ComparisonSummary | null;
  comparison_matrix: ComparisonSummary[];
  period_breakdown: ReviewPeriodBreakdown[];
  insights: string[];
  recent_results: ScoreTrendPoint[];
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
