import { rangeText } from "../lib/format";
import type { LabValue } from "../lib/types";
import { LabStatusBadge } from "./badges";

export default function LabTable({ labs, showExplanation = true }: { labs: LabValue[]; showExplanation?: boolean }) {
  if (!labs.length) return <p className="text-sm text-slate-500">No lab values were recognised.</p>;
  const sorted = [...labs].sort((a, b) => Number(a.status === "normal") - Number(b.status === "normal"));
  return (
    <div className="-mx-5 overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="px-5 py-2 font-medium">Test</th>
            <th className="px-3 py-2 font-medium">Result</th>
            <th className="px-3 py-2 font-medium">Typical range*</th>
            <th className="px-3 py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((l) => (
            <tr key={l.key} className="border-b border-slate-100 align-top">
              <td className="px-5 py-2">
                <div className="font-medium text-slate-800">{l.test}</div>
                {showExplanation && l.explanation && l.status !== "normal" && <div className="mt-0.5 max-w-md text-xs text-slate-500">{l.explanation}</div>}
              </td>
              <td className="whitespace-nowrap px-3 py-2 font-mono">{l.value} <span className="text-slate-500">{l.unit}</span></td>
              <td className="whitespace-nowrap px-3 py-2 text-slate-600">{rangeText(l.ref_low, l.ref_high)}</td>
              <td className="px-3 py-2"><LabStatusBadge status={l.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-5 pt-2 text-xs text-slate-500">*Generic adult ranges used for screening. The reference range printed on your own report takes precedence.</p>
    </div>
  );
}
