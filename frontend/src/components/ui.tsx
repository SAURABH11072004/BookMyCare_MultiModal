import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { AlertTriangle, CheckCircle2, Info, Loader2, XCircle } from "lucide-react";

export function cx(...c: (string | false | null | undefined)[]): string {
  return c.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "ghost" | "danger";

export function Button({
  variant = "primary", loading, className, children, disabled, ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  const styles: Record<Variant, string> = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 shadow-sm",
    secondary: "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50",
    ghost: "text-slate-600 hover:bg-slate-100",
    danger: "bg-white text-red-600 ring-1 ring-red-200 hover:bg-red-50",
  };
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
        styles[variant], className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

export function Card({ className, children, title, actions, subtitle }: {
  className?: string; children: ReactNode; title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode;
}) {
  return (
    <section className={cx("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-100 px-5 py-4">
          <div>
            {title && <h2 className="text-base font-semibold text-slate-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Field({ label, hint, error, children, htmlFor }: {
  label: string; hint?: string; error?: string | null; children: ReactNode; htmlFor?: string;
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-slate-700">{label}</label>
      {children}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

const inputBase =
  "block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:bg-slate-50";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx(inputBase, props.className)} />;
}
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cx(inputBase, props.className)} />;
}
export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cx(inputBase, props.className)} />;
}

export function Checkbox({ label, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-slate-700">
      <input type="checkbox" {...props} className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
      {label}
    </label>
  );
}

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", className ?? "bg-slate-100 text-slate-700")}>{children}</span>;
}

type AlertKind = "info" | "success" | "warning" | "error";
export function Alert({ kind = "info", title, children, className }: { kind?: AlertKind; title?: ReactNode; children?: ReactNode; className?: string }) {
  const meta = {
    info: { Icon: Info, cls: "border-sky-200 bg-sky-50 text-sky-900" },
    success: { Icon: CheckCircle2, cls: "border-emerald-200 bg-emerald-50 text-emerald-900" },
    warning: { Icon: AlertTriangle, cls: "border-amber-200 bg-amber-50 text-amber-900" },
    error: { Icon: XCircle, cls: "border-red-200 bg-red-50 text-red-900" },
  }[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={cx("flex gap-3 rounded-lg border p-3 text-sm", meta.cls, className)}>
      <meta.Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="space-y-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div>{children}</div>}
      </div>
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500" role="status">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> {label}
    </div>
  );
}

export function EmptyState({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-slate-300 px-6 py-10 text-center">
      {icon && <div className="text-slate-400">{icon}</div>}
      <p className="font-medium text-slate-700">{title}</p>
      {children && <div className="text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-slate-500">{description}</p>}
      </div>
      {actions}
    </div>
  );
}

export function ProgressBar({ value, className, label }: { value: number; className?: string; label?: string }) {
  const v = Math.max(0, Math.min(1, value));
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(v * 100)} aria-label={label}>
      <div className={cx("h-full rounded-full transition-all", className ?? "bg-brand-600")} style={{ width: `${v * 100}%` }} />
    </div>
  );
}
