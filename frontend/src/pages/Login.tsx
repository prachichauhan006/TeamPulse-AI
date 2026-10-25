import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { AuthMarketingPanel } from "../components/AuthMarketingPanel";
import { inputClass, labelClass } from "../components/ui";
import { ApiError, toUserMessage } from "../lib/api";

export function Login() {
  const { login, user, sessionExpired } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const destination = (location.state as { from?: string } | null)?.from ?? "/";
  if (user) return <Navigate to={destination} replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try { await login(email, password); navigate(destination, { replace: true }); }
    catch (reason) { setError(reason instanceof ApiError && reason.status === 401 ? "Email or password is incorrect." : toUserMessage(reason)); }
    finally { setBusy(false); }
  }

  return (
    <main className="grid min-h-screen bg-white lg:grid-cols-2">
      <section className="flex items-center justify-center bg-slate-50/60 px-5 py-12 sm:px-10"><div className="w-full max-w-md rounded-3xl border border-slate-200/80 bg-white p-7 shadow-xl shadow-slate-200/40 sm:p-9">
        <Link to="/" className="mb-10 flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-200"><Icon name="sparkles" /></span><span><strong className="block text-lg text-slate-950">TeamPulse AI</strong><span className="text-xs text-slate-500">AI Operating System for Teams</span></span></Link>
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">Your workspace awaits</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">Welcome back</h1><p className="mt-2 text-sm text-slate-500">Sign in to your team’s command center.</p>
        {(sessionExpired || (location.state as { sessionExpired?: boolean } | null)?.sessionExpired) && <div role="status" className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Your session expired. Please sign in again to continue.</div>}
        <form className="mt-8 space-y-5" onSubmit={submit}><label className={labelClass}>Email address<input type="email" autoComplete="email" required className={inputClass} value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" /></label><label className={labelClass}>Password<input type="password" autoComplete="current-password" required className={inputClass} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Your password" /></label>{error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}<button className="btn-primary w-full py-3" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button></form>
        <p className="mt-6 text-center text-sm text-slate-500">New to TeamPulse? <Link to="/register" className="font-semibold text-indigo-600 hover:underline">Create an account</Link></p><p className="mt-8 text-center text-xs leading-5 text-slate-400">Demo credentials are supplied by your local development configuration. No passwords are embedded in this application.</p>
      </div></section>
      <AuthMarketingPanel />
    </main>
  );
}
