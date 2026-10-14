import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity, BookOpen, ClipboardList, FileText, HeartPulse, History, LayoutDashboard, LogOut, Menu, Stethoscope, User, X,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import type { SystemStatus } from "../lib/types";
import { cx } from "./ui";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/analyses/new", label: "New analysis", icon: Stethoscope },
  { to: "/analyses", label: "Analysis history", icon: Activity, end: true },
  { to: "/reports", label: "Reports & images", icon: FileText },
  { to: "/history", label: "Medical history", icon: History },
  { to: "/profile", label: "My profile", icon: User },
  { to: "/library", label: "Health library", icon: BookOpen },
];

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cx("flex items-center gap-2", className)}>
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm">
        <HeartPulse className="h-5 w-5" aria-hidden />
      </span>
      <span className="text-lg font-semibold tracking-tight text-slate-900">BookMy<span className="text-brand-600">Care</span></span>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    api.status().then(setStatus).catch(() => setStatus(null));
  }, []);

  const nav = (
    <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Main">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
              isActive ? "bg-brand-50 text-brand-800" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )
          }
        >
          <Icon className="h-4 w-4" aria-hidden />
          {label}
        </NavLink>
      ))}
    </nav>
  );

  const userBox = (
    <div className="border-t border-slate-200 p-3">
      <div className="mb-2 px-3 text-xs text-slate-500">
        Signed in as
        <div className="truncate text-sm font-medium text-slate-800">{user?.full_name}</div>
      </div>
      <button onClick={logout} className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100">
        <LogOut className="h-4 w-4" aria-hidden /> Sign out
      </button>
    </div>
  );

  return (
    <div className="flex min-h-full">
      {/* Desktop sidebar */}
      <aside className="no-print sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
        <div className="border-b border-slate-200 px-5 py-4"><Logo /></div>
        {nav}
        {userBox}
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <Logo />
              <button onClick={() => setOpen(false)} aria-label="Close menu" className="rounded p-1 hover:bg-slate-100"><X className="h-5 w-5" /></button>
            </div>
            {nav}
            {userBox}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <Logo />
          <button onClick={() => setOpen(true)} aria-label="Open menu" className="rounded-lg p-2 hover:bg-slate-100"><Menu className="h-5 w-5" /></button>
        </header>

        {status?.ai.mock_mode && (
          <div className="no-print border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
            <strong>Mock AI mode:</strong> no AI provider key is configured. Explanations are template-based; screening uses the rule-based engine.
          </div>
        )}

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet context={status} />
        </main>

        <footer className="border-t border-slate-200 bg-white px-4 py-4 text-center text-xs text-slate-500">
          <ClipboardList className="mr-1 inline h-3.5 w-3.5" aria-hidden />
          BookMyCare is an educational prototype. It does not provide medical diagnoses. In an emergency call {status?.emergency_number ?? "your local emergency number"}.
        </footer>
      </div>
    </div>
  );
}
