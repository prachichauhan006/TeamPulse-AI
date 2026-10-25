import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { AuthMarketingPanel } from "../components/AuthMarketingPanel";
import { inputClass, labelClass } from "../components/ui";
import { apiRequest, toUserMessage } from "../lib/api";
import type { User } from "../types";

export function Register() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirmation) { setError("Passwords do not match."); return; }
    setBusy(true); setError("");
    try { await apiRequest<User>("/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ full_name: fullName, email, password }) }); await login(email, password); navigate("/", { replace: true }); }
    catch (reason) { setError(toUserMessage(reason)); } finally { setBusy(false); }
  }
  return (
    <main className="grid min-h-screen bg-white lg:grid-cols-2"><section className="flex items-center justify-center bg-slate-50/60 px-5 py-12 sm:px-10"><div className="w-full max-w-md rounded-3xl border border-slate-200/80 bg-white p-7 shadow-xl shadow-slate-200/40 sm:p-9">
      <Link to="/" className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-indigo-600 text-white"><Icon name="sparkles" /></span><strong className="text-lg">TeamPulse AI</strong></Link><p className="mt-8 text-xs font-semibold uppercase tracking-wider text-indigo-600">A calmer way to work</p><h1 className="mt-2 text-3xl font-bold tracking-tight">Create your account</h1><p className="mt-2 text-sm text-slate-500">Start a clearer, more connected way of working.</p>
      <form className="mt-7 space-y-4" onSubmit={submit}><label className={labelClass}>Full name<input required minLength={1} maxLength={120} autoComplete="name" className={inputClass} value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Alex Morgan" /></label><label className={labelClass}>Email address<input type="email" required autoComplete="email" className={inputClass} value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" /></label><label className={labelClass}>Password<input type="password" required minLength={12} maxLength={128} autoComplete="new-password" className={inputClass} value={password} onChange={(event) => setPassword(event.target.value)} /><span className="text-xs font-normal text-slate-400">At least 12 characters.</span></label><label className={labelClass}>Confirm password<input type="password" required minLength={12} maxLength={128} autoComplete="new-password" className={inputClass} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>{error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}<button className="btn-primary w-full py-3" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button></form><p className="mt-6 text-center text-sm text-slate-500">Already have an account? <Link to="/login" className="font-semibold text-indigo-600 hover:underline">Sign in</Link></p>
    </div></section><AuthMarketingPanel /></main>
  );
}
