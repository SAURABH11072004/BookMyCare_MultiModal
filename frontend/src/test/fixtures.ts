import type { AnalysisResult } from "../lib/types";

export const analysisFixture: AnalysisResult = {
  disclaimer: "BookMyCare provides educational screening information only. It is not a medical diagnosis.",
  is_mock: true,
  urgency: "urgent",
  urgency_guidance: "See a doctor within 24 hours.",
  red_flags: [{ code: "dengue_warning", level: "urgent", title: "Fever with bleeding", message: "Get a blood test today." }],
  symptoms: [{ key: "fever", label: "Fever" }],
  conditions: [
    {
      key: "dengue", name: "Dengue fever", category: "infection", description: "A mosquito-borne viral infection.",
      match_score: 0.86, score_components: { saturation: 0.98, coverage: 0.74 }, confidence: "high", evidence_points: 18,
      factors: [
        { type: "lab", label: "Platelets 85 (low)", points: 3, direction: "supports", share: 0.4 },
        { type: "symptom", label: "Fever", points: 2, direction: "supports", share: 0.3 },
        { type: "lab", label: "HbA1c normal", points: -1, direction: "against", share: 0 },
      ],
      not_reported: ["Rash"], suggested_tests: ["Dengue NS1 antigen"], specialist: "General physician", notes: [],
    },
  ],
  lab_values: [{ test: "Platelets", key: "platelets", value: 85, unit: "x10^3/µL", ref_low: 150, ref_high: 450, status: "low", explanation: "Low platelets." }],
  abnormal_lab_count: 1,
  reports: [{ report_id: 1, title: "CBC", extraction_status: "done", lab_count: 1 }],
  images: [],
  care_plan: {
    urgency: "urgent", follow_up: "Within 24 hours.", immediate_actions: ["See a doctor within 24 hours."],
    self_care: ["Drink fluids"], when_to_see_doctor: ["Bleeding gums"], suggested_tests: ["CBC"], specialists: ["General physician"], personalised: [],
  },
  sources: [{ slug: "who-dengue", title: "Dengue - WHO", source: "WHO", url: "https://www.who.int/x", topics: ["dengue"], origin: "curated", score: 3, snippet: "Dengue is a viral infection." }],
  explanation: { summary: "See a doctor within 24 hours.", report_interpretation: "Platelets are low.", questions_for_doctor: ["Do I need repeat tests?"], notice: "Mock AI mode: template output.", safety_filtered_sentences: 0 },
  data_completeness: { symptoms: true, lab_values: true, images: false, profile: false },
  limitations: ["Rule-based heuristic."],
  provenance: { engine_version: "rules-1.0", explanation_provider: "mock", explanation_model: "template-v1", provider_attempts: [{ provider: "mock", ok: true }], image_provider: null, duration_ms: 12 },
};

import type { AiStatus, Assessment } from "../lib/types";

export const citationsFixture = [
  { id: "S1", title: "Dengue - WHO", source: "WHO", url: "https://www.who.int/x", excerpt: "Dengue is a viral infection.", reasons: ["condition:dengue"] },
];

export const assessmentFixture: Assessment = {
  diagnosis_status: "screening_only_not_a_diagnosis",
  ai: { status: "generated", is_real_ai: true, provider: "gemini", model: "gemini-3.8-flash", reason: null, message: null, attempts: [{ provider: "gemini", ok: true }] },
  urgency: { level: "urgent", guidance: "See a doctor within 24 hours.", set_by: "safety_rules", red_flag_codes: ["dengue_warning"] },
  possible_conditions: [
    {
      key: "dengue", name: "Dengue fever", status: "unconfirmed", is_diagnosis: false, confidence: "high", match_score: 0.86,
      supporting: [{ type: "symptom", label: "Fever", points: 2 }], against: [], not_reported: ["Rash"],
      history_considered: ["Existing condition in your history: Type 2 diabetes"], already_in_history: false,
      evidence_ids: ["S1"], evidence_note: null, uncertainty: ["This is a screening match, not a confirmed diagnosis."],
      ai_explanation: "Fever and low platelets can fit dengue; a doctor can confirm.", ai_cites: ["S1"], ai_grounded: true,
    },
  ],
  uncertainty: [
    { text: "Condition scores come from hand-set rules.", source: "rules" },
    { text: "A blood test is needed to tell these apart.", source: "ai" },
  ],
  limitations: ["Rule-based heuristic."],
  history_considered: { conditions: ["Type 2 diabetes"], medications: [], allergies: [], family_history: [] },
  citations: citationsFixture,
};

export function withAi(ai: Partial<AiStatus> & Pick<AiStatus, "status">, extra: Partial<AnalysisResult> = {}): AnalysisResult {
  const full: AiStatus = { is_real_ai: ai.status === "generated", provider: "gemini", model: "gemini-3.8-flash", reason: null, message: null, attempts: [], ...ai };
  return {
    ...analysisFixture,
    is_mock: full.status === "mock",
    ai: full,
    assessment: { ...assessmentFixture, ai: full },
    sources: [{ ...analysisFixture.sources[0], id: "S1", reasons: ["condition:dengue"] }],
    ...extra,
  };
}
