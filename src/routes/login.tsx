import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { authClient, authEnabled, signInWithGoogle } from "@/lib/auth/client";
import { SignedIn } from "@/lib/auth/gates";
import { adoptLegacyLogin } from "@/lib/legacy";
import { confirmPasswordReset, requestPasswordReset } from "@/lib/password-reset";
import { PasswordField } from "@/components/password-field";
import { Field, PrimaryButton, fieldClass } from "@/components/ui-bits";

export const Route = createFileRoute("/login")({ component: Login });

type Mode = "signin" | "signup" | "forgot" | "reset";

function Login() {
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [code, setCode] = useState("");
  const [previewCode, setPreviewCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSignIn(e: React.FormEvent) {
    e.preventDefault();
    if (!authEnabled) return;
    setBusy(true);
    let result = await authClient.signIn.email({ email, password, callbackURL: "/" });
    if (result.error) {
      const adopted = await adoptLegacyLogin({ data: { identifier: email, password } });
      if (adopted.ok) {
        result = await authClient.signIn.email({
          email: adopted.email,
          password,
          callbackURL: "/",
        });
      }
    }
    setBusy(false);
    if (result.error) {
      toast.error(result.error.message ?? "Could not sign in.");
      return;
    }
    window.location.href = "/";
  }

  async function onSignUp(e: React.FormEvent) {
    e.preventDefault();
    if (!authEnabled) return;
    if (password !== confirm) {
      toast.error("Passwords do not match.");
      return;
    }
    setBusy(true);
    const { error } = await authClient.signUp.email({
      email,
      password,
      name: name.trim() || email.split("@")[0],
      callbackURL: "/",
    });
    setBusy(false);
    if (error) {
      toast.error(error.message ?? "Could not create the account.");
      return;
    }
    window.location.href = "/";
  }

  async function onForgot(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const res = await requestPasswordReset({ data: email });
    setBusy(false);
    setPreviewCode(res.previewCode);
    setMode("reset");
    toast.success("If that email is registered, a reset code is ready.");
  }

  async function onReset(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      toast.error("Passwords do not match.");
      return;
    }
    setBusy(true);
    const res = await confirmPasswordReset({
      data: { email, code, password },
    });
    setBusy(false);
    if (!res.ok) {
      toast.error(res.error);
      return;
    }
    toast.success("Password updated. Sign in with the new one.");
    setPassword("");
    setConfirm("");
    setCode("");
    setPreviewCode(null);
    setMode("signin");
  }

  const title =
    mode === "signup"
      ? "Create account"
      : mode === "forgot" || mode === "reset"
        ? "Reset password"
        : "Sign in";

  return (
    <main className="min-h-dvh bg-bg px-4 py-8 text-ink sm:px-6 sm:py-12">
      <div className="mx-auto w-full max-w-md">
        <Link to="/" className="mb-8 inline-block text-sm text-muted hover:text-ink">
          ← Back to the ledger
        </Link>
        <div className="rounded-lg bg-surface p-5 shadow-card sm:p-8">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">Cloud Stock Manager</p>
          <h1 className="mt-1 font-serif text-3xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-2 text-sm text-muted">
            {mode === "signin" && "Use the same email or username from the live shop."}
            {mode === "signup" && "One account for this shop ledger."}
            {mode === "forgot" && "We’ll give you a 6-digit code. In this preview it appears on the next screen."}
            {mode === "reset" && "Enter the code, then choose a new password."}
          </p>

          <SignedIn>
            <p className="mt-4 rounded-md bg-good-bg px-3 py-2 text-sm text-primary">
              You’re already signed in. You can still use this page to reset a password.
            </p>
          </SignedIn>

          {!authEnabled && (
            <p className="mt-4 text-sm text-muted">Sign-in is disabled on this build.</p>
          )}

          {authEnabled && (mode === "signin" || mode === "signup") && (
            <>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await signInWithGoogle({ callbackURL: "/" });
                  } catch (err) {
                    toast.error(err instanceof Error ? err.message : "Google sign-in failed.");
                  }
                }}
                className="mt-6 flex h-12 w-full items-center justify-center gap-3 rounded-md bg-white text-sm font-medium text-[#1f1f1f] shadow-card"
              >
                <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
                  <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z" />
                  <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.71H.96v2.33A9 9 0 0 0 9 18z" />
                  <path fill="#FBBC05" d="M3.97 10.71A5.41 5.41 0 0 1 3.69 9c0-.59.1-1.17.28-1.71V4.96H.96A9 9 0 0 0 0 9c0 1.45.35 2.82.96 4.04l3.01-2.33z" />
                  <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.96l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z" />
                </svg>
                Continue with Google
              </button>
              <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-wide text-muted">
                <span className="h-px flex-1 bg-line" />
                or email
                <span className="h-px flex-1 bg-line" />
              </div>
            </>
          )}
          {authEnabled && mode === "signin" && (
            <form className="mt-6 space-y-4" onSubmit={onSignIn}>
              <Field label="Email or username">
                <input
                  type="text"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                  className={fieldClass}
                />
              </Field>
              <PasswordField
                id="signin-password"
                label="Password"
                value={password}
                onChange={setPassword}
                autoComplete="current-password"
              />
              <div className="flex justify-end">
                <button
                  type="button"
                  className="min-h-11 text-sm font-medium text-primary"
                  onClick={() => setMode("forgot")}
                >
                  Forgot password?
                </button>
              </div>
              <PrimaryButton type="submit" className="h-12 w-full text-base" disabled={busy}>
                {busy ? "Signing in…" : "Sign in"}
              </PrimaryButton>
            </form>
          )}

          {authEnabled && mode === "signup" && (
            <form className="mt-6 space-y-4" onSubmit={onSignUp}>
              <Field label="Name">
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                  className={`${fieldClass} h-12 text-base`}
                />
              </Field>
              <Field label="Email">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  inputMode="email"
                  className={`${fieldClass} h-12 text-base`}
                />
              </Field>
              <PasswordField
                id="signup-password"
                label="Password"
                value={password}
                onChange={setPassword}
                autoComplete="new-password"
                minLength={8}
              />
              <PasswordField
                id="signup-confirm"
                label="Confirm password"
                value={confirm}
                onChange={setConfirm}
                autoComplete="new-password"
                minLength={8}
              />
              <PrimaryButton type="submit" className="h-12 w-full text-base" disabled={busy}>
                {busy ? "Creating…" : "Create account"}
              </PrimaryButton>
            </form>
          )}

          {authEnabled && mode === "forgot" && (
            <form className="mt-6 space-y-4" onSubmit={onForgot}>
              <Field label="Account email">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  inputMode="email"
                  className={`${fieldClass} h-12 text-base`}
                />
              </Field>
              <PrimaryButton type="submit" className="h-12 w-full text-base" disabled={busy}>
                {busy ? "Sending…" : "Send reset code"}
              </PrimaryButton>
              <button type="button" className="min-h-11 w-full text-sm text-muted" onClick={() => setMode("reset")}>
                I already have a code
              </button>
            </form>
          )}

          {authEnabled && mode === "reset" && (
            <form className="mt-6 space-y-4" onSubmit={onReset}>
              {previewCode && (
                <p className="rounded-md bg-warn-bg px-3 py-3 text-sm text-warn">
                  This preview can’t send email. Your code is{" "}
                  <span className="font-semibold tabular-nums tracking-widest">{previewCode}</span>
                </p>
              )}
              <Field label="Email">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  className={`${fieldClass} h-12 text-base`}
                />
              </Field>
              <Field label="6-digit code">
                <input
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  autoComplete="one-time-code"
                  className={`${fieldClass} h-12 text-center text-lg tracking-[0.4em]`}
                />
              </Field>
              <PasswordField
                id="reset-password"
                label="New password"
                value={password}
                onChange={setPassword}
                autoComplete="new-password"
                minLength={8}
              />
              <PasswordField
                id="reset-confirm"
                label="Confirm new password"
                value={confirm}
                onChange={setConfirm}
                autoComplete="new-password"
                minLength={8}
              />
              <PrimaryButton type="submit" className="h-12 w-full text-base" disabled={busy}>
                {busy ? "Saving…" : "Update password"}
              </PrimaryButton>
            </form>
          )}

          <p className="mt-6 text-center text-sm text-muted">
            {mode === "signup" ? (
              <button type="button" className="min-h-11 font-medium text-primary" onClick={() => setMode("signin")}>
                Already have an account? Sign in
              </button>
            ) : mode === "signin" ? (
              <button type="button" className="min-h-11 font-medium text-primary" onClick={() => setMode("signup")}>
                New here? Create an account
              </button>
            ) : (
              <button type="button" className="min-h-11 font-medium text-primary" onClick={() => setMode("signin")}>
                Back to sign in
              </button>
            )}
          </p>
        </div>
      </div>
    </main>
  );
}
