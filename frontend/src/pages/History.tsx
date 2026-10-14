import { useState, type FormEvent } from "react";
import { History as HistoryIcon, Pencil, Plus, Trash2 } from "lucide-react";
import { Alert, Badge, Button, Card, Checkbox, EmptyState, Field, Input, PageHeader, Select, Spinner, Textarea } from "../components/ui";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";
import type { HistoryCategory, HistoryEntry } from "../lib/types";
import { useAsync } from "../lib/useAsync";

const CATEGORIES: { value: HistoryCategory; label: string }[] = [
  { value: "condition", label: "Condition / diagnosis" },
  { value: "surgery", label: "Surgery / procedure" },
  { value: "medication", label: "Medication" },
  { value: "allergy", label: "Allergy" },
  { value: "vaccination", label: "Vaccination" },
  { value: "visit", label: "Doctor visit" },
  { value: "other", label: "Other" },
];

type Draft = Omit<HistoryEntry, "id" | "created_at">;
const EMPTY: Draft = { category: "condition", title: "", details: "", event_date: null, is_ongoing: false };

export default function HistoryPage() {
  const { data, setData, loading, error } = useAsync(() => api.listHistory());
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [editing, setEditing] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [filter, setFilter] = useState<HistoryCategory | "">("");

  if (loading) return <Spinner />;
  if (error || !data) return <Alert kind="error">{error}</Alert>;

  function startEdit(e: HistoryEntry) {
    setDraft({ category: e.category, title: e.title, details: e.details ?? "", event_date: e.event_date, is_ongoing: e.is_ongoing });
    setEditing(e.id);
    setShowForm(true);
  }

  async function submit(ev: FormEvent) {
    ev.preventDefault();
    if (!data) return;
    setBusy(true);
    setFormError(null);
    try {
      const payload = { ...draft, details: draft.details || null };
      if (editing) {
        const updated = await api.updateHistory(editing, payload);
        setData(data.map((x) => (x.id === editing ? updated : x)));
      } else {
        const created = await api.createHistory(payload);
        setData([created, ...data]);
      }
      setDraft(EMPTY);
      setEditing(null);
      setShowForm(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!data || !window.confirm("Delete this history entry?")) return;
    try {
      await api.deleteHistory(id);
      setData(data.filter((x) => x.id !== id));
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  const items = filter ? data.filter((x) => x.category === filter) : data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Medical history"
        description="Past and ongoing conditions, procedures, medicines, allergies and vaccinations. Ongoing conditions, allergies and family history are considered in analyses."
        actions={!showForm && <Button onClick={() => { setDraft(EMPTY); setEditing(null); setShowForm(true); }}><Plus className="h-4 w-4" /> Add entry</Button>}
      />

      {showForm && (
        <Card title={editing ? "Edit entry" : "Add entry"}>
          <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
            <Field label="Category" htmlFor="cat">
              <Select id="cat" value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value as HistoryCategory })}>
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </Select>
            </Field>
            <Field label="Title" htmlFor="title" hint='For family history, include the word "family", e.g. "Family history of diabetes".'>
              <Input id="title" required maxLength={200} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
            </Field>
            <Field label="Date" htmlFor="date">
              <Input id="date" type="date" value={draft.event_date ?? ""} onChange={(e) => setDraft({ ...draft, event_date: e.target.value || null })} />
            </Field>
            <div className="flex items-end pb-2"><Checkbox label="Ongoing / current" checked={draft.is_ongoing} onChange={(e) => setDraft({ ...draft, is_ongoing: e.target.checked })} /></div>
            <div className="md:col-span-2">
              <Field label="Details" htmlFor="details">
                <Textarea id="details" rows={3} maxLength={5000} value={draft.details ?? ""} onChange={(e) => setDraft({ ...draft, details: e.target.value })} />
              </Field>
            </div>
            {formError && <div className="md:col-span-2"><Alert kind="error">{formError}</Alert></div>}
            <div className="flex justify-end gap-2 md:col-span-2">
              <Button type="button" variant="secondary" onClick={() => { setShowForm(false); setEditing(null); }}>Cancel</Button>
              <Button type="submit" loading={busy} disabled={!draft.title.trim()}>{editing ? "Save changes" : "Add entry"}</Button>
            </div>
          </form>
        </Card>
      )}

      <Card
        title="Timeline"
        actions={
          <Select aria-label="Filter by category" className="w-48" value={filter} onChange={(e) => setFilter(e.target.value as HistoryCategory | "")}>
            <option value="">All categories</option>
            {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </Select>
        }
      >
        {items.length === 0 ? (
          <EmptyState icon={<HistoryIcon className="h-8 w-8" />} title="No entries yet">Add conditions, medicines, allergies or vaccinations.</EmptyState>
        ) : (
          <ol className="relative space-y-4 border-l border-slate-200 pl-6">
            {items.map((e) => (
              <li key={e.id} className="relative">
                <span className="absolute -left-[31px] top-1.5 h-3 w-3 rounded-full border-2 border-white bg-brand-500 ring-1 ring-brand-200" />
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-slate-800">{e.title}</span>
                      <Badge>{CATEGORIES.find((c) => c.value === e.category)?.label}</Badge>
                      {e.is_ongoing && <Badge className="bg-brand-50 text-brand-800">Ongoing</Badge>}
                    </div>
                    <div className="text-xs text-slate-500">{formatDate(e.event_date)}</div>
                    {e.details && <p className="mt-1 whitespace-pre-line text-sm text-slate-600">{e.details}</p>}
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" className="px-2" onClick={() => startEdit(e)} aria-label={`Edit ${e.title}`}><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" className="px-2 text-red-600" onClick={() => remove(e.id)} aria-label={`Delete ${e.title}`}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}
