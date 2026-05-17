export interface Task {
  id: string;
  title: string;
  description?: string;
  category?: string;
  status: "pending" | "in_progress" | "completed" | "cancelled";
  priority: number;
  due_date?: string;
  scheduled_for?: string;
  estimated_minutes?: number;
  actual_minutes?: number;
  assigned_agent?: string;
  execution_output?: string;
  times_deferred: number;
  created_at: string;
}

export interface CheckIn {
  id: string;
  checkin_type: "morning" | "midday" | "evening";
  checkin_date: string;
  mood_score?: number;
  energy_score?: number;
  stress_score?: number;
  focus_score?: number;
  sleep_hours?: number;
  sleep_quality?: number;
  exercised?: boolean;
  notes?: string;
  wins?: string[];
  struggles?: string[];
  tasks_planned?: number;
  tasks_completed?: number;
}

export interface Goal {
  id: string;
  title: string;
  description?: string;
  why?: string;
  domain?: string;
  timeframe?: string;
  status: "active" | "completed" | "paused" | "abandoned";
  progress_pct: number;
  last_action_at?: string;
  milestones?: Record<string, unknown>;
}

export interface Memory {
  id: string;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface AgentStatusCard {
  name: string;
  display_name: string;
  status: "idle" | "running";
  last_run_at?: string;
  last_output_summary?: string;
  runs_today: number;
}

export interface AgentRun {
  id: string;
  agent_name?: string;
  status: string;
  input_summary?: string;
  output_summary?: string;
  full_response?: string;
  trigger_type?: string;
  task_id?: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  accepted?: boolean;
  overridden: boolean;
  override_note?: string;
  created_at: string;
}

export interface AgentEvent {
  agent: string;
  interaction_id: string;
  status: "running" | "completed" | "failed";
  task_id?: string;
  output_summary?: string;
  error?: string;
}

export interface DashboardData {
  today: {
    date: string;
    pending_tasks: number;
    checkin_done: boolean;
    energy_level: string;
  };
  tasks: Array<{
    id: string;
    title: string;
    status: string;
    priority: number;
    category?: string;
    due_date?: string;
    times_deferred: number;
  }>;
  streak: number;
  completed_this_week: number;
  goals: Array<{
    id: string;
    title: string;
    domain?: string;
    progress_pct: number;
    drift_alert: boolean;
  }>;
  averages: {
    mood?: number;
    energy?: number;
    sleep?: number;
  };
  onboarding_done: boolean;
  has_api_keys: boolean;
  api_key_disclaimer_dismissed: boolean;
  agents: AgentStatusCard[];
}

export interface SuggestedAction {
  label: string;
  message: string;
  agent_hint?: string;
  icon?: string;
}

export interface EmailDraft {
  draft_id: string;
  to?: string;
  subject?: string;
  body_preview?: string;
}

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  agent_used?: string;
  agent_display_name?: string;
  download_url?: string;
  agents_pipeline?: string[];
  suggested_actions?: SuggestedAction[];
  email_draft?: EmailDraft;
}

export interface GeneratedFile {
  id: string;
  filename: string;
  original_name: string;
  file_format: "docx" | "xlsx" | "pdf";
  file_size_bytes: number;
  template_used?: string;
  task_description?: string;
  created_at: string;
}
