import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AlertOctagon, ArrowLeft, Bot, CalendarClock, ChevronDown, ClipboardCheck, FlaskConical, HeartHandshake, ImageIcon,
  Info, Printer, ShieldAlert, Stethoscope, Trash2, UserCheck,
} from "lucide-react";
import { MockBadge, UrgencyBadge } from "../components/badges";
import LabTable from "../components/LabTable";
import { Alert, Badge, Button, Card, PageHeader, ProgressBar, Spinner, cx } from "../components/ui";
import { SourceCard } from "./Library";
import { api } from "../lib/api";
import { confidenceClass, formatDateTime, pct, urgencyMeta } from "../lib/format";
import type { ConditionMatch, Factor, AnalysisResult } from "../lib/types";
import { useAsync } from "../lib/useAsync";

const FACTOR_LABEL: Record<Factor["type"], string> = {
  symptom: "Symptom", lab: "Lab result", risk_factor: "Risk factor", duration: "Duration", image: "Image", missing: "Missing",
};

export function FactorList({ factors }: { factors: Factor[] }) {
  return (
    <ul className="space-y-2">
      {factors.map((f, i) => (
        <li key={i} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 text-sm">
          <div className="flex min-w-0 items-center gap-2">
            <Badge className={f.direction === "against" ? "bg-rose-50 text-rose-700" : "bg-slate-100 text-slate-600"}>{FACTOR_LABEL[f.type]}</Badge>
            <span className={cx("truncate", f.direction === "against" && "text-rose-700")} title={f.label}>{f.direction === "against" ? "− " : ""}{f.label}</span>
          </div>
          <span className="text-xs tabular-nums text-slate-500">{f.points > 0 ? `+${f.points}` : f.points !== 0 ? f.points : ""}</span>
          {f.direction === "supports" && f.share > 0 && (
            <div className="col-span-2"><ProgressBar value={f.share} className="bg-brand-400" label={`${f.label} contribution`} /></div>
          )}
        </li>
      ))}
    </ul>
  );
}

function ConditionCard({ c, rank }: { c: ConditionMatch; rank: number }) {
  const [open, setOpen] = useState(rank === 0);
  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <button className="flex w-full flex-col gap-3 p-4 text-left sm:flex-row sm:items-center" onClick={() => setOpen(!open)} aria-expanded={open}>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-400">#{rank + 1}</span>
            <h3 className="font-semibold text-slate-900">{c.name}</h3>
            <Badge className={confidenceClass(c.confidence)}>{c.confidence} confidence</Badge>
          </div>
          <p className="mt-1 text-sm text-slate-500">{c.description}</p>
        </div>
        <div className="flex w-full items-center gap-3 sm:w-56">
          <div className="flex-1"><ProgressBar value={c.match_score} label={`${c.name} evidence match`} /></div>
          <span className="w-12 text-right text-sm font-semibold tabular-nums">{pct(c.match_score)}</span>
          <ChevronDown className={cx("h-4 w-4 text-slate-400 transition", open && "rotate-180")} />
        </div>
      </button>
      {open && (
        <div className="grid gap-5 border-t border-slate-100 p-4 md:grid-cols-2">
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Why this was suggested</h4>
            <FactorList factors={c.factors} />
            {c.score_components && (
              <p className="mt-3 text-xs text-slate-500">
                Score = 50% evidence strength ({pct(c.score_components.saturation)}) + 50% feature coverage ({pct(c.score_components.coverage)}). Heuristic, not a probability.
              </p>
            )}
          </div>
          <div className="space-y-3 text-sm">
            {c.notes.map((n) => <Alert key={n} kind="info">{n}</Alert>)}
            {c.not_reported.length > 0 && (
              <div><h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Typical features you did not report</h4><p className="text-slate-600">{c.not_reported.join(", ")}</p></div>
            )}
            {c.suggested_tests.length > 0 && (
              <div><h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Tests a doctor may consider</h4><ul className="list-disc pl-5 text-slate-600">{c.suggested_tests.map((t) => <li key={t}>{t}</li>)}</ul></div>
            )}
            {c.specialist && <div><h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Who to see</h4><p className="text-slate-600">{c.specialist}</p></div>}
          </div>
        </div>
      )}
    </div>
  );
}

