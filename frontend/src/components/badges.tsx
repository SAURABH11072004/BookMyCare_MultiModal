import { AlertOctagon } from "lucide-react";
import { labStatusMeta, urgencyMeta } from "../lib/format";
import type { LabStatus, Urgency } from "../lib/types";
import { Badge, cx } from "./ui";

export function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  const m = urgencyMeta[urgency];
  return <Badge className={m.className}>{urgency === "emergency" && <AlertOctagon className="h-3 w-3" />}{m.label}</Badge>;
}

export function LabStatusBadge({ status }: { status: LabStatus }) {
  const m = labStatusMeta[status];
  return <span className={cx("inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", m.className)}>{m.label}</span>;
}

export function MockBadge() {
  return <Badge className="bg-amber-100 text-amber-900 ring-1 ring-amber-300">Mock AI</Badge>;
}

export function ExtractionBadge({ status }: { status: string }) {
  const cls: Record<string, string> = {
    done: "bg-emerald-50 text-emerald-700",
    partial: "bg-amber-50 text-amber-800",
    skipped: "bg-slate-100 text-slate-600",
    failed: "bg-red-50 text-red-700",
    pending: "bg-slate-100 text-slate-600",
  };
  const label: Record<string, string> = { done: "Text extracted", partial: "Partially extracted", skipped: "Not extracted", failed: "Extraction failed", pending: "Pending" };
  return <Badge className={cls[status] ?? cls.pending}>{label[status] ?? status}</Badge>;
}
