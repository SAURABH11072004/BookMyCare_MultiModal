import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Download, RefreshCw, Trash2 } from "lucide-react";
import { ExtractionBadge } from "../components/badges";
import LabTable from "../components/LabTable";
import { Alert, Badge, Button, Card, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { formatBytes, formatDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export default function ReportDetailPage() {
  const id = Number(useParams().id);
  const nav = useNavigate();
  const { data: r, setData, loading, error } = useAsync(() => api.getReport(id), [id]);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState<"reprocess" | "delete" | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!r || !(r.content_type.startsWith("image/") || r.content_type === "application/pdf")) return;
    let url: string | null = null;
    api.reportBlob(r.id).then((b) => { url = URL.createObjectURL(b); setBlobUrl(url); }).catch(() => setBlobUrl(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [r?.id, r?.content_type]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <Spinner />;
  if (error || !r) return <Alert kind="error">{error ?? "Not found"}</Alert>;

  async function reprocess() {
    setBusy("reprocess");
    setMsg(null);
    try { setData(await api.reprocessReport(id)); setMsg("Re-processed."); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Failed"); }
    finally { setBusy(null); }
  }
  async function remove() {
    if (!window.confirm("Delete this file permanently?")) return;
    setBusy("delete");
    try { await api.deleteReport(id); nav("/reports"); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Failed"); setBusy(null); }
  }
  async function download() {
    const b = await api.reportBlob(id);
    const url = URL.createObjectURL(b);
    const a = document.createElement("a");
    a.href = url;
    a.download = r!.original_filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  const q = r.image_features;
  return (
    <div className="space-y-6">
      <Link to="/reports" className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"><ArrowLeft className="h-4 w-4" /> All files</Link>
      <PageHeader
        title={r.title}
        description={<>{r.original_filename} · {formatBytes(r.size_bytes)} · {formatDate(r.report_date ?? r.created_at)}</>}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={download}><Download className="h-4 w-4" /> Download</Button>
            <Button variant="secondary" onClick={reprocess} loading={busy === "reprocess"}><RefreshCw className="h-4 w-4" /> Re-process</Button>
            <Button variant="danger" onClick={remove} loading={busy === "delete"}><Trash2 className="h-4 w-4" /> Delete</Button>
          </div>
        }
      />
      {msg && <Alert>{msg}</Alert>}

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-3">
          {r.kind === "report" ? (
            <>
              <Card title="Recognised lab values" actions={<ExtractionBadge status={r.extraction_status} />}>
                {r.extraction_error && <Alert kind="warning" className="mb-4">{r.extraction_error}</Alert>}
                <LabTable labs={r.lab_values} />
              </Card>
              <Card title="Extracted text" subtitle={r.extraction_method ? `Method: ${r.extraction_method.replace("_", " ")}` : undefined}>
                {r.extracted_text ? (
                  <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-700">{r.extracted_text}</pre>
                ) : <p className="text-sm text-slate-500">No text was extracted.</p>}
              </Card>
            </>
          ) : (
            <Card title="Image quality checks" subtitle="Describes the image file, not medical findings.">
              {q ? (
                <div className="space-y-3 text-sm">
                  <div className="flex flex-wrap gap-2">
                    <Badge>{q.width} × {q.height}px</Badge>
                    <Badge>{q.is_grayscale ? "Grayscale" : "Colour"}</Badge>
                    <Badge>Brightness {q.mean_brightness}</Badge>
                    <Badge>Contrast {q.contrast}</Badge>
                    <Badge>Sharpness {q.sharpness}</Badge>
                  </div>
                  {q.quality_ok ? <Alert kind="success">No quality issues detected.</Alert> : (
                    <Alert kind="warning" title="Quality notes"><ul className="list-disc pl-4">{q.quality_warnings.map((w) => <li key={w}>{w}</li>)}</ul></Alert>
                  )}
                </div>
              ) : <Alert kind="error">{r.extraction_error ?? "Could not analyse image."}</Alert>}
            </Card>
          )}
        </div>
        <div className="lg:col-span-2">
          <Card title="Preview">
            {blobUrl && r.content_type.startsWith("image/") && <img src={blobUrl} alt={r.title} className="mx-auto max-h-[480px] rounded-lg border border-slate-200" />}
            {blobUrl && r.content_type === "application/pdf" && <iframe src={blobUrl} title={r.title} className="h-[480px] w-full rounded-lg border border-slate-200" />}
            {!blobUrl && <p className="text-sm text-slate-500">{r.content_type.startsWith("text/") ? "Text file - see extracted text." : "Preview unavailable."}</p>}
          </Card>
        </div>
      </div>
    </div>
  );
}
