export interface User {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type Sex = "female" | "male" | "other";

export interface Profile {
  date_of_birth: string | null;
  sex: Sex | null;
  height_cm: number | null;
  weight_kg: number | null;
  blood_group: string | null;
  is_pregnant: boolean;
  smoker: boolean;
  alcohol_use: "none" | "occasional" | "regular" | null;
  activity_level: "low" | "moderate" | "high" | null;
  allergies: string[];
  chronic_conditions: string[];
  current_medications: string[];
  emergency_contact: string | null;
  age?: number | null;
  bmi?: number | null;
  updated_at?: string | null;
}

export type HistoryCategory = "condition" | "surgery" | "medication" | "allergy" | "vaccination" | "visit" | "other";

export interface HistoryEntry {
  id: number;
  category: HistoryCategory;
  title: string;
  details: string | null;
  event_date: string | null;
  is_ongoing: boolean;
  created_at: string;
}

export type LabStatus = "low" | "normal" | "high" | "critical_low" | "critical_high";

export interface LabValue {
  test: string;
  key: string;
  value: number;
  unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  status: LabStatus;
  raw?: string | null;
  explanation?: string;
  report_id?: number;
}

export interface ImageFeatures {
  width: number;
  height: number;
  mode: string;
  format: string | null;
  is_grayscale: boolean;
  mean_brightness: number;
  contrast: number;
  sharpness: number;
  quality_warnings: string[];
  quality_ok: boolean;
}

export interface ReportSummary {
  id: number;
  kind: "report" | "image";
  title: string;
  report_type: string | null;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  report_date: string | null;
  extraction_status: "pending" | "done" | "partial" | "failed" | "skipped";
  extraction_method: string | null;
  lab_count: number;
  created_at: string;
}

export interface ReportDetail extends ReportSummary {
  extracted_text: string | null;
  extraction_error: string | null;
  lab_values: LabValue[];
  image_features: ImageFeatures | null;
}

export type Urgency = "emergency" | "urgent" | "soon" | "routine";

export interface Factor {
  type: "symptom" | "lab" | "risk_factor" | "duration" | "image" | "missing";
  label: string;
  points: number;
  direction: "supports" | "against";
  share: number;
}

export interface ConditionMatch {
  key: string;
  name: string;
  category: string;
  description: string;
  match_score: number;
  score_components?: { saturation: number; coverage: number };
  confidence: "low" | "moderate" | "high";
  evidence_points: number;
  factors: Factor[];
  not_reported: string[];
  suggested_tests: string[];
  specialist: string | null;
  notes: string[];
}

export interface RedFlag {
  code: string;
  level: Urgency;
  title: string;
  message: string;
}

export interface SourceDoc {
  id?: string;
  reasons?: string[];
  slug: string;
  title: string;
  source: "WHO" | "CDC" | string;
  url: string;
  topics: string[];
  origin: string;
  score: number;
  snippet: string;
}

export interface CarePlan {
  urgency: Urgency;
  follow_up: string;
  immediate_actions: string[];
  self_care: string[];
  when_to_see_doctor: string[];
  suggested_tests: string[];
  specialists: string[];
  personalised: string[];
}

export interface ImageResult {
  report_id: number;
  title: string;
  report_type: string | null;
  quality: Partial<ImageFeatures>;
  error?: string;
  ai_observation: {
    provider: string;
    is_mock: boolean;
    observations: string[];
    possible_findings: string[];
    note: string | null;
    quality: string | null;
    unverified: boolean;
  } | null;
}

export interface AiStatus {
  status: "generated" | "mock" | "failed" | "skipped_emergency";
  is_real_ai: boolean;
  provider: string;
  model: string;
  reason: string | null;
  message: string | null;
  attempts: { provider: string; ok: boolean; kind?: string; error?: string }[];
}

export interface Citation {
  id: string;
  title: string;
  source: string;
  url: string;
  excerpt: string;
  reasons: string[];
}

export interface AssessedCondition {
  key: string;
  name: string;
  status: "unconfirmed";
  is_diagnosis: false;
  confidence: "low" | "moderate" | "high";
  match_score: number;
  supporting: { type: string; label: string; points: number }[];
  against: { type: string; label: string; points: number }[];
  not_reported: string[];
  history_considered: string[];
  already_in_history: boolean;
  evidence_ids: string[];
  evidence_note: string | null;
  uncertainty: string[];
  ai_explanation: string | null;
  ai_cites: string[];
  ai_grounded: boolean;
}

export interface Assessment {
  diagnosis_status: string;
  ai: AiStatus;
  urgency: { level: Urgency; guidance: string; set_by: string; red_flag_codes: string[] };
  possible_conditions: AssessedCondition[];
  uncertainty: { text: string; source: "rules" | "ai" }[];
  limitations: string[];
  history_considered: { conditions: string[]; medications: string[]; allergies: string[]; family_history: string[] };
  citations: Citation[];
}

export interface AnalysisResult {
  ai?: AiStatus;
  assessment?: Assessment;
  disclaimer: string;
  is_mock: boolean;
  urgency: Urgency;
  urgency_guidance: string;
  red_flags: RedFlag[];
  symptoms: { key: string; label: string }[];
  conditions: ConditionMatch[];
  lab_values: LabValue[];
  abnormal_lab_count: number;
  reports: { report_id: number; title: string; extraction_status: string; lab_count: number }[];
  images: ImageResult[];
  care_plan: CarePlan;
  sources: SourceDoc[];
  explanation: {
    summary: string;
    report_interpretation: string;
    questions_for_doctor: string[];
    notice?: string | null;
    safety_filtered_sentences: number;
    condition_notes?: { key: string; explanation: string; cites: string[]; grounded: boolean }[];
    uncertainty?: string[];
  };
  data_completeness: Record<"symptoms" | "lab_values" | "images" | "profile", boolean>;
  limitations: string[];
  provenance: {
    engine_version: string;
    explanation_provider: string;
    explanation_model: string;
    provider_attempts: { provider: string; ok: boolean; error?: string }[];
    image_provider: unknown;
    duration_ms: number;
  };
}

export interface AnalysisInputs {
  symptoms: string[];
  symptom_text: string | null;
  duration_days: number | null;
  severity: "mild" | "moderate" | "severe" | null;
  report_ids: number[];
  image_ids: number[];
  notes: string | null;
}

export interface Analysis {
  id: number;
  status: string;
  urgency: Urgency;
  provider: string;
  is_mock: boolean;
  created_at: string;
  inputs: AnalysisInputs;
  result: AnalysisResult;
}

export interface AnalysisSummary {
  id: number;
  status: string;
  urgency: Urgency;
  provider: string;
  is_mock: boolean;
  created_at: string;
  top_condition: string | null;
  symptom_preview: string[];
}

export interface SystemStatus {
  app: string;
  environment: string;
  ai: {
    active_provider: string;
    mock_mode: boolean;
    force_mock: boolean;
    allow_mock_fallback?: boolean;
    unavailable_reason?: string | null;
    unavailable_message?: string | null;
    providers: { name: string; configured: boolean; model: string; vision: boolean }[];
  };
  ocr: { tesseract_available: boolean };
  emergency_number: string;
  crisis_line: string;
  disclaimer: string;
}
