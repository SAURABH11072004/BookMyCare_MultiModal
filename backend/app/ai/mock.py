"""Deterministic, template-based provider used when no API keys are configured.

It never invents findings: it only restates the structured, rule-based results
passed in `LLMRequest.context`, and labels its output as mock."""
from __future__ import annotations

import json

from app.ai.base import LLMProvider, LLMRequest

MOCK_NOTICE = (
    "Mock AI mode: this explanation was assembled from templates using the rule-based results above, "
    "not by a language model. It is for development and demonstration only."
)


class MockProvider(LLMProvider):
    name = "mock"
    is_mock = True
    supports_vision = True  # accepts images but never interprets them

    def available(self) -> bool:
        return True

    @property
    def model(self) -> str:
        return "template-v1"

    def _generate(self, req: LLMRequest) -> str:
        if req.task == "image_observation":
            return json.dumps({
                "observations": [],
                "possible_findings": [],
                "note": "Mock mode: no image model is configured, so the image content was not interpreted.",
            })
        if req.task == "analysis_explanation":
            return json.dumps(self._explanation(req.context))
        if req.task == "health_answer":
            docs = req.context.get("documents", [])
            titles = ", ".join(d["title"] for d in docs[:3]) or "no matching documents"
            return json.dumps({"answer": f"{MOCK_NOTICE} Relevant public-health sources: {titles}. Please read the linked pages for details."})
        return json.dumps({"text": MOCK_NOTICE})

    @staticmethod
    def _explanation(ctx: dict) -> dict:
        conditions = ctx.get("conditions", [])
        labs = ctx.get("labs", [])
        abnormal = ctx.get("abnormal_labs") or [l for l in labs if l.get("status") not in (None, "normal")]
        if not labs and ctx.get("lab_count"):
            labs = [{}] * ctx["lab_count"]
        urgency = ctx.get("urgency", "routine")
        symptoms = ctx.get("symptoms") or ctx.get("symptom_labels") or []

        parts = []
        # For urgent/emergency results the engine puts the safety guidance first.
        if urgency in ("soon", "routine"):
            parts.append({
                "soon": "Consider booking a doctor's appointment in the next few days.",
                "routine": "No urgent warning signs were detected in the information provided.",
            }[urgency])
        if symptoms:
            parts.append(f"You reported: {', '.join(symptoms[:8])}.")
        if conditions:
            top = conditions[0]
            others = [c["name"] for c in conditions[1:3]]
            parts.append(
                f"The screening rules found the closest match with '{top['name']}' "
                f"(evidence match {round(top['match_score'] * 100)}%, {top['confidence']} confidence). This is not a diagnosis."
            )
            if others:
                parts.append(f"Other possibilities to discuss: {', '.join(others)}.")
        else:
            parts.append("The screening rules did not find a strong match with any condition in the knowledge base.")

        if abnormal:
            lab_txt = "; ".join(f"{l['test']} {l['value']} {l.get('unit') or ''} ({l['status'].replace('_', ' ')})".replace("  ", " ") for l in abnormal[:6])
            interp = f"Values outside the typical reference range: {lab_txt}. Your doctor will interpret these alongside your history."
        elif labs:
            interp = "All recognised lab values were within typical reference ranges."
        else:
            interp = "No lab values were recognised in the selected reports."

        notes = []
        for c in conditions[:3]:
            if not c.get("key"):
                continue
            why = ", ".join(c.get("supporting", [])[:3]) or "the reported information"
            text = f"Suggested because of: {why}."
            if c.get("already_in_patient_history"):
                text += " You already listed this condition in your history."
            notes.append({"key": c["key"], "explanation": text, "cites": list(c.get("evidence_ids", []))[:2]})

        questions = ["Do these results need repeat or confirmatory testing?", "Which warning signs should make me seek care sooner?"]
        if conditions:
            questions.insert(0, f"Could my symptoms be related to {conditions[0]['name'].split('(')[0].strip().lower()}, and how can we confirm or rule it out?")
        return {
            "summary": " ".join(parts),
            "report_interpretation": interp,
            "condition_notes": notes,
            "uncertainty": ["Template output: no language model reviewed these results."],
            "questions_for_doctor": questions,
            "notice": MOCK_NOTICE,
        }
