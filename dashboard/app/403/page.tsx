export default function ForbiddenPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="max-w-sm space-y-4 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center">
        <div className="text-5xl">🔒</div>
        <h1 className="text-lg font-semibold tracking-tight">Access denied</h1>
        <p className="text-sm text-[var(--color-text-dim)]">
          You signed in successfully, but this dashboard is only accessible to
          the configured account.
        </p>
        <form action="/auth/signout" method="post">
          <button
            type="submit"
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-2 text-sm transition-colors hover:bg-[var(--color-border)]"
          >
            Sign out and try a different account
          </button>
        </form>
      </div>
    </main>
  );
}
