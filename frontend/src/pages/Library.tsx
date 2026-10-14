import { useState, type FormEvent } from "react";
import { BookOpen, ExternalLink, Search } from "lucide-react";
import { Alert, Badge, Button, Card, EmptyState, Input, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import type { SourceDoc } from "../lib/types";

const SUGGESTIONS = ["dengue warning signs", "high blood pressure", "diabetes symptoms", "anaemia", "stroke signs", "physical activity", "healthy diet", "tuberculosis cough"];

export function SourceCard({ doc }: { doc: SourceDoc }) {
  return (
    <article className="rounded-lg border border-slate-200 p-4">
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <Badge className={doc.source === "WHO" ? "bg-sky-100 text-sky-800" : "bg-indigo-100 text-indigo-800"}>{doc.source}</Badge>
        {doc.origin === "ingested" ? <Badge>Live page text</Badge> : <Badge>Curated summary</Badge>}
      </div>
      <h3 className="font-medium text-slate-900">{doc.title}</h3>
      <p className="mt-1 text-sm text-slate-600">{doc.snippet}</p>
      <a href={doc.url} target="_blank" rel="noreferrer noopener" className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">
        Read on {doc.source === "WHO" ? "who.int" : "cdc.gov"} <ExternalLink className="h-3.5 w-3.5" />
      </a>
    </article>
  );
}

export default function LibraryPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SourceDoc[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(query: string) {
    if (query.trim().length < 2) return;
    setQ(query);
    setLoading(true);
    setError(null);
    try { setResults((await api.searchKnowledge(query)).results); }
    catch (e) { setError(e instanceof Error ? e.message : "Search failed"); }
    finally { setLoading(false); }
  }

  return (
    <div>
      <PageHeader title="Health library" description="Search public-health guidance from the World Health Organization (WHO) and the US Centers for Disease Control and Prevention (CDC). Always follow the link to read the full, up-to-date source." />
      <Card>
        <form onSubmit={(e: FormEvent) => { e.preventDefault(); void run(q); }} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <Input aria-label="Search health topics" className="pl-9" placeholder="Search a condition, symptom or topic…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Button type="submit" disabled={q.trim().length < 2}>Search</Button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => <button key={s} onClick={() => void run(s)} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700 hover:bg-brand-50">{s}</button>)}
        </div>
      </Card>
      <div className="mt-6 space-y-3">
        {loading && <Spinner label="Searching…" />}
        {error && <Alert kind="error">{error}</Alert>}
        {results && !loading && (results.length ? results.map((d) => <SourceCard key={d.slug} doc={d} />) : <EmptyState icon={<BookOpen className="h-8 w-8" />} title="No matching documents" />)}
      </div>
    </div>
  );
}
