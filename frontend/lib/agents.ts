/** Shared agent metadata used across the frontend. */

export const AGENT_DESCRIPTIONS: Record<string, string> = {
  focus: "Task prioritization & daily focus planning",
  health: "Mood, sleep & energy analysis",
  execution: "Step-by-step task breakdowns",
  chaos_triage: "Crisis mode — triages overwhelm",
  goals: "Goal tracking & drift alerts",
  delegate: "Research & admin delegation",
  research: "Web search & structured findings",
  worker: "Document, spreadsheet & PDF generation",
  email: "Gmail inbox, search & draft replies",
};

export const AGENT_COLORS: Record<string, string> = {
  focus: "#00ff88",
  health: "#00d4ff",
  execution: "#ff00ff",
  chaos_triage: "#ff3366",
  goals: "#ffcc00",
  delegate: "#8b5cf6",
  research: "#00aaff",
  worker: "#ff5500",
  email: "#ea4335",
};

export const AGENT_LABELS: Record<string, string> = {
  supervisor: "Routing",
  focus: "Focus",
  health: "Health",
  execution: "Execution",
  chaos_triage: "Triage",
  synthesis: "Life OS",
  goals: "Goals",
  delegate: "Research",
  pattern_learning: "Patterns",
  weekly_review: "Review",
  research: "Research",
  worker: "Worker",
  email: "Email",
};