function ListBlock({ icon: Icon, title, items }: { icon: typeof Info; title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800"><Icon className="h-4 w-4 text-brand-600" /> {title}</h3>
      <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">{items.map((x) => <li key={x}>{x}</li>)}</ul>
    </div>
  );
}

export function ResultView({ result: r }: { result: AnalysisResult }) {
  const meta = urgencyMeta[r.urgency];
  return (
    <div className="space-y-6">
      <div className={cx("rounded-xl border-2 p-5", meta.ring)} data-testid="urgency-banner">
        <div className="flex flex-wrap items-center gap-3">
          {r.urgency === "emergency" ? <AlertOctagon className="h-6 w-6" /> : <CalendarClock className="h-6 w-6" />}
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide opacity-80">Recommended next step</div>
            <div className="text-lg font-semibold">{r.urgency_guidance}</div>
          </div>
        </div>
      </div>

      {r.red_flags.length > 0 && (
        <Card title={<span className="flex items-center gap-2 text-red-700"><ShieldAlert className="h-5 w-5" /> Warning signs detected</span>}>
          <ul className="space-y-3">
            {r.red_flags.map((f) => (
              <li key={f.code} className="flex flex-col items-start gap-1 sm:flex-row sm:gap-3">
                <span className="shrink-0"><UrgencyBadge urgency={f.level} /></span>
                <div><p className="font-medium text-slate-900">{f.title}</p><p className="text-sm text-slate-600">{f.message}</p></div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card
        title={<span className="flex items-center gap-2"><Bot className="h-5 w-5 text-brand-600" /> Summary</span>}
        actions={r.is_mock ? <MockBadge /> : <Badge className="bg-brand-50 text-brand-800">AI: {r.provenance.explanation_provider}</Badge>}
      >
        <div className="space-y-3 text-sm leading-relaxed text-slate-700">
          <p>{r.explanation.summary}</p>
          {r.explanation.notice && <p className="text-xs text-amber-800">{r.explanation.notice}</p>}
          {r.explanation.safety_filtered_sentences > 0 && (
            <p className="text-xs text-slate-500">{r.explanation.safety_filtered_sentences} AI sentence(s) were removed by the safety filter (dosing or diagnostic claims).</p>
          )}
        </div>
      </Card>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Possible conditions to discuss with a doctor</h2>
        {r.conditions.length === 0 ? (
          <Alert kind="info">No condition in the knowledge base matched strongly. This does not mean you are well - see a doctor if you are concerned.</Alert>
        ) : (
          <div className="space-y-3">{r.conditions.map((c, i) => <ConditionCard key={c.key} c={c} rank={i} />)}</div>
        )}
      </section>

      {(r.lab_values.length > 0 || r.reports.length > 0) && (
        <Card title={<span className="flex items-center gap-2"><FlaskConical className="h-5 w-5 text-brand-600" /> Report interpretation</span>} subtitle={`${r.abnormal_lab_count} of ${r.lab_values.length} recognised values outside typical range`}>
          {r.explanation.report_interpretation && <p className="mb-4 text-sm text-slate-700">{r.explanation.report_interpretation}</p>}
          <LabTable labs={r.lab_values} />
        </Card>
      )}

      {r.images.length > 0 && (
        <Card title={<span className="flex items-center gap-2"><ImageIcon className="h-5 w-5 text-brand-600" /> Medical images</span>}>
          <ul className="space-y-4">
            {r.images.map((im) => (
              <li key={im.report_id} className="space-y-2 text-sm">
                <div className="font-medium text-slate-800">{im.title}</div>
                {im.quality?.quality_warnings?.length ? <Alert kind="warning">{im.quality.quality_warnings.join(" ")}</Alert> : <p className="text-slate-500">No image quality issues detected.</p>}
                {im.ai_observation && (im.ai_observation.is_mock ? (
                  <p className="text-slate-500">{im.ai_observation.note}</p>
                ) : (
                  <Alert kind="info" title={`Unverified AI observations (${im.ai_observation.provider})`}>
                    {im.ai_observation.observations.length ? <ul className="list-disc pl-4">{im.ai_observation.observations.map((o) => <li key={o}>{o}</li>)}</ul> : "No observations."}
                    {im.ai_observation.note && <p className="mt-1 text-xs">{im.ai_observation.note}</p>}
                  </Alert>
                ))}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card title={<span className="flex items-center gap-2"><HeartHandshake className="h-5 w-5 text-brand-600" /> Your care plan</span>} subtitle={`Follow-up: ${r.care_plan.follow_up}`}>
        <div className="grid gap-6 md:grid-cols-2">
          <ListBlock icon={AlertOctagon} title="Do this first" items={r.care_plan.immediate_actions} />
          <ListBlock icon={UserCheck} title="Personalised for you" items={r.care_plan.personalised} />
          <ListBlock icon={HeartHandshake} title="Self-care while you wait" items={r.care_plan.self_care} />
          <ListBlock icon={Stethoscope} title="See a doctor if" items={r.care_plan.when_to_see_doctor} />
          <ListBlock icon={FlaskConical} title="Tests to ask about" items={r.care_plan.suggested_tests} />
          <ListBlock icon={ClipboardCheck} title="Questions for your doctor" items={r.explanation.questions_for_doctor} />
        </div>
        {r.care_plan.specialists.length > 0 && <p className="mt-4 text-sm text-slate-600"><strong>Relevant specialists:</strong> {r.care_plan.specialists.join("; ")}</p>}
      </Card>

      {r.sources.length > 0 && (
        <Card title="Trusted sources" subtitle="WHO and CDC guidance related to these results.">
          <div className="grid gap-3 md:grid-cols-2">{r.sources.map((s) => <SourceCard key={s.slug} doc={s} />)}</div>
        </Card>
      )}

      <Card title={<span className="flex items-center gap-2"><Info className="h-5 w-5 text-slate-500" /> How this result was produced</span>}>
        <div className="grid gap-6 md:grid-cols-2 text-sm">
          <div>
            <h3 className="mb-2 font-semibold text-slate-800">Data used</h3>
            <ul className="space-y-1">
              {Object.entries(r.data_completeness).map(([k, v]) => (
                <li key={k} className="flex items-center gap-2"><span className={cx("h-2 w-2 rounded-full", v ? "bg-emerald-500" : "bg-slate-300")} />{k.replace("_", " ")}: {v ? "provided" : "not provided"}</li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-slate-500">
              Engine {r.provenance.engine_version} · explanation by {r.provenance.explanation_provider} ({r.provenance.explanation_model}) · {r.provenance.duration_ms} ms
              {r.provenance.provider_attempts.some((a) => !a.ok) && ` · fell back after: ${r.provenance.provider_attempts.filter((a) => !a.ok).map((a) => a.provider).join(", ")}`}
            </p>
          </div>
          <div>
            <h3 className="mb-2 font-semibold text-slate-800">Limitations</h3>
            <ul className="list-disc space-y-1 pl-5 text-slate-600">{r.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
          </div>
        </div>
      </Card>

      <Alert kind="warning" title="Important">{r.disclaimer}</Alert>
    </div>
  );
}

export default function AnalysisResultPage() {
  const id = Number(useParams().id);
  const nav = useNavigate();
  const { data, loading, error } = useAsync(() => api.getAnalysis(id), [id]);
  if (loading) return <Spinner label="Loading analysis…" />;
  if (error || !data) return <Alert kind="error">{error ?? "Not found"}</Alert>;

  async function remove() {
    if (!window.confirm("Delete this analysis?")) return;
    await api.deleteAnalysis(id);
    nav("/analyses");
  }

  return (
    <div>
      <Link to="/analyses" className="no-print mb-3 inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"><ArrowLeft className="h-4 w-4" /> All analyses</Link>
      <PageHeader
        title={`Analysis #${data.id}`}
        description={<span className="flex flex-wrap items-center gap-2">{formatDateTime(data.created_at)} <UrgencyBadge urgency={data.urgency} /> {data.is_mock && <MockBadge />}</span>}
        actions={
          <div className="no-print flex gap-2">
            <Button variant="secondary" onClick={() => window.print()}><Printer className="h-4 w-4" /> Print / PDF</Button>
            <Button variant="danger" onClick={remove}><Trash2 className="h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {data.result.symptoms.length > 0 && (
        <p className="mb-4 text-sm text-slate-600"><strong>Symptoms considered:</strong> {data.result.symptoms.map((s) => s.label).join(", ")}</p>
      )}
      <ResultView result={data.result} />
    </div>
  );
}
