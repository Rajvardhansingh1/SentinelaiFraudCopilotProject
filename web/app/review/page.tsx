export default function ReviewPage() {
  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold">Receipt Review</h1>
      <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
        Fraud Copilot (receipt review) is paused while SentinelAI itself is being expanded.
        Not linked from the sidebar. Code (agents/, components/review/, this page) is kept on
        disk, not deleted — resuming this feature later is a matter of restoring the nav link
        and running agents/api.py again.
      </div>
    </div>
  );
}
