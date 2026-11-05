
export interface User {
  id: number;
  email: string;
  email_verified: boolean;
  name: string;
  timezone: string;
  week_starts_on: number;
  auth_providers: string[];
  created_at: string;
}

export interface SessionResponse {
  user: User;
  access_token: string;
  token_type: "Bearer";
  expires_in: number;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface ApiSuccess<T> {
  data: T;
}

export type HabitDayStatus =
  | "before_start"
  | "future"
  | "archived"
  | "completed"
  | "bonus"
  | "rest"
  | "pending"
  | "missed";

export interface HabitGridDay {
  date: string;
  weekday: number;
  scheduled: boolean;
  completed: boolean;
  is_bonus: boolean;
  status: HabitDayStatus;
}

export interface MonthlyHabit {
  habit_id: string;
  habit_name: string;
  days: HabitGridDay[];
}

export interface MonthlyGridResponse {
  month: string;
  today: string;
  habits: MonthlyHabit[];
}

export interface CompletionResponse {
  habit_id: string;
  date: string;
  completed: boolean;
  is_bonus?: boolean;
}

export interface Task {
  id: string;
  title: string;
  notes: string;
  date: string;
  is_completed: boolean;
  completed_at: string | null;
  sort_order: number;
  carried_from_task_id: string | null;
}

export interface TaskListResponse {
  date: string;
  tasks: Task[];
  completed: number;
  total: number;
  completion_rate: number | null;
}

export interface CreateTaskResponse {
  task: Task;
}

export interface UpdateTaskResponse {
  task: Task;
}
export interface HabitPerformance {
  habit_id: string;
  habit_name: string;
  scheduled_days: number;
  completed_days: number;
  missed_days: number;
  pending_days: number;
  completion_rate: number | null;
}

export interface DailyTrend {
  date: string;
  habits_scheduled: number;
  habits_completed: number;
  tasks_total: number;
  tasks_completed: number;
  overall_total: number;
  overall_completed: number;
  overall_completion_rate: number | null;
}

export interface ReportOverview {
  habit_scheduled: number;
  habit_completed: number;
  habit_missed: number;
  habit_pending: number;
  habit_completion_rate: number | null;
  task_total: number;
  task_completed: number;
  task_pending: number;
  task_carried_forward: number;
  task_completion_rate: number | null;
  overall_total: number;
  overall_completed: number;
  overall_completion_rate: number | null;
}

export interface ReportPeriod {
  start: string;
  end: string;
  through: string | null;
}

export interface ProgressReport {
  period: ReportPeriod;
  overview: ReportOverview;
  habits: HabitPerformance[];
  strongest_habits: HabitPerformance[];
  weakest_habits: HabitPerformance[];
  daily_trends: DailyTrend[];
  best_day: DailyTrend | null;
  worst_day: DailyTrend | null;
}
