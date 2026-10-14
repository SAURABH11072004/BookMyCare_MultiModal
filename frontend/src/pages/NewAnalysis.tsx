import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Search, X } from "lucide-react";
import { Alert, Button, Card, Checkbox, Field, Input, PageHeader, Select, Spinner, Textarea, cx } from "../components/ui";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const COMMON = ["fever", "cough", "headache", "fatigue", "sore_throat", "body_aches", "nausea", "diarrhea", "shortness_of_breath", "chest_pain", "abdominal_pain", "dizziness"];

export default function NewAnalysisPage() {
  const nav = useNavigate();
  const { data, loading, error } = useAsync(async () => {
    const [catalog, files] = await Promise.all([api.symptomCatalog(), api.listReports()]);
    return { catalog, files };
  });
  const [selected, setSelected] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [text, setText] = useState("");
  const [duration, setDuration] = useState("");
  const [severity, setSeverity] = useState("");
  const [reportIds, setReportIds] = useState<number[]>([]);
  const [imageIds, setImageIds] = useState<number[]>([]);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const labelOf = useMemo(() => Object.fromEntries((data?.catalog ?? []).map((s) => [s.key, s.label])), [data]);
  const matches = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    const list = q ? data.catalog.filter((s) => s.label.toLowerCase().includes(q)) : data.catalog.filter((s) => COMMON.includes(s.key));
    return list.filter((s) => !selected.includes(s.key)).slice(0, 14);
  }, [data, query, selected]);

  if (loading) return <Spinner />;
  if (error || !data) return <Alert kind="error">{error}</Alert>;

  const reports = data.files.filter((f) => f.kind === "report");
  const images = data.files.filter((f) => f.kind === "image");
  const toggle = (list: number[], set: (v: number[]) => void, id: number) => set(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  const hasInput = selected.length > 0 || text.trim().length > 2 || reportIds.length > 0 || imageIds.length > 0;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const a = await api.createAnalysis({
        symptoms: selected,
        symptom_text: text.trim() || null,
        duration_days: duration === "" ? null : Number(duration),
        severity: (severity || null) as "mild" | "moderate" | "severe" | null,
        report_ids: reportIds,
        image_ids: imageIds,
        notes: notes.trim() || null,
      });
      nav(`/analyses/${a.id}`);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "Analysis failed");
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="New analysis" description="Combine your symptoms, lab reports and medical images. Results are screening suggestions to discuss with a doctor - not a diagnosis." />
      <Alert kind="error" className="mb-6" title="Emergency?">If you have chest pain, difficulty breathing, signs of stroke, severe bleeding or thoughts of harming yourself, contact emergency services immediately instead of using this tool.</Alert>

      <form onSubmit={submit} className="space-y-6">
        <Card title="1. Symptoms" subtitle="Select from the list and/or describe in your own words.">
          <div className="space-y-4">
            {selected.length > 0 && (
              <div className="flex flex-wrap gap-2" aria-label="Selected symptoms">
                {selected.map((k) => (
                  <span key={k} className="inline-flex items-center gap-1 rounded-full bg-brand-600 px-3 py-1 text-sm text-white">
                    {labelOf[k] ?? k}
                    <button type="button" aria-label={`Remove ${labelOf[k]}`} onClick={() => setSelected(selected.filter((x) => x !== k))}><X className="h-3.5 w-3.5" /></button>
                  </span>
                ))}
              </div>
            )}
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <Input aria-label="Search symptoms" placeholder="Search symptoms (e.g. rash, thirst, wheezing)…" className="pl-9" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <div className="flex flex-wrap gap-2">
              {matches.map((s) => (
                <button key={s.key} type="button" onClick={() => { setSelected([...selected, s.key]); setQuery(""); }}
                  className="rounded-full border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:border-brand-500 hover:bg-brand-50">
                  + {s.label}
                </button>
              ))}
              {matches.length === 0 && query && <p className="text-sm text-slate-500">No matching symptom - describe it in the text box below.</p>}
            </div>
            <Field label="Describe how you feel" htmlFor="desc" hint="Symptoms mentioned here are recognised automatically (simple negations like “no fever” are ignored).">
              <Textarea id="desc" rows={3} maxLength={4000} placeholder="e.g. High fever since 3 days with pain behind the eyes and joint pain" value={text} onChange={(e) => setText(e.target.value)} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="How long (days)?" htmlFor="dur">
                <Input id="dur" type="number" min={0} max={3650} value={duration} onChange={(e) => setDuration(e.target.value)} />
              </Field>
              <Field label="Severity" htmlFor="sev">
                <Select id="sev" value={severity} onChange={(e) => setSeverity(e.target.value)}>
                  <option value="">Not specified</option><option value="mild">Mild</option><option value="moderate">Moderate</option><option value="severe">Severe</option>
                </Select>
              </Field>
            </div>
          </div>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="2. Medical reports" subtitle="Lab values from selected reports are interpreted.">
            {reports.length === 0 ? <p className="text-sm text-slate-500">No reports yet. <Link to="/reports" className="text-brand-700 hover:underline">Upload one</Link>.</p> : (
              <ul className="space-y-2">
                {reports.map((r) => (
                  <li key={r.id} className={cx("rounded-lg border p-2", reportIds.includes(r.id) ? "border-brand-400 bg-brand-50" : "border-slate-200")}>
                    <Checkbox label={`${r.title} · ${formatDate(r.report_date ?? r.created_at)} · ${r.lab_count} labs`} checked={reportIds.includes(r.id)} onChange={() => toggle(reportIds, setReportIds, r.id)} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="3. Medical images" subtitle="Quality-checked; AI observations only if a vision provider is configured.">
            {images.length === 0 ? <p className="text-sm text-slate-500">No images yet. <Link to="/reports" className="text-brand-700 hover:underline">Upload one</Link>.</p> : (
              <ul className="space-y-2">
                {images.map((r) => (
                  <li key={r.id} className={cx("rounded-lg border p-2", imageIds.includes(r.id) ? "border-brand-400 bg-brand-50" : "border-slate-200")}>
                    <Checkbox label={`${r.title} · ${formatDate(r.report_date ?? r.created_at)}`} checked={imageIds.includes(r.id)} onChange={() => toggle(imageIds, setImageIds, r.id)} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <Card title="4. Notes (optional)">
          <Textarea aria-label="Notes" rows={2} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Anything else you want to record with this analysis" />
        </Card>

        {err && <Alert kind="error">{err}</Alert>}
        <div className="flex items-center justify-end gap-3">
          {!hasInput && <span className="text-sm text-slate-500">Add a symptom, report or image to continue.</span>}
          <Button type="submit" loading={busy} disabled={!hasInput}>Run analysis</Button>
        </div>
      </form>
    </div>
  );
}
