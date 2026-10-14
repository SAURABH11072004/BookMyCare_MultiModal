import { Link } from "react-router-dom";
import { Activity, ArrowRight, FileText, History as HistoryIcon, Stethoscope, UserCircle } from "lucide-react";
import { UrgencyBadge, MockBadge } from "../components/badges";
import { Alert, Card, EmptyState, PageHeader, ProgressBar, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDateTime } from "../lib/format";
import type { Profile } from "../lib/types";
import { useAsync } from "../lib/useAsync";

export function profileCompleteness(p: Profile | null): number {
  if (!p) return 0;
  const checks = [p.date_of_birth, p.sex, p.height_cm, p.weight_kg, p.activity_level, p.alcohol_use, p.blood_group];
  return checks.filter((x) => x !== null && x !== undefined && x !== "").length / checks.length;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, loading, error } = useAsync(async () => {
    const [profile, reports, analyses, history] = await Promise.all([api.getProfile(), api.listReports(), api.listAnalyses(), api.listHistory()]);
    return { profile, reports, analyses, history };
  });

  if (loading) return <Spinner />;
  if (error || !data) return <Alert kind="error">{error}</Alert>;
  const completeness = profileCompleteness(data.profile);
  const firstName = user?.full_name.split(" ")[0];

  return (
    <div className="space-y-6">
      <PageHeader title={`Hello, ${firstName}`} description="Here is an overview of your health records and recent screenings." />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Reports", value: data.reports.filter((r) => r.kind === "report").length, icon: FileText, to: "/reports" },
          { label: "Medical images", value: data.reports.filter((r) => r.kind === "image").length, icon: FileText, to: "/reports" },
          { label: "History entries", value: data.history.length, icon: HistoryIcon, to: "/history" },
          { label: "Analyses", value: data.analyses.length, icon: Activity, to: "/analyses" },
        ].map((s) => (
          <Link key={s.label} to={s.to} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-300">
            <div className="flex items-center justify-between text-slate-500"><span className="text-sm">{s.label}</span><s.icon className="h-4 w-4" /></div>
            <div className="mt-2 text-2xl font-semibold text-slate-900">{s.value}</div>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Start a new analysis" subtitle="Combine symptoms, lab reports and images for an explainable screening summary.">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <ul className="space-y-1 text-sm text-slate-600">
              <li>1. Describe your symptoms</li>
              <li>2. Attach reports or images (optional)</li>
              <li>3. Review matches, warning signs and a personalised care plan</li>
            </ul>
            <Link to="/analyses/new" className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700">
              <Stethoscope className="h-4 w-4" /> New analysis
            </Link>
          </div>
        </Card>

        <Card title="Profile completeness">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <UserCircle className="h-8 w-8 text-brand-600" />
              <div className="flex-1"><ProgressBar value={completeness} label="Profile completeness" /></div>
              <span className="text-sm font-medium">{Math.round(completeness * 100)}%</span>
            </div>
            <p className="text-sm text-slate-500">Age, sex, height and weight improve reference ranges and personalised advice.</p>
            <Link to="/profile" className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">Update profile <ArrowRight className="h-3.5 w-3.5" /></Link>
          </div>
        </Card>
      </div>

      <Card title="Recent analyses" actions={<Link to="/analyses" className="text-sm font-medium text-brand-700 hover:underline">View all</Link>}>
        {data.analyses.length === 0 ? (
          <EmptyState title="No analyses yet">Run your first analysis to see results here.</EmptyState>
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.analyses.slice(0, 5).map((a) => (
              <li key={a.id}>
                <Link to={`/analyses/${a.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3 hover:bg-slate-50">
                  <div>
                    <div className="font-medium text-slate-800">{a.top_condition ?? "No strong match"}</div>
                    <div className="text-xs text-slate-500">{formatDateTime(a.created_at)} · {a.symptom_preview.join(", ") || "Reports only"}</div>
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
