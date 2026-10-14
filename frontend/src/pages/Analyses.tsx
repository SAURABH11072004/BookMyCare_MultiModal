import { Link } from "react-router-dom";
import { Activity, Plus } from "lucide-react";
import { MockBadge, UrgencyBadge } from "../components/badges";
import { Alert, Card, EmptyState, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export default function AnalysesPage() {
  const { data, loading, error } = useAsync(() => api.listAnalyses());
  return (
    <div>
      <PageHeader
        title="Analysis history"
        actions={<Link to="/analyses/new" className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"><Plus className="h-4 w-4" /> New analysis</Link>}
      />
      <Card>
        {loading ? <Spinner /> : error ? <Alert kind="error">{error}</Alert> : !data?.length ? (
          <EmptyState icon={<Activity className="h-8 w-8" />} title="No analyses yet" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.map((a) => (
              <li key={a.id}>
                <Link to={`/analyses/${a.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3 hover:bg-slate-50">
                  <div>
                    <div className="font-medium text-slate-800">{a.top_condition ?? "No strong match"}</div>
                    <div className="text-xs text-slate-500">#{a.id} · {formatDateTime(a.created_at)} · {a.symptom_preview.join(", ") || "Reports/images only"}</div>
                  </div>
                  <div className="flex gap-2">{a.is_mock && <MockBadge />}<UrgencyBadge urgency={a.urgency} /></div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
