import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Brain, FileSearch, ShieldCheck } from "lucide-react";
import { Logo } from "../components/Layout";
import { Alert, Button, Field, Input } from "../components/ui";
import { useAuth } from "../lib/auth";

function Shell({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-gradient-to-br from-brand-700 to-brand-900 p-10 text-white lg:flex">
        <div className="flex items-center gap-2 text-lg font-semibold">BookMyCare</div>
        <div className="space-y-6">
          <h2 className="text-3xl font-semibold leading-tight">Understand your health information, clearly and safely.</h2>
          <ul className="space-y-4 text-brand-100">
            <li className="flex gap-3"><FileSearch className="h-5 w-5 shrink-0" /> Upload lab reports and get plain-language explanations of out-of-range values.</li>
            <li className="flex gap-3"><Brain className="h-5 w-5 shrink-0" /> Explainable screening that shows exactly which symptoms and results were considered.</li>
            <li className="flex gap-3"><ShieldCheck className="h-5 w-5 shrink-0" /> Built-in safety checks for warning signs, with guidance from WHO and CDC sources.</li>
          </ul>
        </div>
        <p className="text-xs text-brand-200">Educational prototype - not a medical device and not a substitute for a doctor.</p>
      </div>
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-6">
          <Logo />
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

export function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password); // GuestOnly redirects once the user is set
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Welcome back" subtitle="Sign in to your BookMyCare account.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <Alert kind="error">{error}</Alert>}
        <Field label="Email" htmlFor="email">
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password" htmlFor="password">
          <Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <Button type="submit" className="w-full" loading={busy} disabled={!email || !password}>Sign in</Button>
      </form>
      <p className="text-sm text-slate-600">New here? <Link to="/register" className="font-medium text-brand-700 hover:underline">Create an account</Link></p>
    </Shell>
  );
}

export function validatePassword(p: string): string | null {
  if (p.length < 8) return "Use at least 8 characters.";
  if (!/[A-Za-z]/.test(p) || !/\d/.test(p)) return "Include at least one letter and one number.";
  return null;
}

export function RegisterPage() {
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [agree, setAgree] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pwError = password ? validatePassword(password) : null;
  const mismatch = confirm && confirm !== password ? "Passwords do not match." : null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (pwError || mismatch || !agree) return;
    setError(null);
    setBusy(true);
    try {
      await register(email, name, password); // GuestOnly redirects to /profile
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Create your account" subtitle="Your data stays in your BookMyCare database.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <Alert kind="error">{error}</Alert>}
        <Field label="Full name" htmlFor="name">
          <Input id="name" autoComplete="name" required value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Email" htmlFor="email">
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password" htmlFor="password" hint="At least 8 characters with a letter and a number." error={pwError}>
          <Input id="password" type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <Field label="Confirm password" htmlFor="confirm" error={mismatch}>
          <Input id="confirm" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </Field>
        <label className="flex items-start gap-2 text-sm text-slate-600">
          <input type="checkbox" className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
          I understand BookMyCare is an educational tool and does not provide medical diagnoses.
        </label>
        <Button type="submit" className="w-full" loading={busy} disabled={!name || !email || !password || !!pwError || !!mismatch || !agree}>
          Create account
        </Button>
      </form>
      <p className="text-sm text-slate-600">Already registered? <Link to="/login" className="font-medium text-brand-700 hover:underline">Sign in</Link></p>
    </Shell>
  );
}
