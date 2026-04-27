// ── Pagination ───────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface APIError {
  message: string;
  detail?: string | Record<string, unknown>;
  status?: number;
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export type UserRole = "admin" | "staff" | "student";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Academic ─────────────────────────────────────────────────────────────────

export interface DepartmentResponse {
  id: string;
  name: string;
  code: string;
  description: string | null;
  created_at: string;
}

export interface ClassRoomResponse {
  id: string;
  name: string;
  grade_level: number;
  section: string;
  department_id: string;
  department?: DepartmentResponse;
  academic_year: string;
  created_at: string;
}

export interface SubjectResponse {
  id: string;
  name: string;
  code: string;
  classroom_id: string;
  classroom?: ClassRoomResponse;
  created_at: string;
}

export interface SessionYearResponse {
  id: string;
  start_year: number;
  end_year: number;
  is_current: boolean;
}

// ── Students ─────────────────────────────────────────────────────────────────

export interface StudentProfileResponse {
  id: string;
  user_id: string;
  user?: UserResponse;
  student_id: string;
  classroom_id: string;
  classroom?: ClassRoomResponse;
  session_year_id: string;
  date_of_birth: string | null;
  gender: string | null;
  phone: string | null;
  address: string | null;
  guardian_name: string | null;
  guardian_phone: string | null;
  enrollment_date: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudentAnalyticsResponse {
  student_id: string;
  assignment_completion_rate: number;
  average_score: number;
  attendance_rate: number;
  quiz_average: number;
  total_assignments: number;
  submitted_assignments: number;
  total_quizzes: number;
  completed_quizzes: number;
}

// ── Staff ─────────────────────────────────────────────────────────────────────

export interface StaffProfileResponse {
  id: string;
  user_id: string;
  user?: UserResponse;
  staff_id: string;
  department_id: string | null;
  department?: DepartmentResponse;
  designation: string | null;
  date_of_birth: string | null;
  gender: string | null;
  phone: string | null;
  address: string | null;
  joining_date: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Assignments ───────────────────────────────────────────────────────────────

export type AssignmentStatus = "draft" | "published" | "closed";

export interface AssignmentResponse {
  id: string;
  title: string;
  description: string | null;
  subject_id: string;
  subject?: SubjectResponse;
  created_by: string;
  created_by_user?: UserResponse;
  due_date: string;
  max_score: number;
  status: AssignmentStatus;
  allow_late: boolean;
  created_at: string;
  updated_at: string;
}

export type SubmissionGradeStatus = "pending" | "graded" | "not_submitted";

export interface SubmissionResponse {
  id: string;
  assignment_id: string;
  assignment?: AssignmentResponse;
  student_id: string;
  student?: StudentProfileResponse;
  content: string;
  submitted_at: string;
  grade_status: SubmissionGradeStatus;
  score: number | null;
  max_score: number | null;
  ai_feedback: string | null;
  graded_at: string | null;
  is_late: boolean;
}

// ── Assessments (Quizzes) ─────────────────────────────────────────────────────

export interface QuizResponse {
  id: string;
  title: string;
  description: string | null;
  subject_id: string;
  subject?: SubjectResponse;
  created_by: string;
  time_limit_minutes: number | null;
  max_attempts: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface QuizQuestionResponse {
  id: string;
  quiz_id: string;
  question_text: string;
  question_type: "mcq" | "essay" | "short_answer";
  options: Record<string, string> | null;
  correct_answer: string | null;
  marks: number;
  order: number;
}

export interface QuizAttemptResponse {
  id: string;
  quiz_id: string;
  quiz?: QuizResponse;
  student_id: string;
  started_at: string;
  submitted_at: string | null;
  score: number | null;
  max_score: number;
  passed: boolean | null;
  grade_status: SubmissionGradeStatus;
  ai_feedback: string | null;
}

// ── Attendance ────────────────────────────────────────────────────────────────

export type AttendanceStatus = "present" | "absent" | "late" | "excused";

export interface AttendanceRecordResponse {
  id: string;
  student_id: string;
  classroom_id: string;
  date: string;
  status: AttendanceStatus;
  remarks: string | null;
  recorded_by: string;
  created_at: string;
}

export interface AttendanceSummaryResponse {
  student_id: string;
  total_days: number;
  present: number;
  absent: number;
  late: number;
  excused: number;
  attendance_rate: number;
}

// ── Notifications ────────────────────────────────────────────────────────────

export interface NotificationResponse {
  id: string;
  user_id: string;
  title: string;
  message: string;
  notification_type: string;
  reference_id: string | null;
  is_read: boolean;
  created_at: string;
}

// ── Leave ─────────────────────────────────────────────────────────────────────

export type LeaveStatus = "pending" | "approved" | "rejected";

export interface LeaveRequestResponse {
  id: string;
  staff_id: string;
  staff?: StaffProfileResponse;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: LeaveStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

// ── Feedback ──────────────────────────────────────────────────────────────────

export interface FeedbackResponse {
  id: string;
  student_id: string;
  subject_id: string;
  staff_id: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface ClassroomAnalyticsResponse {
  classroom_id: string;
  total_students: number;
  average_attendance: number;
  average_assignment_score: number;
  average_quiz_score: number;
  assignment_completion_rate: number;
  recent_activity: {
    date: string;
    type: string;
    count: number;
  }[];
}

export interface PlatformAnalyticsResponse {
  total_users: number;
  total_students: number;
  total_staff: number;
  total_classrooms: number;
  total_assignments: number;
  total_quizzes: number;
  active_sessions: number;
  submissions_today: number;
  grading_queue: number;
}
